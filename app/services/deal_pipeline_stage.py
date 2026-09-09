from app.models.deal_pipeline_stage import DealPipelineStage
from app.models.organization import Organization
from app.repositories.deal import DealRepository
from app.repositories.deal_pipeline_stage import DealPipelineStageRepository
from app.schemas.deal_pipeline_stage import DealPipelineStageCreate
from app.services.deal_workflow import DealConflict, DealNotFound, validate_pagination, workflow_transaction


class DealPipelineStageService:
    def __init__(self):
        self.repository = DealPipelineStageRepository()

    @staticmethod
    def _validate(data):
        if data["is_terminal"] != (data["is_won"] or data["is_lost"]) or (data["is_won"] and data["is_lost"]):
            raise DealConflict("Terminal stages must have exactly one outcome: is_won or is_lost")

    @workflow_transaction
    def create_stage(self, db, payload):
        data = DealPipelineStageCreate.model_validate(payload.model_dump()).model_dump()
        self._validate(data)
        if DealRepository().get_reference(db, Organization, data["organization_id"]) is None:
            raise DealNotFound("Organization not found")
        return self.repository.create(db, DealPipelineStage(**data))

    def get_stage(self, db, stage_id):
        stage = self.repository.get_by_id(db, stage_id)
        if stage is None:
            raise DealNotFound("Deal pipeline stage not found")
        return stage

    def list_stages(self, db, *, organization_id=None, is_active=None, skip=0, limit=100):
        validate_pagination(skip, limit)
        return self.repository.list_stages(db, organization_id, is_active, skip, limit)

    @workflow_transaction
    def update_stage(self, db, stage_id, payload):
        stage = self.repository.get_locked(db, stage_id)
        if stage is None:
            raise DealNotFound("Deal pipeline stage not found")
        changes = payload.model_dump(exclude_unset=True)
        data = {field: getattr(stage, field) for field in DealPipelineStageCreate.model_fields}
        data.update(changes)
        data = DealPipelineStageCreate.model_validate(data).model_dump()
        self._validate(data)
        if self.repository.is_referenced(db, stage_id):
            for field in ("stage_key", "is_terminal", "is_won", "is_lost"):
                if data[field] != getattr(stage, field):
                    raise DealConflict("Referenced stage keys and terminal outcomes cannot change")
        for field in changes:
            setattr(stage, field, data[field])
        return self.repository.update(db, stage)

    @workflow_transaction
    def delete_stage(self, db, stage_id):
        stage = self.repository.get_locked(db, stage_id)
        if stage is None:
            raise DealNotFound("Deal pipeline stage not found")
        if self.repository.is_referenced(db, stage_id):
            raise DealConflict("Stage is referenced by a Deal or its history; deactivate it instead")
        self.repository.delete(db, stage)