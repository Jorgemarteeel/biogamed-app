"""Edition resolution from enabled enrollment; no client-selected academic year."""
from fastapi import HTTPException
from sqlalchemy import select, func
from app.models import AcademicEdition, Enrollment, Question, Subject, Topic, User
from app.services.user_onboarding import lock_users
from app.utils.identity import normalize_dni
from app.utils.security import verify_password


def is_academic(selection):
    return selection.subject_id is not None and selection.topic_id is not None and selection.block_id is None


def enabled_edition(db, actor, subject_id):
    row = db.execute(select(AcademicEdition, Subject).join(Subject).join(
        Enrollment, (Enrollment.edition_id == AcademicEdition.id) & (Enrollment.subject_id == Subject.id)
    ).where(Enrollment.student_id == actor.id, Enrollment.subject_id == subject_id, Enrollment.play_enabled.is_(True))).first()
    if row is None:
        raise HTTPException(403, "No tienes una matrícula habilitada para jugar en esta asignatura.")
    return row


def subjects(db, actor):
    return [dict(id=s.id, name=s.name, academic_year=e.academic_year) for e, s in db.execute(
        select(AcademicEdition, Subject).join(Subject).join(Enrollment, Enrollment.edition_id == AcademicEdition.id)
        .where(Enrollment.student_id == actor.id, Enrollment.play_enabled.is_(True)).order_by(Subject.name, Subject.id))]


def eligible(edition_id, topic_id, level):
    return select(Question).where(Question.edition_id == edition_id, Question.topic_id == topic_id,
        Question.difficulty == level, Question.is_active.is_(True), Question.question_type == "PASAPALABRA",
        Question.letter.is_not(None), Question.exact_word.is_not(None))


def themes(db, actor, subject_id):
    ed, subject = enabled_edition(db, actor, subject_id)
    counts = {(t, d): c for t, d, c in db.execute(select(Question.topic_id, Question.difficulty, func.count()).where(
        Question.edition_id == ed.id, Question.is_active.is_(True), Question.question_type == "PASAPALABRA",
        Question.letter.is_not(None), Question.exact_word.is_not(None)).group_by(Question.topic_id, Question.difficulty))}
    return dict(subject=subject.name, academic_year=ed.academic_year, topics=[dict(id=t.id, name=t.name,
        icon=t.icon_data, levels=[dict(level=n, available=counts.get((t.id,n),0)) for n in range(1,5)])
        for t in db.scalars(select(Topic).where(Topic.edition_id == ed.id).order_by(Topic.name, Topic.id))])


def resolve(db, actor, selection):
    ed, subject = enabled_edition(db, actor, selection.subject_id)
    topic = db.get(Topic, selection.topic_id)
    if topic is None or topic.edition_id != ed.id:
        raise HTTPException(409, "La temática no pertenece al curso que tienes habilitado. Vuelve a elegir la asignatura.")
    context = dict(subject_id=subject.id, subject_name=subject.name, edition_id=ed.id,
                   academic_year=ed.academic_year, topic_id=topic.id, topic_name=topic.name, difficulty=selection.difficulty)
    return eligible(ed.id, topic.id, selection.difficulty), context, topic


def same_edition(db, actor, selection, edition_id):
    ed, _ = enabled_edition(db, actor, selection.subject_id)
    if ed.id != edition_id:
        raise HTTPException(409, "Los dos participantes deben tener habilitado el mismo curso de esta asignatura.")


def companion(db, owner, request):
    # Called only behind the existing login limiter, before doing the expensive hash.
    try:
        dni = normalize_dni(request.guest_dni or "")
    except ValueError:
        raise HTTPException(400, "DNI o contraseña del acompañante incorrectos.") from None
    user = db.scalar(select(User).where(User.dni == dni))
    if user is None or user.hashed_password is None or request.guest_password is None or not verify_password(request.guest_password.get_secret_value(), user.hashed_password):
        raise HTTPException(400, "DNI o contraseña del acompañante incorrectos.")
    if user.id == owner.id:
        raise HTTPException(409, "El acompañante debe confirmar con una cuenta distinta de la del anfitrión.")
    return user
