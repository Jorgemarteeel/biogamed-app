from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserRole
from app.schemas.user import UserCreate
from app.utils.security import get_password_hash


def get_user_by_email(db: Session, email: str) -> User | None:
    """Busca en la base de datos si ya existe alguien con este email"""
    statement = select(User).where(User.email == email)
    return db.scalar(statement)


def create_user(db: Session, user: UserCreate) -> User:
    """Cifra la contraseña y guarda el nuevo usuario en PostgreSQL"""
    hashed_password = get_password_hash(user.password)
    
    # Creamos el objeto de base de datos
    db_user = User(
        name=user.name,
        email=str(user.email),
        hashed_password=hashed_password,
        role=UserRole.STUDENT,
    )
    
    # Lo guardamos de verdad en PostgreSQL
    db.add(db_user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(db_user)
    return db_user
