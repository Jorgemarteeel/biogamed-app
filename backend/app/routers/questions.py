from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_content_staff
from app.models import Question, User
from app.schemas.question import QuestionCreate, QuestionResponse, QuestionStateUpdate, QuestionSynonymsUpdate
from app.services import question as question_service


def private_response(response: Response):
    response.headers["Cache-Control"] = "no-store"

router = APIRouter(prefix="/questions", tags=["Questions"], dependencies=[Depends(private_response)])


@router.patch("/{question_id}/accepted-answers", response_model=QuestionResponse)
def update_accepted_answers(
    payload: QuestionSynonymsUpdate,
    question_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_content_staff),
) -> Question:
    return question_service.update_accepted_answers(db, question_id, payload.accepted_answers)


@router.post("/", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(
    question: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_content_staff),
) -> Question:
    return question_service.create_question(db=db, question=question)


@router.get("/topic/{topic_id}", response_model=list[QuestionResponse])
def get_questions_by_topic(
    topic_id: int = Path(ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_content_staff),
) -> list[Question]:
    # This management response includes solutions, so it requires a staff role.
    return question_service.get_questions_by_topic(
        db=db, topic_id=topic_id, skip=skip, limit=limit
    )


@router.get("/catalog")
def catalog(mode: str | None = Query(None, pattern="^(INMUNOQUEST|PASAPALABRA|TRIVIAL)$"),
            subject_id: int | None = Query(None, gt=0), block_id: int | None = Query(None, gt=0), category_id: int | None = Query(None, gt=0),
            difficulty: int | None = Query(None, ge=1, le=4), difficulty_unknown: bool = False,
            state: str = Query("all", pattern="^(all|active|retired)$"), bank: str | None = Query(None, pattern="^(LYMPHOCYTE|MACROPHAGE|SPLEEN|FLASK|DNA)$"),
            classification: str = Query("all", pattern="^(all|unassigned|uncategorized)$"),
            skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
            db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    from app.services.question_catalog import catalog as query
    return query(db, mode=mode, subject_id=subject_id, block_id=block_id, category_id=category_id, difficulty=difficulty,
                 difficulty_unknown=difficulty_unknown, state=state, bank=bank, classification=classification, skip=skip, limit=limit)


@router.get("/catalog/open")
def open_catalog(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    from app.services.question_catalog import catalog
    return catalog(db, mode="INMUNOQUEST", skip=skip, limit=limit)["items"]


@router.put("/manage/{question_id}")
def edit_question(question_id: int, payload: QuestionCreate, db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    from sqlalchemy import select
    from fastapi import HTTPException
    from app.services.question_catalog import academic_destination, public_staff_row
    # Lock the destination before the question, matching imports/manual creation.
    existing = db.get(Question, question_id)
    if existing is None: raise HTTPException(404, "La pregunta no existe.")
    academic = academic_destination(db, payload.subject_id, payload.block_id, payload.category_id)
    for destination in sorted({existing.category_id or 0, academic["category_id"] or 0}):
        question_service.lock_question_destination(db, destination or None)
    q = db.scalar(select(Question).where(Question.id == question_id).with_for_update().execution_options(populate_existing=True))
    if q is None: raise HTTPException(404, "La pregunta no existe.")
    academic = academic_destination(db, payload.subject_id, payload.block_id, payload.category_id)
    if q.question_type != payload.question_type: raise HTTPException(422, "No se puede cambiar el formato.")
    if payload.topic_id: question_service._require_topic(db, payload.topic_id)
    for k, v in {**question_service._question_values(payload), **academic}.items(): setattr(q, k, v)
    db.commit()
    return public_staff_row(q)


@router.put("/manage/{question_id}/state", response_model=QuestionResponse)
def state_question(question_id: int, payload: QuestionStateUpdate, db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    from sqlalchemy import select
    from fastapi import HTTPException
    q = db.scalar(select(Question).where(Question.id == question_id).with_for_update())
    if q is None: raise HTTPException(404, "La pregunta no existe.")
    q.is_active = payload.is_active
    db.commit()
    return q


@router.get("/destinations")
def destinations(kind: str = Query(..., pattern="^(subject|block|category)$"), subject_id: int | None = Query(None, gt=0),
                 block_id: int | None = Query(None, gt=0), selected_id: int | None = Query(None, gt=0), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100),
                 db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    from sqlalchemy import select, func
    from app.models import Subject, ContentBlock, Category
    from app.services.question_catalog import academic_destination
    resolved = academic_destination(db, subject_id, block_id)
    if kind == "subject":
        stmt = select(Subject.id, Subject.name)
    elif kind == "block":
        stmt = select(ContentBlock.id, ContentBlock.name, ContentBlock.subject_id, Subject.name.label("subject_name")).join(Subject, ContentBlock.subject_id == Subject.id)
        if resolved["subject_id"]: stmt = stmt.where(ContentBlock.subject_id == resolved["subject_id"])
    else:
        stmt = select(Category.id, Category.name, Category.block_id, ContentBlock.subject_id, Subject.name.label("subject_name"), ContentBlock.name.label("block_name")).outerjoin(ContentBlock, Category.block_id == ContentBlock.id).outerjoin(Subject, ContentBlock.subject_id == Subject.id)
        if resolved["subject_id"]: stmt = stmt.where(ContentBlock.subject_id == resolved["subject_id"])
        if resolved["block_id"]: stmt = stmt.where(Category.block_id == resolved["block_id"])
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    model = {"subject": Subject, "block": ContentBlock, "category": Category}[kind]
    def named(row):
        data = dict(row)
        if kind == "subject": data["display_name"] = data["name"]
        elif kind == "block": data["display_name"] = data["subject_name"] + " · " + data["name"]
        else: data["display_name"] = ((data["subject_name"] + " · " + data["block_name"] + " · ") if data["block_id"] else "Sin bloque · ") + data["name"]
        return data
    selected = db.execute(stmt.where(model.id == selected_id)).mappings().first() if selected_id else None
    return {"items": [named(row) for row in db.execute(stmt.order_by("id").offset(skip).limit(limit)).mappings()], "total": total,
            "selected": named(selected) if selected else None}
