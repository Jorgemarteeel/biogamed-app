"""Edition-scoped question management and one mixed CSV workflow."""
import base64
import csv
import hashlib
import io
import json
import struct
from collections import Counter
from datetime import timedelta
from uuid import UUID

import jwt
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import func, select, delete

from app.models import AcademicEdition, Question, Subject, Topic
from app.models.academic_edition import EditionBoardTopic
from app.models.question_import import QuestionImport
from app.schemas.question import QuestionCreate
from app.services import question_import as imports
from app.services.question import build_question, lock_question_destination
from app.utils.security import SECRET_KEY, ALGORITHM

BANKS = [("LYMPHOCYTE", "Linfocito"), ("MACROPHAGE", "Macrófago"), ("SPLEEN", "Bazo"), ("FLASK", "Matraz"), ("DNA", "ADN")]
COLUMNS = ["juego", "dificultad", "enunciado", "respuesta_referencia", "referencia_apuntes", "letra", "solucion", "alternativas"]


class TopicInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def clean(self):
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("El nombre no puede estar vacío.")
        return self


class ContentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_type: str
    difficulty: int = Field(strict=True, ge=1, le=4)
    text: str = Field(min_length=1, max_length=10000)
    reference_answer: str | None = Field(default=None, max_length=10000)
    note_reference: str | None = Field(default=None, max_length=120)
    letter: str | None = None
    exact_word: str | None = None
    accepted_answers: list[str] | None = None

    @model_validator(mode="after")
    def validate_content(self):
        if self.question_type == "PASAPALABRA":
            QuestionCreate(**self.model_dump(), topic_id=1)
        elif self.question_type == "INMUNOQUEST":
            if not self.text.strip() or not (self.reference_answer or "").strip():
                raise ValueError("Indica enunciado y respuesta de referencia.")
            if any(value is not None for value in (self.letter, self.exact_word, self.accepted_answers)):
                raise ValueError("Trivial no admite letra, solución de Pasapalabra ni alternativas.")
        else:
            raise ValueError("Juego debe ser INMUNOQUEST o PASAPALABRA.")
        return self


def edition(db, edition_id):
    row = db.execute(select(AcademicEdition, Subject).join(Subject).where(AcademicEdition.id == edition_id)).first()
    if not row:
        raise HTTPException(404, "La edición no existe.")
    return row


def theme(db, edition_id, topic_id):
    edition(db, edition_id)
    result = db.scalar(select(Topic).where(Topic.id == topic_id, Topic.edition_id == edition_id))
    if result is None:
        raise HTTPException(404, "La temática no pertenece a esta edición.")
    return result


def topic_row(topic):
    return dict(id=topic.id, name=topic.name, description=topic.description, icon=topic.icon_data)


def save_topic(db, edition_id, payload, topic_id=None):
    edition(db, edition_id)
    lock_question_destination(db, None)
    duplicate = db.scalar(select(Topic.id).where(Topic.edition_id == edition_id, func.lower(Topic.name) == payload.name.lower()))
    if duplicate is not None and duplicate != topic_id:
        raise HTTPException(409, "Ya existe una temática con ese nombre en esta edición.")
    topic = theme(db, edition_id, topic_id) if topic_id else Topic(edition_id=edition_id)
    topic.name, topic.description = payload.name, payload.description
    db.add(topic)
    db.commit()
    return topic_row(topic)


