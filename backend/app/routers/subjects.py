from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_content_staff
from app.models import ContentBlock, Subject, User
from app.schemas.content_block import ContentBlockCreate, ContentBlockResponse
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


@router.get("/{subject_id}", response_model=SubjectResponse)
def subject_detail(
    subject_id: int = Path(ge=1), db: Session = Depends(get_db),
    current_user: User = Depends(require_content_staff),
) -> Subject:
    return subject_service.get_subject(db, subject_id)


@router.get("/{subject_id}/blocks", response_model=list[ContentBlockResponse])
def list_blocks(
    subject_id: int = Path(ge=1), skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(require_content_staff),
) -> list[ContentBlock]:
    return subject_service.get_blocks(db, subject_id, skip, limit)


@router.post("/{subject_id}/blocks", response_model=ContentBlockResponse,
             status_code=status.HTTP_201_CREATED)
def create_block(
    payload: ContentBlockCreate, subject_id: int = Path(ge=1),
    db: Session = Depends(get_db), current_user: User = Depends(require_content_staff),
) -> ContentBlock:
    return subject_service.create_block(db, subject_id, payload)
