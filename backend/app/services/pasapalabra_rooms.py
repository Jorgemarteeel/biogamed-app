"""Private lobby lifecycle. All match rules live in the shared engine."""
from datetime import timedelta
import secrets
from uuid import uuid5, NAMESPACE_URL

from fastapi import HTTPException
from sqlalchemy import select

from app.models import User, Topic, Category
from app.models.pasapalabra import PasapalabraRoom as Room, RoomOperation, RoomJoinLimit
from app.schemas.pasapalabra import Selection, LocalStart
from app.services import pasapalabra as engine


def lock_actor(db, actor):
    # Consistent lock order: actor, then room, then match/question rows.
    db.expire_all()
    db.scalar(select(User).where(User.id == actor.id).with_for_update(key_share=True))


def expire(room, now):
    if room.status == "WAITING" and now >= engine.utc(room.expires_at):
        room.status = "EXPIRED"
        room.version += 1


def authorize(room, actor):
    if room is None or actor.id not in (room.owner_id, room.guest_id):
        raise HTTPException(404, "La sala no existe o ya no perteneces a ella.")


def view(db, room, actor, now):
    authorize(room, actor)
    return {"id": room.id, "version": room.version, "status": room.status,
            "self_position": 1 if actor.id == room.owner_id else 2,
            "configuration": room.configuration, "selection": room.selection,
            "code": room.code if room.status == "WAITING" else None,
            "expires_at": room.expires_at, "server_now": now, "match_id": room.match_id,
            "participants": [{"position": position, "name": db.get(User, user_id).name,
                              "ready": room.owner_ready if position == 1 else room.guest_ready}
                             for position, user_id in [(1, room.owner_id), (2, room.guest_id)] if user_id]}


def receipt(db, actor, operation_id, payload):
    previous = db.scalar(select(RoomOperation).where(RoomOperation.user_id == actor.id,
                                                     RoomOperation.operation_id == str(operation_id)))
    if previous and previous.payload != payload:
        raise HTTPException(409, {"code": "IDEMPOTENCY_CONFLICT"})
    return previous


def record(db, actor, operation_id, payload, room):
    db.add(RoomOperation(user_id=actor.id, operation_id=str(operation_id), payload=payload, room_id=room.id))


def read(db, actor, room_id):
    db.expire_all()
    room = db.scalar(select(Room).where(Room.id == room_id,
                                       (Room.owner_id == actor.id) | (Room.guest_id == actor.id)).with_for_update())
    authorize(room, actor)
    now = engine.server_now(db)
    expire(room, now)
    result = view(db, room, actor, now)
    db.commit()
    return result


def create(db, actor, request):
    lock_actor(db, actor)
    selection = request.model_dump(exclude={"operation_id"})
    payload = {"kind": "create", **selection}
    previous = receipt(db, actor, request.operation_id, payload)
    if previous:
        return read(db, actor, previous.room_id)
    engine.prepare(db, Selection(**selection))
    topic = db.get(Topic, request.topic_id)
    category = db.get(Category, request.category_id) if request.category_id else None
    now = engine.server_now(db)
    # 60 random bits, 12 unambiguous uppercase hex/base32 characters.
    code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(12))
    room = Room(owner_id=actor.id, code=code, selection=selection, created_at=now,
                expires_at=now + timedelta(minutes=30),
                configuration={"topic": topic.name, "category": category.name if category else "Todas, incluidas sin categoría",
                               "difficulty": request.difficulty, "difficulty_unknown": request.difficulty_unknown,
                               "questions_per_player": 20, "time_per_player_ms": 600000})
    db.add(room)
    db.flush()
    record(db, actor, request.operation_id, payload, room)
    result = view(db, room, actor, now)
    db.commit()
    return result


