from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.game import GameAvailabilityResponse, GameHistoryDetail, GameHistorySummary, GameProgressResponse, GameResultResponse, GameSessionStartResponse, GameSubmit
from app.schemas.question import QuestionType
from app.services import game as game_service


router = APIRouter(prefix="/game", tags=["Game"])


@router.get("/availability/{topic_id}", response_model=GameAvailabilityResponse)
def availability(
    topic_id: int = Path(ge=1), mode: QuestionType = Query(default="TRIVIAL"),
    category_id: int | None = Query(default=None, ge=1),
    difficulty: int | None = Query(default=None, ge=1, le=4),
    difficulty_unknown: bool = Query(default=False),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
) -> GameAvailabilityResponse:
    return game_service.get_game_availability(
        db, topic_id, mode, category_id, difficulty, difficulty_unknown,
    )


@router.get("/history", response_model=list[GameHistorySummary])
def history(
    skip: int = Query(default=0, ge=0), limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    return game_service.get_game_history(db, current_user, skip, limit)


@router.get("/history/{session_id}", response_model=GameHistoryDetail)
def history_detail(
    session_id: int = Path(ge=1), db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return game_service.get_game_history_detail(db, current_user, session_id)


@router.get("/progress", response_model=GameProgressResponse)
def progress(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> GameProgressResponse:
    return game_service.get_game_progress(db, current_user)


@router.post("/start/{topic_id}", response_model=GameSessionStartResponse,
             status_code=status.HTTP_201_CREATED)
def start_game(
    topic_id: int = Path(ge=1),
    mode: QuestionType = Query(default="TRIVIAL"),
    category_id: int | None = Query(default=None, ge=1),
    difficulty: int | None = Query(default=None, ge=1, le=4),
    difficulty_unknown: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameSessionStartResponse:
    return game_service.start_game_session(
        db, current_user, topic_id, game_mode=mode, category_id=category_id,
        difficulty=difficulty, difficulty_unknown=difficulty_unknown,
    )


@router.post("/submit/{session_id}", response_model=GameResultResponse)
def submit_game(
    submission: GameSubmit,
    session_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameResultResponse:
    return game_service.submit_game_session(db, current_user, session_id, submission.answers)
