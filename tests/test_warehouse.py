"""Warehouse CRUD regressions; matching must not change legacy warehouse APIs."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import AvailabilityStatus, User, WarehouseType
from app.schemas.warehouse import WarehouseCreate, WarehouseResponse, WarehouseUpdate
from app.services.warehouse import WarehouseService


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(id=1, full_name="Owner", email="owner@example.com", hashed_password="unused"))
        session.commit()
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_warehouse_crud_and_relationships(db_session):
    service = WarehouseService()
    created = service.create_warehouse(db_session, WarehouseCreate(
        warehouse_name="Stock", city="Bengaluru", state="Karnataka", owner_id=1,
        total_area_sqft=1000, warehouse_type=WarehouseType.COVERED,
        availability_status=AvailabilityStatus.AVAILABLE,
    ))
    stock_id = created.id
    assert created.owner.email == "owner@example.com"
    assert created.matches == []
    assert WarehouseResponse.model_validate(created).total_area_sqft == 1000
    assert service.get_warehouse_by_id(db_session, stock_id) is created
    assert service.list_warehouses(db_session) == [created]
    assert service.get_warehouses_by_city(db_session, "Bengaluru") == [created]
    assert service.get_warehouses_by_state(db_session, "Karnataka") == [created]
    assert service.get_warehouses_by_owner(db_session, 1) == [created]
    updated = service.update_warehouse(db_session, stock_id, WarehouseUpdate(availability_status=AvailabilityStatus.INACTIVE))
    assert updated.availability_status == AvailabilityStatus.INACTIVE
    # Preserve the legacy get_available contract; matching uses its own filtered query.
    assert service.list_available_warehouses(db_session) == [created]
    assert service.delete_warehouse(db_session, stock_id) is created
    assert service.get_warehouse_by_id(db_session, stock_id) is None


def test_warehouse_missing_records(db_session):
    service = WarehouseService()
    assert service.get_warehouse_by_id(db_session, 9999) is None
    assert service.update_warehouse(db_session, 9999, WarehouseUpdate(city="Mumbai")) is None
    assert service.delete_warehouse(db_session, 9999) is None