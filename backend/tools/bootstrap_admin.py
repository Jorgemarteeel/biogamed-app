"""Interactive, explicit bootstrap of the first administrator (no promotion)."""
from getpass import getpass
from sqlalchemy import select, text
from app.database import SessionLocal
from app.models import User, UserRole
from app.schemas.user import UserCreate
from app.utils.security import get_password_hash


def main():
    print("Creates a NEW first administrator in the configured DATABASE_URL; never promotes an existing account.")
    name = input("Name: ")
    email = input("Email: ")
    password = getpass("Password (8–255 characters): ")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords do not match")
    try:
        data = UserCreate(name=name, email=email, password=password)
    except ValueError:
        raise SystemExit("Invalid name, email or password; no account created") from None
    with SessionLocal() as db:
        db.execute(text("SELECT pg_advisory_xact_lock(741805196)"))
        if db.scalar(select(User.id).where(User.role == UserRole.ADMIN).limit(1)):
            raise SystemExit("Administrator already exists; use role management")
        if db.scalar(select(User.id).where(User.email == data.email)):
            raise SystemExit("Account exists; bootstrap never promotes or changes it")
        db.add(User(name=data.name, email=data.email, hashed_password=get_password_hash(data.password), role=UserRole.ADMIN))
        db.commit()
    print("First administrator created")


if __name__ == "__main__":
    main()
