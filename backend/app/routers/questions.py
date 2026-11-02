from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_content_staff
from app.models import Question, User
from app.schemas.question import QuestionCreate, QuestionResponse, QuestionSynonymsUpdate
from app.services import question as question_service


router = APIRouter(prefix="/questions", tags=["Questions"])


@router.patch("/{question_id}/accepted-answers", response_model=QuestionResponse)
def update_accepted_answers(
    payload: QuestionSynonymsUpdate,
    question_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_content_staff),
) -> Question:
    return question_service.update_accepted_answers(db, question_id, payload.accepted_answers)


@router.post("/", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(
    question: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_content_staff),
) -> Question:
    return question_service.create_question(db=db, question=question)


@router.get("/topic/{topic_id}", response_model=list[QuestionResponse])
def get_questions_by_topic(
    topic_id: int = Path(ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_content_staff),
) -> list[Question]:
    # This management response includes solutions, so it requires a staff role.
    return question_service.get_questions_by_topic(
        db=db, topic_id=topic_id, skip=skip, limit=limit
    )
