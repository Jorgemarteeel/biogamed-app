"""Preview and confirm user CSVs, rotate invitations and activate accounts."""
import csv
import hashlib
import io
import json
import re
import secrets
from collections import Counter
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, or_, select, text, update
from sqlalchemy.exc import IntegrityError

from app.models import User, UserRole
from app.models.user_import import UserImport
from app.services import activation_mail, student_import
from app.utils.academic_identity import normalize_academic_year, normalize_subject_code
from app.utils.auth_limits import positive
from app.utils.identity import normalize_dni, normalize_email
from app.utils.security import ALGORITHM, SECRET_KEY, get_password_hash

MAX_BYTES = 256 * 1024
MAX_ROWS = 100
COLUMNS = ("dni", "nombre", "correo")
STUDENT_COLUMNS = (*COLUMNS, "codigo_asignatura", "anio_academico")
ROLES = {
    "alumnado": (UserRole.TEACHER, UserRole.STUDENT),
    "profesorado": (UserRole.ADMIN, UserRole.TEACHER),
}
email_address = TypeAdapter(EmailStr)


def now():
    return datetime.now(timezone.utc)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def lock_users(db):
    # Shares the lock used for role updates so permissions can be rechecked after waiting.
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(702641903)"))


def require_manager(actor, target):
    if actor.role != ROLES[target][0]:
        raise HTTPException(403, "Tu rol no permite gestionar estas altas.")


def checked_manager(db, actor, target):
    actor_id, version = actor.id, actor.auth_version
    lock_users(db)
    current = db.get(User, actor_id, populate_existing=True)
    if current is None or current.hashed_password is None or current.auth_version != version:
        raise HTTPException(401, "La sesión ya no es válida.")
    require_manager(current, target)
    return current


def import_columns(target):
    return STUDENT_COLUMNS if target == "alumnado" else COLUMNS


def read_csv(raw, target):
    columns = import_columns(target)
    if not raw or len(raw) > MAX_BYTES:
        raise HTTPException(413, "El archivo debe contener datos y no superar 256 KiB.")
    try:
        source = raw.decode("utf-8-sig")
        if "\x00" in source:
            raise ValueError
        reader = csv.reader(io.StringIO(source, newline=""), delimiter=";", strict=True)
        if tuple(next(reader, [])) != columns:
            raise HTTPException(422, f"Usa la plantilla con la cabecera {';'.join(columns)}, en ese orden.")
        rows, errors, row_numbers = [], [], []
        for number, cells in enumerate(reader, 2):
            if number > MAX_ROWS + 1:
                raise HTTPException(413, "El archivo supera el máximo de 100 filas.")
            row_numbers.append(number)
            if len(cells) != len(columns):
                count = "cinco" if target == "alumnado" else "tres"
                errors.append({"row": number, "field": "archivo", "message": f"Se esperan {count} columnas."})
                continue
            raw_dni, name, raw_email, *destination = (field.strip() for field in cells)
            error_count = len(errors)
            try:
                dni = normalize_dni(raw_dni)
            except ValueError as error:
                errors.append({"row": number, "field": "dni", "message": str(error)})
            if not name or len(name) > 255 or any(ord(char) < 32 for char in name):
                errors.append({"row": number, "field": "nombre", "message": "Indica un nombre de 1 a 255 caracteres."})
            try:
                email = normalize_email(str(email_address.validate_python(raw_email)))
                if len(email) > 255:
                    raise ValueError
            except (ValidationError, ValueError):
                errors.append({"row": number, "field": "correo", "message": "Indica un correo válido."})
            if destination:
                for index, normalize in enumerate((normalize_subject_code, normalize_academic_year)):
                    try:
                        destination[index] = normalize(destination[index])
                    except ValueError as error:
                        errors.append({"row": number, "field": columns[index + 3], "message": str(error)})
            if len(errors) == error_count:
                rows.append((number, dni, name, email, *destination))
        if not row_numbers:
            raise HTTPException(422, "El archivo no contiene cuentas.")
        return rows, errors, row_numbers
    except (UnicodeError, csv.Error, ValueError):
        raise HTTPException(422, "CSV inválido. Usa UTF-8 y separador de punto y coma.") from None


