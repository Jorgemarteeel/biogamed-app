import csv
import io
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_content_staff
from app.models import Question, Topic, User
from app.services import edition_content as service

def private_response(response: Response):
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(dependencies=[Depends(private_response)], prefix="/edition-content", tags=["Contenidos por edición"])


@router.get("/{edition_id}")
def overview(edition_id: int, db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    edition, subject = service.edition(db, edition_id)
    return dict(id=edition.id, year=edition.academic_year, subject=subject.name,
                topics=[service.topic_row(t) for t in db.scalars(select(Topic).where(Topic.edition_id == edition_id).order_by(Topic.name, Topic.id))],
                board=service.board(db, edition_id))


@router.post("/{edition_id}/topics")
def create_topic(edition_id: int, payload: service.TopicInput, db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    return service.save_topic(db, edition_id, payload)


@router.put("/{edition_id}/topics/{topic_id}")
def edit_topic(edition_id: int, topic_id: int, payload: service.TopicInput, db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    return service.save_topic(db, edition_id, payload, topic_id)


@router.post("/{edition_id}/topics/{topic_id}/icon")
async def upload_icon(edition_id: int, topic_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    return service.icon(db, edition_id, topic_id, await file.read(512 * 1024 + 1))


@router.get("/{edition_id}/questions")
def questions(edition_id: int, topic_id: int = Query(..., gt=0), skip: int = Query(0, ge=0),
              limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    service.theme(db, edition_id, topic_id)
    query = select(Question).where(Question.edition_id == edition_id, Question.topic_id == topic_id)
    return dict(total=db.scalar(select(func.count()).select_from(query.subquery())),
                items=[service.question_row(q) for q in db.scalars(query.order_by(Question.id).offset(skip).limit(limit))])


@router.post("/{edition_id}/topics/{topic_id}/questions")
def create_question(edition_id: int, topic_id: int, payload: service.ContentInput, db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    return service.save_question(db, edition_id, topic_id, payload)


@router.put("/{edition_id}/topics/{topic_id}/questions/{question_id}")
def edit_question(edition_id: int, topic_id: int, question_id: int, payload: service.ContentInput, db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    return service.save_question(db, edition_id, topic_id, payload, question_id)


@router.patch("/{edition_id}/topics/{topic_id}/questions/{question_id}")
def retire(edition_id: int, topic_id: int, question_id: int, active: bool,
           db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    service.theme(db, edition_id, topic_id)
    q = db.scalar(select(Question).where(Question.id == question_id, Question.edition_id == edition_id, Question.topic_id == topic_id))
    if q is None:
        raise HTTPException(404, "La pregunta no pertenece a esta temática.")
    q.is_active = active
    db.commit()
    return service.question_row(q)


@router.put("/{edition_id}/board")
def configure_board(edition_id: int, payload: dict[str, int | None], db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    return service.save_board(db, edition_id, payload)


@router.get("/{edition_id}/template")
def template(edition_id: int, topic_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    service.edition(db, edition_id)
    if topic_id:
        service.theme(db, edition_id, topic_id)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(([] if topic_id else ["tematica"]) + service.COLUMNS)
    return Response("\ufeff" + buffer.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="preguntas-edicion.csv"', "Cache-Control": "no-store"})


@router.post("/{edition_id}/validate")
async def validate(edition_id: int, file: UploadFile = File(...), topic_id: int | None = Form(None),
                   db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    return service.validate(db, user, edition_id, topic_id, await file.read(service.imports.MAX_BYTES + 1))


@router.post("/{edition_id}/confirm")
async def confirm(edition_id: int, file: UploadFile = File(...), topic_id: int | None = Form(None),
                  proof: str = Form(..., max_length=2048), operation_id: UUID = Form(...),
                  db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    return service.confirm(db, user, edition_id, topic_id, await file.read(service.imports.MAX_BYTES + 1), proof, operation_id)


@router.get("/legacy/pending")
def legacy(skip: int = Query(0, ge=0), db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    query = select(Question).where(Question.edition_id.is_(None))
    return dict(total=db.scalar(select(func.count()).select_from(query.subquery())),
                items=[dict(id=q.id, text=q.text, game=q.question_type, subject_id=q.subject_id, topic_id=q.topic_id,
                            block_id=q.block_id, category_id=q.category_id)
                       for q in db.scalars(query.order_by(Question.id).offset(skip).limit(20))])

@router.get("/{edition_id}/receipts/{operation_id}")
def receipt(edition_id: int, operation_id: UUID, topic_id: int | None = Query(None, gt=0),
            db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    return service.read_receipt(db, user, edition_id, topic_id, operation_id)
