"""Interactive, explicit bootstrap of the first administrator (no promotion)."""
from getpass import getpass
from sqlalchemy import select, func
from app.database import SessionLocal
from app.models import User, UserRole
from app.schemas.user import UserCreate
from app.services.user_onboarding import lock_users
from app.utils.identity import normalize_dni, normalize_email
from app.utils.security import get_password_hash


def main():
    print("Creates a NEW first administrator in the configured DATABASE_URL; never promotes an existing account.")
    name = input("Name: ")
    email = normalize_email(input("Email: "))
    raw_dni = getpass("DNI: ")
    password = getpass("Password (8–255 characters): ")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match")
    try:
        data = UserCreate(name=name, email=email, password=password)
        dni = normalize_dni(raw_dni)
    except ValueError:
        raise SystemExit("Invalid name, email, DNI or password; no account created") from None
    with SessionLocal() as db:
        lock_users(db)
        if db.scalar(select(User.id).where(User.role == UserRole.ADMIN).limit(1)):
            raise SystemExit("Administrator already exists; use role management")
        if db.scalar(select(User.id).where(func.lower(User.email) == data.email).limit(1)) or db.scalar(select(User.id).where(User.dni == dni)):
            raise SystemExit("Account exists; bootstrap never promotes or changes it")
        db.add(User(name=data.name, email=data.email, dni=dni,
                    hashed_password=get_password_hash(data.password), role=UserRole.ADMIN))
        db.commit()
    print("First administrator created")


if __name__ == "__main__":
    main()
