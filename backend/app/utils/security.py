import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext


SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "dev-only-change-this-secret-key-before-production",
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Configuramos bcrypt para calcular y verificar hashes de contraseñas.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """
    Calcula el hash de una contraseña con bcrypt y una sal aleatoria.
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compara la contraseña que escribe el usuario con el hash guardado en la BD.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    payload = data.copy()
    expires_at = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload["exp"] = expires_at
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
