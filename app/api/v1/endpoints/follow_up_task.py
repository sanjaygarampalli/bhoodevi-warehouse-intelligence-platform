from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.follow_up_task import TaskStatus
from app.models.user import User
from app.schemas.follow_up_task import (
    FollowUpTaskCreate, FollowUpTaskResponse, FollowUpTaskUpdate, TaskCancellation, TaskCompletion,
)
from app.services.follow_up_task import FollowUpTaskService

router = APIRouter(prefix="/follow-up-tasks", tags=["Follow-up Tasks"])
task_service = FollowUpTaskService()


@router.get("/", response_model=list[FollowUpTaskResponse])
def list_tasks(
    lead_id: int | None = Query(None, gt=0), deal_id: int | None = Query(None, gt=0),
    assigned_to_user_id: int | None = Query(None, gt=0), status: TaskStatus | None = None,
    queue: Literal["OPEN", "OVERDUE", "UPCOMING"] | None = None,
    skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    return task_service.list_tasks(db, lead_id=lead_id, deal_id=deal_id,
                                   assigned_to_user_id=assigned_to_user_id, status=status,
                                   queue=queue, skip=skip, limit=limit)


@router.post("/", response_model=FollowUpTaskResponse)
def create_task(
    task: FollowUpTaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin),
):
    return task_service.create_task(db, task)


@router.get("/{task_id}", response_model=FollowUpTaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return task_service.get_task(db, task_id)


@router.put("/{task_id}", response_model=FollowUpTaskResponse)
def update_task(
    task_id: int, task: FollowUpTaskUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin),
):
    return task_service.update_task(db, task_id, task)


@router.post("/{task_id}/complete", response_model=FollowUpTaskResponse)
def complete_task(
    task_id: int, completion: TaskCompletion,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin),
):
    return task_service.complete_task(db, task_id, completion)


@router.post("/{task_id}/cancel", response_model=FollowUpTaskResponse)
def cancel_task(
    task_id: int, cancellation: TaskCancellation,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin),
):
    return task_service.cancel_task(db, task_id, cancellation)