def icon(db, edition_id, topic_id, raw):
    topic = theme(db, edition_id, topic_id)
    if len(raw) > 512 * 1024 or len(raw) < 33 or raw[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR":
        raise HTTPException(422, "Selecciona una imagen PNG de hasta 512 KiB.")
    width, height = struct.unpack(">II", raw[16:24])
    if not 1 <= width <= 1024 or not 1 <= height <= 1024:
        raise HTTPException(422, "La imagen debe medir como máximo 1024 × 1024 píxeles.")
    topic.icon_data = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
    db.commit()
    return topic_row(topic)


def question_values(payload, topic_id, edition_id, subject_id):
    values = payload.model_dump()
    if payload.question_type == "PASAPALABRA":
        validated = QuestionCreate(**values, topic_id=topic_id)
        question = build_question(validated, academic={"subject_id": subject_id})
        question.edition_id = edition_id
        return question
    # Bank belongs to the edition's board mapping, never inferred from names.
    return Question(**values, topic_id=topic_id, edition_id=edition_id, subject_id=subject_id)


def question_row(q):
    return {"id": q.id, "is_active": q.is_active, **{
        field: getattr(q, field) for field in ContentInput.model_fields
    }}


def save_question(db, edition_id, topic_id, payload, question_id=None):
    theme(db, edition_id, topic_id)
    lock_question_destination(db, None)
    ed, _ = edition(db, edition_id)
    fresh = question_values(payload, topic_id, edition_id, ed.subject_id)
    if question_id:
        q = db.scalar(select(Question).where(Question.id == question_id, Question.edition_id == edition_id, Question.topic_id == topic_id))
        if q is None:
            raise HTTPException(404, "La pregunta no pertenece a esta temática.")
        if q.question_type != payload.question_type:
            raise HTTPException(422, "Conserva el juego de la pregunta.")
        for field in ContentInput.model_fields:
            setattr(q, field, getattr(fresh, field))
        q.correct_answer = fresh.correct_answer
    else:
        q = fresh
        db.add(q)
    db.commit()
    return question_row(q)


def board(db, edition_id):
    edition(db, edition_id)
    mappings = {r.bank: r.topic_id for r in db.scalars(select(EditionBoardTopic).where(EditionBoardTopic.edition_id == edition_id))}
    topics = {t.id: t for t in db.scalars(select(Topic).where(Topic.edition_id == edition_id))}
    counts = {(t, level): count for t, level, count in db.execute(select(Question.topic_id, Question.difficulty, func.count()).where(
        Question.edition_id == edition_id, Question.question_type == "INMUNOQUEST", Question.is_active.is_(True)
    ).group_by(Question.topic_id, Question.difficulty))}
    return {"slots": [{"bank": bank, "label": label, "topic_id": mappings.get(bank),
                      "missing_icon": not topics[mappings[bank]].icon_data if bank in mappings else True,
                      "decks": [{"level": n, "count": counts.get((mappings.get(bank), n), 0)} for n in range(1, 5)]}
                     for bank, label in BANKS], "can_start": False}


def save_board(db, edition_id, mappings):
    edition(db, edition_id)
    if set(mappings) - {b for b, _ in BANKS}:
        raise HTTPException(422, "Tipo de casilla desconocido.")
    ids = [i for i in mappings.values() if i is not None]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "Selecciona cinco temáticas distintas. Puedes dejar casillas pendientes.")
    for topic_id in ids:
        theme(db, edition_id, topic_id)
    lock_question_destination(db, None)
    db.execute(delete(EditionBoardTopic).where(EditionBoardTopic.edition_id == edition_id))
    db.add_all([EditionBoardTopic(edition_id=edition_id, bank=b, topic_id=t) for b, t in mappings.items() if t is not None])
    db.commit()
    return board(db, edition_id)


def parse(db, edition_id, topic_id, raw):
    ed, subject = edition(db, edition_id)
    fixed = theme(db, edition_id, topic_id) if topic_id else None
    topics = {t.name: t for t in db.scalars(select(Topic).where(Topic.edition_id == edition_id))}
    if not raw or len(raw) > imports.MAX_BYTES:
        raise HTTPException(413, "Selecciona un CSV de hasta 2 MiB.")
    headers = (["tematica"] if fixed is None else []) + COLUMNS
    try:
        reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), delimiter=";", strict=True)
        actual = next(reader)
        if actual != headers:
            missing = set(headers) - set(actual)
            unknown = set(actual) - set(headers)
            repeated = [h for h, c in Counter(actual).items() if c > 1]
            raise ValueError("Cabeceras incorrectas. Ausentes: " + ", ".join(sorted(missing))[:200] +
                             ". Desconocidas: " + ", ".join(sorted(unknown))[:200] +
                             ". Repetidas: " + ", ".join(repeated)[:200] + ". Descarga la plantilla de este destino.")
        rows, errors, total, seen = [], [], 0, {}
        existing = {(q.topic_id, q.question_type, imports.canonical(q)): q.id for q in db.scalars(select(Question).where(Question.edition_id == edition_id))}
        for n, cells in enumerate(reader, 2):
            total += 1
            if total > 500:
                raise HTTPException(413, "Máximo 500 preguntas. No se ha guardado ninguna.")
            if len(cells) != len(headers):
                errors.append({"row": n, "column": "archivo", "message": "Número de columnas incorrecto."})
                continue
            row = dict(zip(headers, cells))
            topic = fixed or topics.get(row["tematica"].strip())
            if topic is None:
                errors.append({"row": n, "column": "tematica", "message": "Crea primero esta temática en la edición seleccionada."})
                continue
            try:
                if row["dificultad"] not in ("1", "2", "3", "4"):
                    raise ValueError("dificultad: usa un nivel de 1 a 4.")
                game = row["juego"].strip().upper()
                if game == "TRIVIAL":
                    game = "INMUNOQUEST"  # CSV display name; never the historical options format.
                payload = dict(question_type=game, difficulty=int(row["dificultad"]), text=row["enunciado"],
                               reference_answer=row["respuesta_referencia"] or None, note_reference=row["referencia_apuntes"] or None,
                               letter=row["letra"] or None, exact_word=row["solucion"] or None,
                               accepted_answers=row["alternativas"].splitlines() if row["alternativas"] else None)
                validated = ContentInput(**payload)
                question = question_values(validated, topic.id, ed.id, ed.subject_id)
                key = (topic.id, game, imports.canonical(question))
                if key in seen or key in existing:
                    raise ValueError("contenido: duplicado exacto de " + (f"la fila {seen[key]}" if key in seen else f"la pregunta {existing[key]} (incluidas retiradas)"))
                seen[key] = n
                rows.append((n, topic, question))
            except ValidationError as exc:
                for err in exc.errors():
                    errors.append({"row": n, "column": ".".join(map(str, err["loc"])) or "contenido", "message": err["msg"]})
            except ValueError as exc:
                errors.append({"row": n, "column": str(exc).split(":")[0], "message": str(exc)})
        if total == 0:
            raise ValueError("El CSV no contiene preguntas.")
        return rows, errors, total, subject.name, ed.academic_year
    except (UnicodeError, csv.Error, ValueError, StopIteration) as exc:
        raise HTTPException(422, str(exc)[:800] or "CSV sin cabecera.") from None


