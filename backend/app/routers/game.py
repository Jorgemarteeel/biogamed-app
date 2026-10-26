from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.game import GameHistoryDetail, GameHistorySummary, GameResultResponse, GameSessionStartResponse, GameSubmit
from app.services import game as game_service


router = APIRouter(prefix="/game", tags=["Game"])


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


@router.post("/start/{topic_id}", response_model=GameSessionStartResponse,
             status_code=status.HTTP_201_CREATED)
def start_game(
    topic_id: int = Path(ge=1),
    mode: str = "TRIVIAL",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameSessionStartResponse:
    return game_service.start_game_session(db, current_user, topic_id, game_mode=mode)


@router.post("/submit/{session_id}", response_model=GameResultResponse)
def submit_game(
    submission: GameSubmit,
    session_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameResultResponse:
    return game_service.submit_game_session(db, current_user, session_id, submission.answers)
