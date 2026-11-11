"""Bounded, insert-only CSV imports; validation performs no writes."""
from collections import Counter
import csv
import hashlib
import io
import json
import unicodedata
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Question, User, UserRole
from app.models.question_import import QuestionImport
from app.schemas.question import CategoryQuestionCreate
from app.services.subject import get_category
from app.services.question import _require_topic, build_question, lock_question_destination
from app.utils.security import SECRET_KEY, ALGORITHM

MAX_BYTES = 2 * 1024 * 1024
COLUMNS = {
    "TRIVIAL": ["enunciado", "opcion_a", "opcion_b", "opcion_c", "opcion_d", "correcta", "dificultad"],
    "PASAPALABRA": ["enunciado", "letra", "solucion", "alternativas", "dificultad"],
}

def now():
    return datetime.now(timezone.utc)


def staff(db, user):
    db.refresh(user)
    if user.role not in (UserRole.ADMIN, UserRole.TEACHER):
        raise HTTPException(403, "Acceso exclusivo para docentes y administradores.")


def canonical(question):
    fields = ["text", "difficulty", "options", "correct_option_index", "letter", "exact_word", "accepted_answers"]
    data = {k: getattr(question, k) for k in fields}
    data["accepted_answers"] = data["accepted_answers"] or []
    def clean(value):
        if isinstance(value, str):
            return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value
    return json.dumps({k: clean(v) for k, v in data.items()}, ensure_ascii=False, sort_keys=True)


def parse(raw, mode, topic_id):
    if not raw or len(raw) > MAX_BYTES:
        raise HTTPException(413, "El archivo debe contener datos y no superar 2 MiB.")
    try:
        source = raw.decode("utf-8-sig")
        if "\x00" in source:
            raise ValueError("El archivo contiene un carácter nulo no admitido.")
        csv.field_size_limit(MAX_BYTES)
        reader = csv.reader(io.StringIO(source, newline=""), delimiter=";", strict=True)
        headers = next(reader)
        allowed = COLUMNS[mode]
        required = set(allowed) - {"dificultad", "alternativas"}
        if len(headers) != len(set(headers)) or not required.issubset(headers) or set(headers) - set(allowed):
            def labels(values):
                values = list(values)
                return ", ".join(repr(str(v)[:80]) for v in values[:12]) + (" …" if len(values) > 12 else "")
            missing = sorted(required - set(headers))
            unknown = sorted(set(headers) - set(allowed))
            repeated = sorted(h for h, count in Counter(headers).items() if count > 1)
            parts = []
            if missing: parts.append("Columnas obligatorias ausentes: " + labels(missing))
            if unknown: parts.append("Columnas desconocidas: " + labels(unknown))
            if repeated: parts.append("Cabeceras repetidas: " + labels(repeated))
            raise ValueError(". ".join(parts) + ". Descarga la plantilla del juego seleccionado.")
        rows, errors = [], []
        count = 0
        for number, cells in enumerate(reader, 2):
            count += 1
            if count > 500:
                raise HTTPException(413, "Máximo 500 preguntas; no se ha truncado el archivo.")
            if len(cells) != len(headers):
                errors.append({"row": number, "column": "archivo", "message": "Número de columnas incorrecto."}); continue
            row = dict(zip(headers, cells))
            try:
                level = row.get("dificultad", "").strip()
                if level not in ("", "1", "2", "3", "4"):
                    raise ValueError("dificultad: usa 1–4 o deja la celda vacía.")
                data = dict(text=row["enunciado"], topic_id=topic_id, question_type=mode, difficulty=int(level) if level else None)
                if mode == "TRIVIAL":
                    answer = row["correcta"].strip().upper()
                    if answer not in ("A", "B", "C", "D"):
                        raise ValueError("correcta: usa A, B, C o D.")
                    data.update(options=[row[f"opcion_{v}"] for v in "abcd"], correct_option_index="ABCD".index(answer))
                else:
                    data.update(letter=row["letra"], exact_word=row["solucion"], accepted_answers=row.get("alternativas", "").splitlines())
                rows.append((number, CategoryQuestionCreate(**data)))
            except ValidationError as exc:
                for error in exc.errors():
                    errors.append({"row": number, "column": ".".join(map(str, error["loc"])) or "contenido", "message": error["msg"]})
            except ValueError as exc:
                errors.append({"row": number, "column": "contenido", "message": str(exc)})
        if count == 0:
            raise ValueError("El archivo no contiene preguntas.")
        return rows, errors, count
    except (UnicodeError, csv.Error, ValueError, StopIteration) as exc:
        raise HTTPException(422, "CSV inválido: " + (str(exc) or "Faltan cabeceras.")) from exc


