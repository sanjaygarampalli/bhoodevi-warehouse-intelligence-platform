from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories.warehouse_intelligence_conversion import WarehouseIntelligenceOpportunityConversionRepository
from app.schemas.warehouse_intelligence_conversion import (
    WarehouseIntelligenceConversionResponse,
    WarehouseMatchOpportunityConversionRequest,
    WarehouseMatchOpportunityConversionResponse,
)
from app.services.organization_access import require_organization_access, require_organization_write
from app.services.warehouse_intelligence_conversion import (
    WarehouseIntelligenceConversionError,
    WarehouseIntelligenceOpportunityConversionService,
)
from app.models.warehouse_match import WarehouseMatch
from app.models.company import Company

router = APIRouter(prefix="/workflow", tags=["Workflow"])
conversion_service = WarehouseIntelligenceOpportunityConversionService()
conversion_repository = WarehouseIntelligenceOpportunityConversionRepository()


@router.post(
    "/warehouse-matches/{warehouse_match_id}/opportunities",
    response_model=WarehouseMatchOpportunityConversionResponse,
)
def convert_warehouse_match(
    warehouse_match_id: int,
    payload: WarehouseMatchOpportunityConversionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match = db.get(WarehouseMatch, warehouse_match_id)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse match not found")
    company = db.get(Company, match.lead.company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse match company not found")
    require_organization_write(db, current_user, company.organization_id)
    try:
        conversion, deal, created = conversion_service.convert_warehouse_match(
            db, warehouse_match_id, payload, user_id=current_user.id, organization_id=company.organization_id,
        )
        return WarehouseMatchOpportunityConversionResponse(conversion=conversion, deal=deal, created=created)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ValueError, WarehouseIntelligenceConversionError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/warehouse-intelligence-conversions/{conversion_id}",
    response_model=WarehouseIntelligenceConversionResponse,
)
def get_conversion(
    conversion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversion = conversion_repository.get_by_id(db, conversion_id)
    if conversion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversion not found")
    require_organization_access(db, current_user, conversion.organization_id)
    return conversion