def join(db, actor, request):
    lock_actor(db, actor)
    payload = {"kind": "join", "code": request.code.strip().upper()}
    previous = receipt(db, actor, request.operation_id, payload)
    if previous:
        return read(db, actor, previous.room_id)
    now = engine.server_now(db)
    limit = db.get(RoomJoinLimit, actor.id)
    if limit is None:
        limit = RoomJoinLimit(user_id=actor.id, window_start=now, attempts=0)
        db.add(limit)
    if now >= engine.utc(limit.window_start) + timedelta(minutes=10):
        limit.window_start, limit.attempts = now, 0
    if limit.attempts >= 10:
        db.commit()
        raise HTTPException(429, {"code": "JOIN_RATE_LIMIT", "retry_after_seconds": 600}, headers={"Retry-After": "600"})
    limit.attempts += 1
    db.flush()
    room = db.scalar(select(Room).where(Room.code == payload["code"]).with_for_update())
    now = engine.server_now(db)
    error = None
    if room is None:
        error = "ROOM_UNAVAILABLE"
    else:
        expire(room, now)
        if room.status == "EXPIRED":
            error = "ROOM_EXPIRED"
        elif room.status == "CANCELLED":
            error = "ROOM_CANCELLED"
        elif room.status != "WAITING":
            error = "ROOM_UNAVAILABLE"
        elif room.owner_id == actor.id:
            error = "DISTINCT_ACCOUNT_REQUIRED"
        elif room.guest_id is not None and room.guest_id != actor.id:
            error = "ROOM_FULL"
    if error:
        db.commit()
        raise HTTPException(409 if error != "ROOM_UNAVAILABLE" else 404, {"code": error})
    if room.guest_id is None:
        room.guest_id = actor.id
        room.owner_ready = room.guest_ready = False
        room.version += 1
    record(db, actor, request.operation_id, payload, room)
    result = view(db, room, actor, now)
    db.commit()
    return result


def action(db, actor, room_id, kind, request):
    lock_actor(db, actor)
    payload = {"kind": kind, "room_id": room_id, "expected_version": request.expected_version}
    previous = receipt(db, actor, request.operation_id, payload)
    if previous and kind == "leave":
        db.commit()
        return {"id": room_id, "status": "LEFT"}
    room = db.scalar(select(Room).where(Room.id == room_id,
                                       (Room.owner_id == actor.id) | (Room.guest_id == actor.id)).with_for_update())
    authorize(room, actor)
    now = engine.server_now(db)
    expire(room, now)
    if previous:
        result = view(db, room, actor, now)
        db.commit()
        return result
    error = None
    if room.status != "WAITING":
        error = "ROOM_NOT_WAITING"
    elif room.version != request.expected_version:
        error = "STALE_VERSION"
    elif kind in {"start", "cancel"} and room.owner_id != actor.id:
        error = "OWNER_REQUIRED"
    elif kind == "leave" and room.guest_id != actor.id:
        error = "GUEST_REQUIRED"
    elif kind in {"ready", "start"} and room.guest_id is None:
        error = "TWO_PLAYERS_REQUIRED"
    elif kind == "start" and not (room.owner_ready and room.guest_ready):
        error = "BOTH_READY_REQUIRED"
    if error:
        version = room.version
        db.commit()
        raise HTTPException(409, {"code": error, "version": version})
    if kind == "ready":
        if actor.id == room.owner_id:
            room.owner_ready = True
        else:
            room.guest_ready = True
    elif kind == "cancel":
        room.status = "CANCELLED"
    elif kind == "leave":
        room.guest_id = None
        room.owner_ready = room.guest_ready = False
    elif kind == "start":
        owner, guest = db.get(User, room.owner_id), db.get(User, room.guest_id)
        start_request = LocalStart(**room.selection, guest_name=guest.name,
                                   operation_id=uuid5(NAMESPACE_URL, f"biogamed:room:{room.id}"))
        try:
            room.match_id = engine.start_shared(db, owner, start_request, online_guest=guest, auto_commit=False, start_before=room.expires_at)
        except HTTPException as exc:
            if isinstance(exc.detail, dict) and exc.detail.get("code") == "ROOM_EXPIRED":
                room.status = "EXPIRED"
                room.version += 1
                db.commit()
            raise
        room.status = "STARTED"
    room.version += 1
    record(db, actor, request.operation_id, payload, room)
    result = {"id": room.id, "status": "LEFT"} if kind == "leave" else view(db, room, actor, now)
    db.commit()
    return result