def duplicates(db, category_id, topic_id, mode, rows):
    existing = {}
    for q in db.scalars(select(Question).where(Question.category_id == category_id, Question.topic_id == topic_id, Question.question_type == mode)):
        existing.setdefault(canonical(q), []).append(q.id)
    seen, errors = {}, []
    for number, q in rows:
        key = canonical(q)
        if key in seen:
            errors.append({"row": number, "column": "contenido", "message": f"Duplicado del registro {seen[key]} del archivo."})
        if key in existing:
            errors.append({"row": number, "column": "contenido", "message": "Duplicado de preguntas existentes (incluidas retiradas): " + ", ".join(map(str, existing[key]))})
        seen.setdefault(key, number)
    return errors


def context(raw, user, subject_id, block_id, category_id, topic_id, mode):
    return dict(kind="question-import-v1", sub=str(user.id), subject=subject_id, block=block_id,
                category=category_id, topic=topic_id, mode=mode, sha=hashlib.sha256(raw).hexdigest())


def validate(db, user, raw, subject_id, block_id, category_id, topic_id, mode):
    staff(db, user)
    get_category(db, subject_id, block_id, category_id); _require_topic(db, topic_id)
    rows, errors, total = parse(raw, mode, topic_id)
    errors += duplicates(db, category_id, topic_id, mode, rows)
    proof = None if errors else jwt.encode({**context(raw, user, subject_id, block_id, category_id, topic_id, mode), "exp": now() + timedelta(minutes=15)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"total": total, "valid": len(rows), "errors": errors, "proof": proof,
            "preview": [{"row": n, **q.model_dump()} for n, q in rows]}


def confirm(db, user, raw, subject_id, block_id, category_id, topic_id, mode, proof, operation_id):
    staff(db, user)
    get_category(db, subject_id, block_id, category_id); _require_topic(db, topic_id)
    expected = context(raw, user, subject_id, block_id, category_id, topic_id, mode)
    try:
        claims = jwt.decode(proof, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False, "require": ["exp"]})
        if any(claims.get(k) != v for k, v in expected.items()):
            raise ValueError()
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(422, "La validación no corresponde al archivo, cuenta o destinos.")
    fingerprint = hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest()
    lock_question_destination(db, category_id)
    staff(db, user)
    key = (user.id, str(operation_id))
    def replay(receipt):
        if receipt.fingerprint != fingerprint:
            raise HTTPException(409, "El identificador de operación ya se utilizó con otro contenido.")
        return {"question_ids": receipt.question_ids, "count": len(receipt.question_ids)}
    receipt = db.get(QuestionImport, key)
    if receipt:
        return replay(receipt)
    if claims["exp"] <= now().timestamp():
        raise HTTPException(409, "Validación caducada. Vuelve a validar el archivo.")
    rows, errors, _ = parse(raw, mode, topic_id)
    errors += duplicates(db, category_id, topic_id, mode, rows)
    if errors:
        raise HTTPException(409, {"message": "No se importó ninguna pregunta. Revisa el archivo.", "errors": errors})
    try:
        questions = [build_question(q, category_id) for _, q in rows]
        db.add_all(questions); db.flush()
        receipt = QuestionImport(owner_id=user.id, operation_id=str(operation_id), fingerprint=fingerprint, question_ids=[q.id for q in questions])
        db.add(receipt); db.commit()
        return replay(receipt)
    except IntegrityError:
        db.rollback()
        receipt = db.get(QuestionImport, key)
        if receipt:
            return replay(receipt)
        raise
    except Exception:
        db.rollback()
        raise


def read_receipt(db, user, subject_id, block_id, category_id, operation_id):
    staff(db, user)
    get_category(db, subject_id, block_id, category_id)
    receipt = db.get(QuestionImport, (user.id, str(operation_id)))
    if receipt is None:
        return {"status": "unknown"}
    destinations = list(db.execute(select(Question.id, Question.category_id).where(Question.id.in_(receipt.question_ids))))
    if len(destinations) != len(receipt.question_ids) or any(row.category_id != category_id for row in destinations):
        return {"status": "unknown"}
    return {"status": "confirmed", "count": len(receipt.question_ids)}
