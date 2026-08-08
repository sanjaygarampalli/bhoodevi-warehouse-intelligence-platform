from sqlalchemy.orm import Session

from app.models.warehouse_match import WarehouseMatch
from app.repositories.lead import LeadRepository
from app.repositories.requirement import RequirementRepository
from app.repositories.warehouse import WarehouseRepository
from app.repositories.warehouse_match import WarehouseMatchRepository
from app.schemas.warehouse_match import WarehouseMatchCreate, WarehouseMatchUpdate


class WarehouseMatchService:
    def __init__(self) -> None:
        self.repository = WarehouseMatchRepository()
        self.lead_repository = LeadRepository()
        self.warehouse_repository = WarehouseRepository()
        self.requirement_repository = RequirementRepository()

    def create_match(
        self,
        db: Session,
        match_data: WarehouseMatchCreate,
    ) -> WarehouseMatch | None:
        lead = self.lead_repository.get_by_id(db, match_data.lead_id)
        if lead is None:
            return None

        warehouse = self.warehouse_repository.get_by_id(db, match_data.warehouse_id)
        if warehouse is None:
            return None

        if match_data.requirement_id is not None:
            requirement = self.requirement_repository.get_by_id(
                db,
                match_data.requirement_id,
            )
            if requirement is None:
                return None

        db_match = WarehouseMatch(**match_data.model_dump())
        return self.repository.create(db, db_match)

    def get_match_by_id(
        self,
        db: Session,
        match_id: int,
    ) -> WarehouseMatch | None:
        return self.repository.get_by_id(db, match_id)

    def list_matches_for_lead(
        self,
        db: Session,
        lead_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WarehouseMatch]:
        return self.repository.get_matches_for_lead(
            db,
            lead_id,
            limit=limit,
            offset=offset,
        )

    def list_matches_for_warehouse(
        self,
        db: Session,
        warehouse_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WarehouseMatch]:
        return self.repository.get_matches_for_warehouse(
            db,
            warehouse_id,
            limit=limit,
            offset=offset,
        )

    def list_matches_for_requirement(
        self,
        db: Session,
        requirement_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WarehouseMatch]:
        return self.repository.get_matches_for_requirement(
            db,
            requirement_id,
            limit=limit,
            offset=offset,
        )

    def update_match(
        self,
        db: Session,
        match_id: int,
        match_data: WarehouseMatchUpdate,
    ) -> WarehouseMatch | None:
        db_match = self.repository.get_by_id(db, match_id)
        if db_match is None:
            return None

        update_data = match_data.model_dump(exclude_unset=True)

        if "lead_id" in update_data and update_data["lead_id"] != db_match.lead_id:
            lead = self.lead_repository.get_by_id(db, update_data["lead_id"])
            if lead is None:
                return None

        if "warehouse_id" in update_data and update_data["warehouse_id"] != db_match.warehouse_id:
            warehouse = self.warehouse_repository.get_by_id(
                db,
                update_data["warehouse_id"],
            )
            if warehouse is None:
                return None

        if "requirement_id" in update_data:
            requirement_id = update_data["requirement_id"]
            if requirement_id is None:
                db_match.requirement_id = None
            else:
                requirement = self.requirement_repository.get_by_id(
                    db,
                    requirement_id,
                )
                if requirement is None:
                    return None
                db_match.requirement_id = requirement_id

        for key, value in update_data.items():
            if key == "requirement_id":
                continue
            setattr(db_match, key, value)

        return self.repository.update(db, db_match)

    def delete_match(
        self,
        db: Session,
        match_id: int,
    ) -> WarehouseMatch | None:
        db_match = self.repository.get_by_id(db, match_id)
        if db_match is None:
            return None

        self.repository.delete(db, db_match)
        return db_match