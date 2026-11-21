"""Associate a verified DNI to one legacy account, preserving its internal ID."""
from getpass import getpass
from uuid import UUID

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.services.user_onboarding import lock_users
from app.utils.identity import normalize_dni


def assign(db, account_id, dni):
    dni = normalize_dni(dni)
    lock_users(db)
    user = db.scalar(select(User).where(User.id == account_id).with_for_update())
    if not user or user.hashed_password is None:
        raise ValueError("Se requiere una cuenta existente y activa.")
    if user.dni == dni:
        return
    if user.dni is not None or db.scalar(select(User.id).where(User.dni == dni)):
        raise ValueError("La cuenta ya tiene otro DNI o el DNI pertenece a otra cuenta.")
    user.dni = dni
    db.commit()


def main():
    print("Asocia un DNI verificado a una cuenta existente en la base configurada.")
    try:
        account_id = UUID(input("UUID de la cuenta verificada: ").strip())
        dni = getpass("DNI verificado: ")
        if normalize_dni(dni) != normalize_dni(getpass("Repite el DNI verificado: ")):
            raise ValueError("Los DNI no coinciden.")
        with SessionLocal() as db:
            assign(db, account_id, dni)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    print("Identidad asociada.")


if __name__ == "__main__":
    main()