def inspect_csv(db, raw, target):
    rows, errors, row_numbers = read_csv(raw, target)
    if target == "alumnado":
        return student_import.inspect(db, rows, errors, row_numbers)
    dnis = Counter(row[1] for row in rows)
    emails = Counter(row[3] for row in rows)
    matches = db.execute(select(User.dni, func.lower(User.email)).where(
        or_(User.dni.in_(list(dnis)), func.lower(User.email).in_(list(emails)))
    )).all()
    existing_dnis = {dni for dni, _ in matches}
    existing_emails = {email for _, email in matches}

    for number, dni, _, email in rows:
        for field, key, counts, existing in (
            ("dni", dni, dnis, existing_dnis), ("correo", email, emails, existing_emails)
        ):
            if counts[key] > 1:
                errors.append({"row": number, "field": field, "message": "Duplicado dentro del CSV."})
            if key in existing:
                errors.append({"row": number, "field": field, "message": "Coincide con una cuenta existente."})

    invalid_rows = {error["row"] for error in errors}
    preview = [
        {"row": number, "dni": "••••••" + dni[-3:], "name": name, "email": email}
        for number, dni, name, email in rows if number not in invalid_rows
    ]
    return rows, {
        "total": len(row_numbers),
        "valid": len(preview),
        "errors": sorted(errors, key=lambda error: error["row"]),
        "preview": preview,
    }


def reviewed_editions(rows):
    # Only the play decision needs to retain a snapshot of its starting point.
    editions = [(row.edition.id, row.enabled_edition_id) for row in rows]
    return digest(json.dumps(editions, separators=(",", ":")).encode("ascii"))


def preview(db, actor, target, raw):
    require_manager(actor, target)
    rows, result = inspect_csv(db, raw, target)
    claims = {
        "kind": "user-import",
        "actor": str(actor.id),
        "target": target,
        "digest": digest(raw),
        "exp": now() + timedelta(minutes=15),
    }
    if target == "alumnado":
        # A new preview can intentionally apply the same file again. A retry of
        # that preview still returns its original receipt.
        claims.update(mode="enable", jti=secrets.token_hex(16), review=reviewed_editions(rows))
    result["proof"] = None if result["errors"] else jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)
    return result


def invitation_for(user, ttl, issued_at):
    code = secrets.token_urlsafe(32)
    hashed = digest(code.encode("ascii"))
    user.activation_hash = hashed
    user.activation_expires_at = issued_at + timedelta(hours=ttl)
    user.invitation_attempted_at = issued_at
    user.invitation_sent_at = None
    return activation_mail.Invitation(user.id, user.email, code, hashed)


def record_delivery(db, invitations, ttl):
    delivered = activation_mail.send_invitations(invitations, ttl)
    for invitation in invitations:
        if invitation.user_id in delivered:
            db.execute(update(User).where(
                User.id == invitation.user_id, User.activation_hash == invitation.digest
            ).values(invitation_sent_at=now()))
    db.commit()
    return len(delivered)


