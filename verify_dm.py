"""Temp verification for Decision Maker (deleted after use)."""
from sqlalchemy.orm import configure_mappers


def check(label, fn):
    try:
        fn()
        print(f"[PASS] {label}")
    except Exception as e:
        print(f"[FAIL] {label}: {type(e).__name__}: {e}")


def imports():
    import app.main  # noqa
    import app.api.v1.routes  # noqa
    import app.models  # noqa
    import app.models.decision_maker  # noqa
    import app.schemas.decision_maker  # noqa
    import app.repositories.decision_maker  # noqa
    import app.services.decision_maker  # noqa
    import app.api.v1.endpoints.decision_maker  # noqa


def rels():
    from app.models.decision_maker import DecisionMaker
    from app.models.company import Company
    configure_mappers()
    dm = DecisionMaker.__mapper__
    cp = Company.__mapper__
    assert dm.relationships["company"].mapper.class_ is Company
    assert cp.relationships["decision_makers"].mapper.class_ is DecisionMaker
    fk = next(iter(next(c for c in dm.columns if c.name == "company_id").foreign_keys)).column
    assert fk.table.name == "companies" and fk.name == "id"


def alembic():
    import alembic.config
    from alembic.script import ScriptDirectory
    script = ScriptDirectory.from_config(alembic.config.Config("alembic.ini"))
    assert script.get_heads() == ["a1b2c3d4e5f6"]
    rev = script.get_revision("a1b2c3d4e5f6")
    assert rev.down_revision == "2d5dc7a7d3e6"
    assert script.get_revision("2d5dc7a7d3e6") is not None


def router():
    from app.api.v1.routes import router as r
    paths = [x.path for x in r.routes]
    for p in ["/decision-makers/", "/decision-makers/company/{company_id}", "/decision-makers/{decision_maker_id}"]:
        assert p in paths, p


check("imports resolve", imports)
check("relationships", rels)
check("alembic chain", alembic)
check("router reg", router)
print("DONE")