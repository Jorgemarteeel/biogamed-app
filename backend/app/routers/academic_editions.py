from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.database import get_db
from app.dependencies import get_current_user
from app.models import AcademicEdition, Enrollment, Subject, User, UserRole
from app.services.enrollment_access import enable_for_play
from app.services.user_onboarding import checked_manager, require_manager
from app.utils.academic_identity import normalize_academic_year, normalize_subject_code


router = APIRouter(prefix="/academic-editions", tags=["Ediciones académicas"])


def require_teacher(actor: User = Depends(get_current_user)) -> User:
    require_manager(actor, "alumnado")
    return actor


class EditionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_id: int = Field(gt=0)
    subject_code: str | None = Field(default=None, max_length=32)
    academic_year: str = Field(max_length=9)

    @field_validator("subject_code")
    @classmethod
    def validate_code(cls, value):
        return normalize_subject_code(value) if value is not None else None

    @field_validator("academic_year")
    @classmethod
    def validate_year(cls, value):
        return normalize_academic_year(value)


class EnableEnrollment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_edition_id: int | None = Field(gt=0)


@router.get("/subjects")
def list_subjects(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
                  db: Session = Depends(get_db), actor: User = Depends(require_teacher)):
    subjects = db.execute(
        select(Subject.id, Subject.name, Subject.code).order_by(Subject.name, Subject.id)
        .offset(skip).limit(limit + 1)
    ).mappings().all()
    return {"items": [dict(row) for row in subjects[:limit]], "has_more": len(subjects) > limit}


@router.get("")
def list_editions(skip: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100),
                  db: Session = Depends(get_db), actor: User = Depends(require_teacher)):
    rows = db.execute(
        select(AcademicEdition.id, AcademicEdition.academic_year, Subject.name.label("subject_name"),
               Subject.code.label("subject_code"))
        .join(Subject, AcademicEdition.subject_id == Subject.id)
        .order_by(Subject.name, AcademicEdition.academic_year.desc(), AcademicEdition.id)
        .offset(skip).limit(limit + 1)
    ).mappings().all()
    return {"items": [dict(row) for row in rows[:limit]], "has_more": len(rows) > limit}


@router.post("", status_code=201)
def create_edition(payload: EditionCreate, db: Session = Depends(get_db), actor: User = Depends(require_teacher)):
    checked_manager(db, actor, "alumnado")
    subject = db.get(Subject, payload.subject_id, with_for_update=True)
    if subject is None:
        raise HTTPException(404, "No existe la asignatura indicada.")
    if subject.code is None and payload.subject_code is None:
        raise HTTPException(422, "Asigna un código a la asignatura antes de crear su primera edición.")
    if subject.code is not None and payload.subject_code not in (None, subject.code):
        raise HTTPException(409, "La asignatura ya tiene un código distinto.")
    if subject.code is None:
        subject.code = payload.subject_code
    if db.scalar(select(AcademicEdition.id).where(
        AcademicEdition.subject_id == subject.id, AcademicEdition.academic_year == payload.academic_year
    )) is not None:
        raise HTTPException(409, "Ya existe una edición de esa asignatura para el año indicado.")
    edition = AcademicEdition(subject_id=subject.id, academic_year=payload.academic_year)
    db.add(edition)
    try:
        db.flush()
        result = {"id": edition.id, "academic_year": edition.academic_year,
                  "subject_name": subject.name, "subject_code": subject.code}
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "El código ya pertenece a otra asignatura o la edición ya existe.") from None
    return result


@router.get("/{edition_id}/enrollments")
def list_enrollments(edition_id: int, skip: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100),
                     db: Session = Depends(get_db), actor: User = Depends(require_teacher)):
    edition = db.execute(
        select(AcademicEdition.id, AcademicEdition.academic_year, Subject.name.label("subject_name"),
               Subject.code.label("subject_code")).join(Subject, AcademicEdition.subject_id == Subject.id)
        .where(AcademicEdition.id == edition_id)
    ).mappings().one_or_none()
    if edition is None:
        raise HTTPException(404, "No existe la edición indicada.")
    active = aliased(Enrollment)
    active_edition = aliased(AcademicEdition)
    rows = db.execute(
        select(User.id, User.name, User.email, Enrollment.play_enabled,
               active.edition_id.label("enabled_edition_id"), active_edition.academic_year.label("enabled_year"))
        .select_from(Enrollment)
        .join(User, User.id == Enrollment.student_id)
        .outerjoin(active, (active.student_id == User.id) & (active.subject_id == Enrollment.subject_id)
                   & active.play_enabled.is_(True))
        .outerjoin(active_edition, active_edition.id == active.edition_id)
        .where(Enrollment.edition_id == edition_id, User.role == UserRole.STUDENT)
        .order_by(User.name, User.id).offset(skip).limit(limit + 1)
    ).mappings().all()
    return {"edition": dict(edition), "items": [dict(row) for row in rows[:limit]], "has_more": len(rows) > limit}


@router.put("/{edition_id}/enrollments/{student_id}/play")
def enable_enrollment(edition_id: int, student_id: UUID, payload: EnableEnrollment,
                      db: Session = Depends(get_db), actor: User = Depends(require_teacher)):
    checked_manager(db, actor, "alumnado")
    target = db.get(Enrollment, (student_id, edition_id))
    user = db.get(User, student_id)
    if target is None or user is None or user.role != UserRole.STUDENT:
        raise HTTPException(404, "No existe esa matrícula para una cuenta de alumnado.")
    if target.play_enabled:
        return {"enabled_edition_id": edition_id}
    active = db.scalar(select(Enrollment.edition_id).where(
        Enrollment.student_id == student_id, Enrollment.subject_id == target.subject_id,
        Enrollment.play_enabled.is_(True),
    ))
    if active != payload.expected_edition_id:
        raise HTTPException(409, "La edición habilitada ha cambiado. Actualiza el listado antes de decidir.")
    enable_for_play(db, target)
    db.commit()
    return {"enabled_edition_id": edition_id}
