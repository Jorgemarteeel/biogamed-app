from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, Request, HTTPException
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services import user_onboarding
from app.utils.auth_limits import user_import_limit

router = APIRouter(prefix="/user-imports", tags=["Altas de usuarios"])
Target = Literal["alumnado", "profesorado"]


@router.get("/{target}/template")
def template(target: Target, actor: User = Depends(get_current_user)):
    user_onboarding.require_manager(actor, target)
    header = ";".join(user_onboarding.import_columns(target))
    return Response(f"\ufeff{header}\r\n", media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="{target}.csv"',
        "Cache-Control": "no-store",
    })


@router.post("/{target}/validate", dependencies=[Depends(user_import_limit)])
async def validate(target: Target, request: Request, file: UploadFile = File(...),
                   db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    user_onboarding.require_manager(actor, target)
    if "mode" in await request.form():
        raise HTTPException(422, "La importación habilita el curso indicado. Vuelve a validar sin seleccionar una modalidad.")
    return user_onboarding.preview(db, actor, target, await file.read(user_onboarding.MAX_BYTES + 1))


@router.post("/{target}/confirm", dependencies=[Depends(user_import_limit)])
async def confirm(target: Target, request: Request, proof: str = Form(..., max_length=2048), file: UploadFile = File(...),
                  db: Session = Depends(get_db),
                  actor: User = Depends(get_current_user)):
    user_onboarding.require_manager(actor, target)
    if "mode" in await request.form():
        raise HTTPException(422, "Vuelve a validar el archivo con el importador actualizado.")
    raw = await file.read(user_onboarding.MAX_BYTES + 1)
    return await run_in_threadpool(user_onboarding.confirm, db, actor, target, raw, proof)


@router.get("/{target}/pending")
def pending(target: Target, skip: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
            db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return user_onboarding.pending(db, actor, target, skip, limit)


@router.post("/{target}/pending/{user_id}/resend", dependencies=[Depends(user_import_limit)])
def resend(target: Target, user_id: UUID, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return user_onboarding.resend(db, actor, target, user_id)
