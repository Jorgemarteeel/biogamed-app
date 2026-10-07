from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.game import GameResultResponse, GameSessionStartResponse, GameSubmit
from app.services import game as game_service


router = APIRouter(prefix="/game", tags=["Game"])


@router.post("/start/{topic_id}", response_model=GameSessionStartResponse,
             status_code=status.HTTP_201_CREATED)
def start_game(
    topic_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameSessionStartResponse:
    return game_service.start_game_session(db, current_user, topic_id)


@router.post("/submit/{session_id}", response_model=GameResultResponse)
def submit_game(
    submission: GameSubmit,
    session_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GameResultResponse:
    return game_service.submit_game_session(db, current_user, session_id, submission.answers)
