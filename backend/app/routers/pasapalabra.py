from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.pasapalabra import Selection, LocalStart, Answer, Command, Abandon, MatchState, CommandResponse
from app.services import pasapalabra as service

router = APIRouter(prefix="/pasapalabra", tags=["Pasapalabra"])


@router.post("/preparations")
def prepare(selection: Selection, db: Session = Depends(get_db), owner: User = Depends(get_current_user)):
    return service.prepare(db, selection)


@router.post("/local/start", response_model=MatchState, status_code=201)
def start(request: LocalStart, db: Session = Depends(get_db), owner: User = Depends(get_current_user)):
    return service.start_local(db, owner, request)


@router.get("/matches/{match_id}", response_model=MatchState)
def state(match_id: int, db: Session = Depends(get_db), owner: User = Depends(get_current_user)):
    return service.read_state(db, owner, match_id)


@router.get("/matches/{match_id}/result", response_model=MatchState)
def result(match_id: int, db: Session = Depends(get_db), owner: User = Depends(get_current_user)):
    return service.read_state(db, owner, match_id, result_only=True)


@router.post("/matches/{match_id}/answer", response_model=CommandResponse)
def answer(match_id: int, request: Answer, db: Session = Depends(get_db), owner: User = Depends(get_current_user)):
    return service.execute(db, owner, match_id, "answer", request)


@router.post("/matches/{match_id}/pass", response_model=CommandResponse)
def pass_word(match_id: int, request: Command, db: Session = Depends(get_db), owner: User = Depends(get_current_user)):
    return service.execute(db, owner, match_id, "pass", request)


@router.post("/matches/{match_id}/abandon", response_model=CommandResponse)
def abandon(match_id: int, request: Abandon, db: Session = Depends(get_db), owner: User = Depends(get_current_user)):
    return service.execute(db, owner, match_id, "abandon", request)
