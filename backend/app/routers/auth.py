from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.user import ActivationRequest, OwnNameUpdate, OwnPasswordUpdate, UserResponse
from app.services import user as user_service, user_onboarding
from app.utils.auth_limits import activation_limit, login_limit
from app.utils.identity import normalize_dni
from app.utils.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", include_in_schema=False)
def register_user():
    raise HTTPException(410, "El alta de cuentas se realiza mediante invitación.")


@router.post("/activate", dependencies=[Depends(activation_limit)])
def activate(request: ActivationRequest, db: Session = Depends(get_db)):
    user_onboarding.activate(db, request.code, request.password)
    return {"message": "Cuenta activada. Ya puedes iniciar sesión."}


@router.post("/login", dependencies=[Depends(login_limit)])
def login(
    credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    invalid = HTTPException(
        status_code=401, detail="DNI o contraseña incorrectos.", headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        dni = normalize_dni(credentials.username)
    except ValueError:
        raise invalid from None
    user = user_service.get_user_by_dni(db, dni)
    if user is None or user.hashed_password is None or not verify_password(credentials.password, user.hashed_password):
        raise invalid

    access_token = create_access_token(data={
        "sub": str(user.id), "email": user.email, "role": user.role.value, "auth_version": user.auth_version,
    })
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_own_name(request: OwnNameUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.name = request.name
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(user)
    return user


@router.post("/me/password")
def update_own_password(request: OwnPasswordUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from app.services.account import change_password
    change_password(db, user.id, user.auth_version, request)
    return {"message": "Contraseña cambiada. Todas las sesiones anteriores han quedado cerradas."}