def import_context(user, edition_id, topic_id, raw):
    return dict(kind="edition-content-v1", sub=str(user.id), edition=edition_id, topic=topic_id, sha=hashlib.sha256(raw).hexdigest())


def validate(db, user, edition_id, topic_id, raw):
    imports.staff(db, user)
    rows, errors, total, subject, year = parse(db, edition_id, topic_id, raw)
    groups = Counter((t.name, q.question_type) for _, t, q in rows)
    proof = None if errors else jwt.encode({**import_context(user, edition_id, topic_id, raw), "topics": [[n, t.id] for n, t, _ in rows], "exp": imports.now() + timedelta(minutes=15)}, SECRET_KEY, algorithm=ALGORITHM)
    return dict(total=total, valid=len(rows), errors=errors, proof=proof, subject=subject, year=year,
                groups=[dict(topic=t, game=g, count=c) for (t, g), c in groups.items()],
                preview=[dict(row=n, topic=t.name, game=q.question_type, text=q.text, level=q.difficulty) for n, t, q in rows])


def confirm(db, user, edition_id, topic_id, raw, proof, operation_id):
    imports.staff(db, user)
    edition(db, edition_id)
    expected = import_context(user, edition_id, topic_id, raw)
    try:
        claims = jwt.decode(proof, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False, "require": ["exp"]})
        if any(claims.get(k) != v for k, v in expected.items()):
            raise ValueError
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(422, "Valida de nuevo el archivo con este destino.") from None
    fingerprint = hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest()
    lock_question_destination(db, None)
    imports.staff(db, user)
    receipt = db.get(QuestionImport, (user.id, str(operation_id)))
    if receipt:
        if receipt.fingerprint != fingerprint:
            raise HTTPException(409, "La operación ya corresponde a otro archivo o destino.")
        return {"count": len(receipt.question_ids), "question_ids": receipt.question_ids}
    if claims["exp"] <= imports.now().timestamp():
        raise HTTPException(409, "La validación ha caducado.")
    rows, errors, _, _, _ = parse(db, edition_id, topic_id, raw)
    if errors:
        raise HTTPException(409, {"errors": errors})
    if claims.get("topics") != [[n, t.id] for n, t, _ in rows]:
        raise HTTPException(409, "Las temáticas han cambiado. Vuelve a validar el archivo.")
    try:
        db.add_all([q for _, _, q in rows])
        db.flush()
        ids = [q.id for _, _, q in rows]
        db.add(QuestionImport(owner_id=user.id, operation_id=str(operation_id), fingerprint=fingerprint, question_ids=ids))
        db.commit()
        return {"count": len(ids), "question_ids": ids}
    except Exception:
        db.rollback()
        raise

def read_receipt(db, user, edition_id, topic_id, operation_id):
    imports.staff(db, user)
    ed, subject = edition(db, edition_id)
    topic = theme(db, edition_id, topic_id) if topic_id else None
    result = dict(status="unknown", subject_id=subject.id, subject=subject.name, year=ed.academic_year,
                  topic=topic.name if topic else None)
    receipt = db.get(QuestionImport, (user.id, str(operation_id)))
    if receipt is None:
        return result
    rows = db.execute(select(Question.edition_id, Question.topic_id).where(Question.id.in_(receipt.question_ids))).all()
    if len(rows) != len(receipt.question_ids) or any(e != edition_id or (topic_id is not None and t != topic_id) for e, t in rows):
        return result
    return {**result, "status": "confirmed", "count": len(receipt.question_ids)}
