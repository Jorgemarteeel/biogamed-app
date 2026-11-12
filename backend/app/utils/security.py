import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError


SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "dev-only-change-this-secret-key-before-production",
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# bcrypt se conserva exclusivamente para verificar los hashes existentes.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, type=Type.ID)

def get_password_hash(password: str) -> str:
    """
    Calcula un hash Argon2id con una sal aleatoria, sin truncar la contraseña.
    """
    if not 8 <= len(password) <= 255:
        raise ValueError("La contraseña debe tener entre 8 y 255 caracteres.")
    return password_hasher.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compara la contraseña que escribe el usuario con el hash guardado en la BD.
    """
    if len(plain_password) > 255:
        return False
    try:
        if hashed_password.startswith("$argon2id$"):
            return password_hasher.verify(hashed_password, plain_password)
        return pwd_context.verify(plain_password, hashed_password)
    except (VerificationError, InvalidHashError, ValueError, UnicodeError):
        return False


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
