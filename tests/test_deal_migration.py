"""Isolated migration round-trip and PostgreSQL DDL/model parity; no live server."""
import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import CheckConstraint, UniqueConstraint, create_engine, create_mock_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable

from app.models import Deal, DealPipelineStage, DealStageHistory


def migration():
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "j5b6c7d8e9f0_add_deal_pipeline.py"
    spec = importlib.util.spec_from_file_location("deal_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_postgresql_ddl_matches_models():
    tables, statements = {}, []

    def capture(sql, *args, **kwargs):
        statements.append(str(sql.compile(dialect=engine.dialect)))
        if isinstance(sql, CreateTable):
            tables[sql.element.name] = sql.element

    engine = create_mock_engine("postgresql://", capture)
    module = migration()
    module.op = Operations(MigrationContext.configure(engine))
    module.upgrade()
    assert module.down_revision == "i4a5b6c7d8e9"
    for model in (DealPipelineStage, Deal, DealStageHistory):
        expected, actual = model.__table__, tables[model.__tablename__]
        module6_columns = {
            "lost_reason_category", "final_commercial_amount", "final_commercial_currency",
            "final_lease_duration_months", "outcome_notes", "closure_evidence_reference",
        } if model is Deal else set()
        expected_columns = set(expected.c.keys()) - module6_columns
        assert expected_columns == set(actual.c.keys())
        for column in expected.c:
            if column.name in module6_columns:
                continue
            assert column.nullable == actual.c[column.name].nullable
            assert str(column.type.compile(dialect=engine.dialect)) == str(actual.c[column.name].type.compile(dialect=engine.dialect))
        for kind in (CheckConstraint, UniqueConstraint):
            assert {c.name for c in expected.constraints if isinstance(c, kind)} == {c.name for c in actual.constraints if isinstance(c, kind)}
        assert {(f.parent.name, f.target_fullname, f.ondelete) for f in expected.foreign_keys} == {
            (f.parent.name, f.target_fullname, f.ondelete) for f in actual.foreign_keys}
        for index in expected.indexes:
            if "lost_reason_category" in index.name:
                continue
            assert any(index.name in statement for statement in statements)
    ddl = "\n".join(statements)
    assert "WHERE deal_status = 'OPEN'" in ddl
    assert "TIMESTAMP WITH TIME ZONE" in ddl
    assert "CREATE TYPE" not in ddl
    module.downgrade()
    assert "DROP TABLE deal_pipeline_stages" in statements[-1]


@pytest.mark.parametrize("populated", [False, True])
def test_upgrade_downgrade_and_constraints(populated):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
        parents = ("organizations", "leads", "requirements", "warehouse_matches", "users")
        for table in parents:
            connection.execute(text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY)"))
            if populated:
                connection.execute(text(f"INSERT INTO {table} VALUES (1)"))
        module = migration()
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        assert {"deals", "deal_pipeline_stages", "deal_stage_history"}.issubset(inspect(connection).get_table_names())
        if populated:
            connection.execute(text("INSERT INTO deal_pipeline_stages (id,organization_id,stage_name,stage_key,stage_order) VALUES (1,1,'Qualified','QUALIFIED',10)"))
            insert = "INSERT INTO deals (organization_id,deal_name,lead_id,requirement_id,stage_id,stage_entered_at) VALUES (1,'Lease',1,1,1,'2026-09-09')"
            connection.execute(text(insert))
            with pytest.raises(IntegrityError):
                connection.execute(text(insert))
            with pytest.raises(IntegrityError):
                connection.execute(text("DELETE FROM leads WHERE id=1"))
            with pytest.raises(IntegrityError):
                connection.execute(text("UPDATE deal_pipeline_stages SET is_terminal=1"))
            with pytest.raises(IntegrityError):
                connection.execute(text("UPDATE deals SET deal_status='WON'"))
            connection.execute(text("INSERT INTO deal_stage_history (deal_id,to_stage_id,to_stage_key,to_stage_name,changed_at) VALUES (1,1,'QUALIFIED','Qualified','2026-09-09')"))
        module.downgrade()
        assert set(inspect(connection).get_table_names()) == set(parents)
        for table in parents:
            assert connection.scalar(text(f"SELECT count(*) FROM {table}")) == int(populated)
        module.upgrade()
        assert connection.scalar(text("SELECT count(*) FROM deals")) == 0
    engine.dispose()