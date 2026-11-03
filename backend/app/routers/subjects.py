from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_content_staff
from app.models import Category, ContentBlock, Question, Subject, User
from app.schemas.category import (BlockDetailResponse, CategoryCreate, CategoryDetailResponse, CategoryResponse,
                                  EmptyLinkRequest, UnassignedCategoryResponse)
from app.schemas.question import CategoryQuestionCreate, CategoryQuestionEdit, CategoryQuestionResponse, QuestionType
from app.schemas.content_block import ContentBlockCreate, ContentBlockResponse
from app.schemas.subject import SubjectCreate, SubjectResponse
from app.services import subject as subject_service
from app.services import question as question_service


router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.get("/categories/unassigned", response_model=list[UnassignedCategoryResponse])
def list_unassigned_categories(
    skip: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(require_content_staff),
) -> list[Category]:
    return subject_service.get_unassigned_categories(db, skip, limit)


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


@router.get("/{subject_id}/blocks/{block_id}", response_model=BlockDetailResponse)
def block_detail(
    subject_id: int = Path(ge=1), block_id: int = Path(ge=1),
    db: Session = Depends(get_db), current_user: User = Depends(require_content_staff),
) -> ContentBlock:
    return subject_service.get_block(db, subject_id, block_id)


@router.get("/{subject_id}/blocks/{block_id}/categories", response_model=list[CategoryResponse])
def list_categories(
    subject_id: int = Path(ge=1), block_id: int = Path(ge=1),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(require_content_staff),
) -> list[Category]:
    return subject_service.get_categories(db, subject_id, block_id, skip, limit)


@router.post("/{subject_id}/blocks/{block_id}/categories", response_model=CategoryResponse,
             status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate, subject_id: int = Path(ge=1), block_id: int = Path(ge=1),
    db: Session = Depends(get_db), current_user: User = Depends(require_content_staff),
) -> Category:
    return subject_service.create_category(db, subject_id, block_id, payload)


@router.get("/{subject_id}/blocks/{block_id}/categories/{category_id}",
            response_model=CategoryDetailResponse)
def category_detail(
    subject_id: int = Path(ge=1), block_id: int = Path(ge=1), category_id: int = Path(ge=1),
    db: Session = Depends(get_db), current_user: User = Depends(require_content_staff),
) -> Category:
    return subject_service.get_category(db, subject_id, block_id, category_id)


@router.post("/{subject_id}/blocks/{block_id}/categories/{category_id}/questions",
             response_model=CategoryQuestionResponse, status_code=status.HTTP_201_CREATED)
def create_category_question(
    payload: CategoryQuestionCreate,
    subject_id: int = Path(ge=1), block_id: int = Path(ge=1), category_id: int = Path(ge=1),
    db: Session = Depends(get_db), current_user: User = Depends(require_content_staff),
) -> Question:
    return question_service.create_category_question(db, subject_id, block_id, category_id, payload)


@router.put("/{subject_id}/blocks/{block_id}/categories/{category_id}/questions/{question_id}",
            response_model=CategoryQuestionResponse)
def edit_category_question(
    payload: CategoryQuestionEdit,
    subject_id: int = Path(ge=1), block_id: int = Path(ge=1), category_id: int = Path(ge=1),
    question_id: int = Path(ge=1), db: Session = Depends(get_db),
    current_user: User = Depends(require_content_staff),
) -> Question:
    return question_service.edit_category_question(db, subject_id, block_id, category_id, question_id, payload)


@router.get("/{subject_id}/blocks/{block_id}/categories/{category_id}/questions",
            response_model=list[CategoryQuestionResponse])
def list_category_questions(
    subject_id: int = Path(ge=1), block_id: int = Path(ge=1), category_id: int = Path(ge=1),
    skip: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=100),
    mode: QuestionType | None = Query(default=None),
    difficulty: int | None = Query(default=None, ge=1, le=4),
    difficulty_unknown: bool = Query(default=False),
    db: Session = Depends(get_db), current_user: User = Depends(require_content_staff),
) -> list[Question]:
    return question_service.get_questions_by_category(
        db, subject_id, block_id, category_id, skip, limit, mode,
        difficulty, difficulty_unknown,
    )


@router.put("/{subject_id}/blocks/{block_id}/categories/{category_id}", response_model=CategoryResponse)
def link_category(
    payload: EmptyLinkRequest, subject_id: int = Path(ge=1), block_id: int = Path(ge=1),
    category_id: int = Path(ge=1), db: Session = Depends(get_db),
    current_user: User = Depends(require_content_staff),
) -> Category:
    return subject_service.link_category(db, subject_id, block_id, category_id)
