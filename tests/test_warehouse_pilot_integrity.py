import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import CheckConstraint

from app.models.warehouse_pilot import WarehouseCommercialProfile, WarehouseOperationalProfile, WarehouseRequirementAssessment
from app.schemas.warehouse_pilot import RequirementAssessmentWrite


def test_profile_warehouse_indexes_are_not_duplicated():
    for model in (WarehouseCommercialProfile, WarehouseOperationalProfile):
        warehouse_indexes = [
            index for index in model.__table__.indexes
            if tuple(index.columns.keys()) == ("warehouse_id",)
        ]
        assert len(warehouse_indexes) == 1


@pytest.mark.parametrize("model", [
    WarehouseCommercialProfile,
    WarehouseOperationalProfile,
    WarehouseRequirementAssessment,
])
def test_module_three_profiles_have_database_checks(model):
    checks = {constraint.name for constraint in model.__table__.constraints if isinstance(constraint, CheckConstraint)}
    assert checks
    assert all(name.startswith("ck_warehouse_") for name in checks)


def test_client_cannot_submit_attribution_fields():
    with pytest.raises(ValueError):
        RequirementAssessmentWrite(captured_by_user_id=99)
    with pytest.raises(ValueError):
        RequirementAssessmentWrite(validated_by_user_id=99)


def test_migration_is_single_connected_head_and_module_three_only():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    config = Config()
    config.set_main_option("script_location", str(versions.parent))
    scripts = ScriptDirectory.from_config(config)
    heads = scripts.get_heads()
    assert len(heads) == 1
    revisions = list(scripts.walk_revisions())
    assert revisions[0].revision == heads[0]
    revisions_by_id = {revision.revision: revision for revision in revisions}
    for revision in revisions:
        parents = revision.down_revision
        parents = (parents,) if isinstance(parents, str) else tuple(parents or ())
        for parent in parents:
            assert parent in revisions_by_id
    migration = (versions / "b657ffadfdac_add_warehouse_pilot_profiles_and_.py").read_text()
    assert "company_contacts" not in migration
    assert "warehouse_capability_profiles" not in migration