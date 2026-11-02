from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_content_staff
from app.models import Subject, User
from app.schemas.subject import SubjectCreate, SubjectResponse
from app.services import subject as subject_service


router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.get("", response_model=list[SubjectResponse])
def list_subjects(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_content_staff),
) -> list[Subject]:
    return subject_service.get_subjects(db, skip, limit)


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(
    subject: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_content_staff),
) -> Subject:
    return subject_service.create_subject(db, subject)
