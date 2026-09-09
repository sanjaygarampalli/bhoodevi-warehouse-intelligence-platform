from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.schemas.industry import IndustryCreate, IndustryResponse, IndustryUpdate
from app.services.industry import IndustryService

router = APIRouter(prefix="/industries", tags=["Industries"])

industry_service = IndustryService()


@router.post("/", response_model=IndustryResponse)
def create_new_industry(
    industry: IndustryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    try:
        return industry_service.create_industry(db, industry)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/", response_model=list[IndustryResponse])
def read_all_industries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return industry_service.list_industries(db, skip=skip, limit=limit)


@router.get("/code/{code}", response_model=IndustryResponse)
def read_industry_by_code(
    code: str = Path(..., min_length=1, max_length=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    industry = industry_service.get_industry_by_code(db, code)
    if industry is None:
        raise HTTPException(status_code=404, detail="Industry not found")
    return industry


@router.get("/{industry_id}", response_model=IndustryResponse)
def read_industry(
    industry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    industry = industry_service.get_industry_by_id(db, industry_id)
    if industry is None:
        raise HTTPException(status_code=404, detail="Industry not found")
    return industry


@router.put("/{industry_id}", response_model=IndustryResponse)
def update_existing_industry(
    industry_id: int,
    industry: IndustryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    try:
        updated = industry_service.update_industry(db, industry_id, industry)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Industry not found")
    return updated


@router.delete("/{industry_id}")
def delete_existing_industry(
    industry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    try:
        deleted = industry_service.delete_industry(db, industry_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if deleted is None:
        raise HTTPException(status_code=404, detail="Industry not found")
    return {"message": "Industry deleted successfully"}