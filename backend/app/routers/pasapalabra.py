from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.pasapalabra import Selection, LocalStart, Answer, Command, Abandon, MatchState, CommandResponse
from app.services import pasapalabra as service
from app.services import pasapalabra_rooms as rooms
from app.schemas.pasapalabra import RoomCreate, RoomJoin, RoomAction, RoomState, RoomLeft

router = APIRouter(prefix="/pasapalabra", tags=["Pasapalabra"])


@router.post("/rooms", status_code=201, response_model=RoomState)
def create_room(request: RoomCreate, db: Session = Depends(get_db), owner: User = Depends(get_current_user)):
    return rooms.create(db, owner, request)


@router.post("/rooms/join", response_model=RoomState)
def join_room(request: RoomJoin, db: Session = Depends(get_db), owner: User = Depends(get_current_user)):
    return rooms.join(db, owner, request)


@router.get("/rooms/{room_id}", response_model=RoomState)
def room_state(room_id: int, db: Session = Depends(get_db), owner: User = Depends(get_current_user)):
    return rooms.read(db, owner, room_id)


@router.post("/rooms/{room_id}/{kind}", response_model=RoomState | RoomLeft)
def room_action(room_id: int, kind: str, request: RoomAction, db: Session = Depends(get_db), owner: User = Depends(get_current_user)):
    from fastapi import HTTPException
    if kind not in {"ready", "start", "leave", "cancel"}:
        raise HTTPException(404, "Acción no disponible.")
    return rooms.action(db, owner, room_id, kind, request)


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
