"""New migration round-trip plus offline PostgreSQL DDL parity; no live server."""
import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import CheckConstraint, create_engine, create_mock_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models import FollowUpTask


def migration():
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "k6c7d8e9f0a1_add_follow_up_tasks.py"
    spec = importlib.util.spec_from_file_location("follow_up_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_postgresql_model_migration_parity():
    tables, indexes, statements = {}, {}, []
    def capture(sql, *args, **kwargs):
        statements.append(str(sql.compile(dialect=engine.dialect)))
        if isinstance(sql, CreateTable):
            tables[sql.element.name] = sql.element
        if isinstance(sql, CreateIndex):
            indexes[sql.element.name] = sql.element
    engine = create_mock_engine("postgresql://", capture)
    module = migration()
    module.op = Operations(MigrationContext.configure(engine))
    module.upgrade()
    assert module.down_revision == "j5b6c7d8e9f0"
    assert list(tables) == ["follow_up_tasks"]
    expected, actual = FollowUpTask.__table__, tables["follow_up_tasks"]
    assert set(expected.c.keys()) == set(actual.c.keys())
    for column in expected.c:
        migrated = actual.c[column.name]
        assert column.nullable == migrated.nullable
        assert str(column.type.compile(dialect=engine.dialect)) == str(migrated.type.compile(dialect=engine.dialect))
        assert (str(column.server_default.arg) if column.server_default else None) == (
            str(migrated.server_default.arg) if migrated.server_default else None)
    assert {(c.name, str(c.sqltext)) for c in expected.constraints if isinstance(c, CheckConstraint)} == {
        (c.name, str(c.sqltext)) for c in actual.constraints if isinstance(c, CheckConstraint)}
    assert {(f.parent.name, f.target_fullname, f.ondelete) for f in expected.foreign_keys} == {
        (f.parent.name, f.target_fullname, f.ondelete) for f in actual.foreign_keys}
    assert {index.name for index in expected.indexes} == set(indexes)
    for index in expected.indexes:
        actual_index = indexes[index.name]
        assert index.unique == actual_index.unique
        assert list(index.columns.keys()) == list(actual_index.columns.keys())
        assert str(index.dialect_options["postgresql"].get("where")) == str(actual_index.dialect_options["postgresql"].get("where"))
    ddl = "\n".join(statements)
    assert "TIMESTAMP WITH TIME ZONE" in ddl
    assert "WHERE status IN ('OPEN','IN_PROGRESS') AND recommendation_key IS NOT NULL" in ddl
    assert "CREATE TYPE" not in ddl
    module.downgrade()
    assert "DROP TABLE follow_up_tasks" in statements[-1]


@pytest.mark.parametrize("populated", [False, True])
def test_upgrade_downgrade_preserves_parent_data(populated):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
        parents = ("leads", "deals", "users")
        for table in parents:
            connection.execute(text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)"))
            if populated:
                connection.execute(text(f"INSERT INTO {table} VALUES (1)"))
        module = migration()
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        assert "follow_up_tasks" in inspect(connection).get_table_names()
        if populated:
            connection.execute(text("INSERT INTO follow_up_tasks (lead_id,deal_id,assigned_to_user_id,subject,due_at) VALUES (1,1,1,'Call','2026-09-09')"))
            for statement in (
                "DELETE FROM leads WHERE id=1", "DELETE FROM deals WHERE id=1", "DELETE FROM users WHERE id=1",
                "UPDATE follow_up_tasks SET lead_id=999", "UPDATE follow_up_tasks SET deal_id=999",
                "UPDATE follow_up_tasks SET assigned_to_user_id=999", "UPDATE follow_up_tasks SET due_at=NULL",
                "UPDATE follow_up_tasks SET status='OVERDUE'", "UPDATE follow_up_tasks SET priority='INVALID'",
                "UPDATE follow_up_tasks SET task_type='INVALID'", "UPDATE follow_up_tasks SET subject=' '",
                "UPDATE follow_up_tasks SET status='COMPLETED'", "UPDATE follow_up_tasks SET status='CANCELLED'",
                "UPDATE follow_up_tasks SET completed_at='2026-09-09'",
            ):
                with pytest.raises(IntegrityError):
                    connection.execute(text(statement))
            connection.execute(text("UPDATE follow_up_tasks SET recommendation_key='RESEARCH_COMPANY'"))
            with pytest.raises(IntegrityError):
                connection.execute(text("INSERT INTO follow_up_tasks (lead_id,subject,due_at,recommendation_key,status) VALUES (1,'Duplicate','2026-09-09','RESEARCH_COMPANY','IN_PROGRESS')"))
            connection.execute(text("UPDATE follow_up_tasks SET status='COMPLETED',completed_at='2026-09-09'"))
            connection.execute(text("INSERT INTO follow_up_tasks (lead_id,subject,due_at,recommendation_key) VALUES (1,'New task','2026-09-09','RESEARCH_COMPANY')"))
        module.downgrade()
        assert set(inspect(connection).get_table_names()) == set(parents)
        for table in parents:
            assert connection.scalar(text(f"SELECT count(*) FROM {table}")) == int(populated)
        module.upgrade()
        assert connection.scalar(text("SELECT count(*) FROM follow_up_tasks")) == 0
    engine.dispose()