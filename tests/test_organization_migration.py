"""Offline PostgreSQL DDL and metadata checks; no live database is contacted."""
import importlib.util
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import UniqueConstraint, create_mock_engine

from app.db.base import Base
from app.models import Company, Industry, Organization


VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def load_migration(filename):
    spec = importlib.util.spec_from_file_location("migration_under_test", VERSIONS / filename)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_warehouse_owner_downgrade_names_postgresql_constraint():
    migration = load_migration("51dc5e75a64f_create_users_and_warehouses_tables.py")
    statements = []
    engine = create_mock_engine(
        "postgresql://", lambda sql, *args, **kwargs: statements.append(
            str(sql.compile(dialect=engine.dialect))
        )
    )
    migration.op = Operations(MigrationContext.configure(engine))
    migration.downgrade()
    assert "DROP CONSTRAINT warehouses_owner_id_fkey" in statements[0]
    assert "CREATE INDEX ix_warehouses_id" in statements[1]
    assert "DROP COLUMN owner_id" in statements[-1]


def test_migration_chain_has_one_connected_head():
    config = Config()
    config.set_main_option("script_location", str(VERSIONS.parent))
    scripts = ScriptDirectory.from_config(config)
    heads = scripts.get_heads()
    assert len(heads) == 1
    revisions = list(scripts.walk_revisions())
    assert len(revisions) == len(list(VERSIONS.glob("*.py")))
    assert revisions[0].revision == heads[0]
    for child, parent in zip(revisions, revisions[1:]):
        assert child.down_revision == parent.revision
    assert revisions[-1].down_revision is None


def test_company_ownership_migration_matches_metadata():
    migration = load_migration("g2e3d4c5b6a7_add_organization_id_to_companies_table.py")
    statements = []
    engine = create_mock_engine(
        "postgresql://", lambda sql, *args, **kwargs: statements.append(
            str(sql.compile(dialect=engine.dialect))
        )
    )
    migration.op = Operations(MigrationContext.configure(engine))
    migration.upgrade()
    assert "ADD COLUMN organization_id INTEGER" in statements[0]
    assert "ALTER TABLE companies ALTER COLUMN organization_id SET NOT NULL" in statements[2]
    assert "CREATE INDEX ix_companies__organization_id" in statements[3]
    assert "CONSTRAINT fk_companies__organization_id" in statements[4]
    assert "REFERENCES organizations (id) ON DELETE RESTRICT" in statements[4]
    column = Company.__table__.c.organization_id
    assert column.nullable is False
    ownership_indexes = [
        index for index in Company.__table__.indexes
        if tuple(index.columns.keys()) == ("organization_id",)
    ]
    assert [index.name for index in ownership_indexes] == ["ix_companies__organization_id"]
    foreign_key = next(iter(column.foreign_keys))
    assert foreign_key.constraint.name == "fk_companies__organization_id"
    assert foreign_key.ondelete == "RESTRICT"
    statements.clear()
    migration.downgrade()
    assert "DROP CONSTRAINT fk_companies__organization_id" in statements[0]
    assert "DROP INDEX ix_companies__organization_id" in statements[1]
    assert "DROP COLUMN organization_id" in statements[2]


def test_original_migration_matches_model_columns_and_unique_constraints():
    migration = load_migration("f1e2d3c4b5a6_create_industries_and_organizations_tables.py")
    tables = {}

    def capture(sql, *args, **kwargs):
        if sql.__class__.__name__ == "CreateTable":
            tables[sql.element.name] = sql.element

    engine = create_mock_engine("postgresql://", capture)
    migration.op = Operations(MigrationContext.configure(engine))
    migration.upgrade()
    for model in (Industry, Organization):
        table = model.__table__
        assert Base.metadata.tables[table.name] is table
        original = tables[table.name]
        assert set(original.columns.keys()) == set(table.columns.keys())
        for column in table.columns:
            expected = original.c[column.name]
            assert column.nullable == expected.nullable
            assert str(column.type.compile(dialect=engine.dialect)) == str(
                expected.type.compile(dialect=engine.dialect)
            )
            assert (column.server_default is None) == (expected.server_default is None)
            if hasattr(column.type, "enums"):
                assert column.type.enums == expected.type.enums
        def unique_constraints(metadata_table):
            return {
                (constraint.name, tuple(constraint.columns.keys()))
                for constraint in metadata_table.constraints
                if isinstance(constraint, UniqueConstraint)
            }
        assert unique_constraints(table) == unique_constraints(original)


def test_corrective_migration_ddl_and_indexes_match_metadata():
    migration = load_migration("h3f4e5d6c7b8_align_organization_industry_constraints.py")
    statements = []
    engine = create_mock_engine(
        "postgresql://", lambda sql, *args, **kwargs: statements.append(
            str(sql.compile(dialect=engine.dialect))
        )
    )
    migration.op = Operations(MigrationContext.configure(engine))
    migration.upgrade()
    assert len(statements) == 4
    assert "DROP CONSTRAINT organizations_industry_id_fkey" in statements[0]
    assert "FOREIGN KEY(industry_id) REFERENCES industries (id) ON DELETE SET NULL" in statements[1]
    assert "CREATE INDEX ix_organizations__industry_id" in statements[2]
    assert "CREATE INDEX ix_organizations__legal_name" in statements[3]
    foreign_key = next(iter(Organization.__table__.c.industry_id.foreign_keys))
    assert foreign_key.ondelete == "SET NULL"
    assert foreign_key.constraint.name == "organizations_industry_id_fkey"
    assert {index.name for index in Industry.__table__.indexes} == {"ix_industries__category"}
    assert {index.name for index in Organization.__table__.indexes} == {
        "ix_organizations__city", "ix_organizations__legal_name",
        "ix_organizations__industry_id", "uq_organizations__gstin", "uq_organizations__pan",
    }
    statements.clear()
    migration.downgrade()
    assert len(statements) == 4
    assert "DROP INDEX ix_organizations__legal_name" in statements[0]
    assert "DROP INDEX ix_organizations__industry_id" in statements[1]
    assert "DROP CONSTRAINT organizations_industry_id_fkey" in statements[2]
    assert "FOREIGN KEY(industry_id) REFERENCES industries (id)" in statements[3]
    assert "ON DELETE" not in statements[3]