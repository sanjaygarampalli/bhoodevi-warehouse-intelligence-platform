"""New revision round-trips on disposable SQLite; PostgreSQL DDL is offline."""
import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, create_mock_engine, inspect, text
from sqlalchemy.schema import CreateTable

from app.models import LeadScoreSnapshot


def load_migration():
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "i4a5b6c7d8e9_add_lead_score_snapshots.py"
    spec = importlib.util.spec_from_file_location("score_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_postgresql_migration_matches_model_and_reuses_priority_enum():
    migration = load_migration()
    statements = []
    tables = []

    def capture(sql, *args, **kwargs):
        statements.append(str(sql.compile(dialect=engine.dialect)))
        if isinstance(sql, CreateTable):
            tables.append(sql.element)

    engine = create_mock_engine("postgresql://", capture)
    migration.op = Operations(MigrationContext.configure(engine))
    migration.upgrade()
    assert migration.down_revision == "h3f4e5d6c7b8"
    assert len(statements) == 2
    assert "JSONB NOT NULL" in statements[0]
    assert "TIMESTAMP WITH TIME ZONE NOT NULL" in statements[0]
    assert "priority leadpriority NOT NULL" in statements[0]
    assert "ON DELETE CASCADE" in statements[0]
    assert "CREATE TYPE" not in "\n".join(statements)
    model = LeadScoreSnapshot.__table__
    migrated = tables[0]
    assert set(migrated.columns.keys()) == set(model.columns.keys())
    for column in model.columns:
        other = migrated.c[column.name]
        assert column.nullable == other.nullable
        assert str(column.type.compile(dialect=engine.dialect)) == str(other.type.compile(dialect=engine.dialect))
    assert {index.name for index in model.indexes} == {"ix_lead_score_snapshots__lead_id__calculated_at"}
    assert "(lead_id, calculated_at, id)" in statements[1]
    statements.clear()
    migration.downgrade()
    assert len(statements) == 2
    assert "DROP INDEX ix_lead_score_snapshots__lead_id__calculated_at" in statements[0]
    assert "DROP TABLE lead_score_snapshots" in statements[1]
    assert "DROP TYPE" not in "\n".join(statements)


@pytest.mark.parametrize("populated", [False, True])
def test_new_migration_upgrade_downgrade_preserves_existing_leads(populated):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
        connection.execute(text("CREATE TABLE leads (id INTEGER PRIMARY KEY)"))
        if populated:
            connection.execute(text("INSERT INTO leads (id) VALUES (1)"))
        migration = load_migration()
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        assert "lead_score_snapshots" in inspect(connection).get_table_names()
        assert inspect(connection).get_foreign_keys("lead_score_snapshots")[0]["options"]["ondelete"] == "CASCADE"
        if populated:
            connection.execute(text(
                "INSERT INTO lead_score_snapshots (lead_id,total_score,priority,scoring_version,reasons,calculated_at) "
                "VALUES (1,10,'LOW','v1','[]','2026-09-09 12:00:00')"
            ))
        migration.downgrade()
        assert inspect(connection).get_table_names() == ["leads"]
        assert connection.scalar(text("SELECT count(*) FROM leads")) == int(populated)
        migration.upgrade()
        assert connection.scalar(text("SELECT count(*) FROM lead_score_snapshots")) == 0
    engine.dispose()