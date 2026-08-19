from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services import user as user_service

# Creamos un "mini-servidor" (Router) solo para temas de autenticación
router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario en la plataforma.
    """
    # 1. Comprobamos si el email ya está en uso
    db_user = user_service.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Este correo electrónico ya está registrado.")
    
    # 2. Si todo va bien, creamos el usuario
    return user_service.create_user(db=db, user=user)