def confirm(db, actor, target, raw, proof):
    require_manager(actor, target)
    if not raw or len(raw) > MAX_BYTES:
        raise HTTPException(413, "El archivo debe contener datos y no superar 256 KiB.")
    fingerprint = digest(raw)
    expected = {"kind": "user-import", "actor": str(actor.id), "target": target, "digest": fingerprint}
    try:
        claims = jwt.decode(proof, SECRET_KEY, algorithms=[ALGORITHM],
                            options={"verify_exp": False, "require": ["exp"]})
        if any(claims.get(key) != value for key, value in expected.items()) or type(claims["exp"]) is not int:
            raise ValueError
        if target == "alumnado":
            operation = claims.get("jti")
            if claims.get("mode") != "enable" or not isinstance(operation, str) or not re.fullmatch(r"[0-9a-f]{32}", operation):
                raise ValueError
            fingerprint = digest(f"enable:{operation}:{fingerprint}".encode("ascii"))
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(422, "Vuelve a validar este archivo con tu cuenta y el tipo de alta elegido.") from None

    actor = checked_manager(db, actor, target)
    previous = db.get(UserImport, (actor.id, target, fingerprint))
    if previous:
        result = {"count": previous.count, "sent": None, "replayed": True}
        if target == "alumnado":
            result.update(enrolled=previous.enrolled, already_enrolled=previous.already_enrolled)
        db.rollback()
        return result
    if claims["exp"] <= now().timestamp():
        raise HTTPException(422, "La validación caducó. Vuelve a validar el archivo.")
    rows, result = inspect_csv(db, raw, target)
    if result["errors"]:
        raise HTTPException(409, result)
    if target == "alumnado" and claims.get("review") != reviewed_editions(rows):
        raise HTTPException(409, "Cambió el año habilitado desde la vista previa. Vuelve a validar el archivo.")

    ttl = positive("BIOGAMED_ACTIVATION_TTL_HOURS", 24)
    enrollment_counts = {}
    try:
        if target == "alumnado":
            users, enrolled, already_enrolled = student_import.apply(db, rows)
            enrollment_counts = {"enrolled": enrolled, "already_enrolled": already_enrolled}
        else:
            users = [User(dni=dni, name=name, email=email, role=UserRole.TEACHER) for _, dni, name, email in rows]
            db.add_all(users)
            db.flush()
        issued_at = now()
        invitations = [invitation_for(user, ttl, issued_at) for user in users]
        db.add(UserImport(actor_id=actor.id, target=target, fingerprint=fingerprint, count=len(users),
                          **enrollment_counts))
        db.commit()
    except IntegrityError:
        db.rollback()
        _, conflicts = inspect_csv(db, raw, target)
        raise HTTPException(409, conflicts if conflicts["errors"] else "El lote cambió. Vuelve a validarlo.") from None

    sent = record_delivery(db, invitations, ttl) if invitations else 0
    return {"count": len(invitations), "sent": sent, "replayed": False, **enrollment_counts}


def pending(db, actor, target, skip, limit):
    require_manager(actor, target)
    where = (User.role == ROLES[target][1], User.hashed_password.is_(None))
    users = db.scalars(select(User).where(*where).order_by(User.name, User.id).offset(skip).limit(limit)).all()
    return {
        "total": db.scalar(select(func.count()).select_from(User).where(*where)),
        "items": [{"id": user.id, "name": user.name, "email": user.email, "sent": user.invitation_sent_at is not None}
                  for user in users],
    }


def resend(db, actor, target, user_id):
    checked_manager(db, actor, target)
    user = db.scalar(select(User).where(
        User.id == user_id, User.role == ROLES[target][1], User.hashed_password.is_(None)
    ).with_for_update())
    if user is None:
        raise HTTPException(404, "Cuenta pendiente no encontrada.")
    issued_at = now()
    cooldown = positive("BIOGAMED_INVITATION_COOLDOWN_SECONDS", 60)
    if user.invitation_attempted_at:
        previous = user.invitation_attempted_at
        if previous.tzinfo is None:
            previous = previous.replace(tzinfo=timezone.utc)
        if issued_at < previous + timedelta(seconds=cooldown):
            raise HTTPException(429, "Espera antes de reenviar la invitación.")
    ttl = positive("BIOGAMED_ACTIVATION_TTL_HOURS", 24)
    invitation = invitation_for(user, ttl, issued_at)
    db.commit()
    return {"sent": record_delivery(db, [invitation], ttl) == 1}


def activate(db, code, password):
    invalid = HTTPException(400, "El enlace de activación no es válido o ha caducado.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", code):
        raise invalid
    user = db.scalar(select(User).where(
        User.activation_hash == digest(code.encode("ascii")),
        User.activation_expires_at > now(),
        User.hashed_password.is_(None),
    ).with_for_update())
    if user is None:
        raise invalid
    user.hashed_password = get_password_hash(password)
    user.activation_hash = None
    user.activation_expires_at = None
    user.auth_version += 1
    db.commit()
