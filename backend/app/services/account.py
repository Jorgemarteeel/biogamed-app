from fastapi import HTTPException
from sqlalchemy import select
from app.models import User
from app.utils.security import get_password_hash, verify_password


def change_password(db, user_id, expected_version, request):
    # The version used to authorize the request is captured before waiting.
    user = db.scalar(select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True))
    if user is None or user.auth_version != expected_version:
        raise HTTPException(409, "Las credenciales cambiaron. Inicia sesión de nuevo.")
    if request.new_password != request.confirmation:
        raise HTTPException(422, "La nueva contraseña y su confirmación no coinciden.")
    if not verify_password(request.current_password, user.hashed_password):
        raise HTTPException(400, "La contraseña actual no es correcta.")
    user.hashed_password = get_password_hash(request.new_password)
    user.auth_version += 1
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
