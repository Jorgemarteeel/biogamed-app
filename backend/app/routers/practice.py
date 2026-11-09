"""Student catalog: metadata only, independent of staff question contracts."""
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Question
from app.services import subject as service
from app.services.game_questions import playable_question_filter
from app.services.content_selection import resolve

router = APIRouter(prefix="/practice", tags=["Practice"], dependencies=[Depends(get_current_user)])

def metadata(item):
    return {"id": item.id, "name": item.name, "description": item.description}

def availability(db, category_id):
    return {mode: db.scalar(select(func.count()).select_from(Question).where(Question.category_id == category_id, playable_question_filter(mode))) for mode in ("TRIVIAL", "PASAPALABRA")}

@router.get("/subjects")
def subjects(skip: int = Query(0, ge=0), limit: int = Query(12, ge=1, le=100), db: Session = Depends(get_db)):
    return {"context": {}, "items": [metadata(x) for x in service.get_subjects(db, skip, limit)]}

@router.get("/subjects/{subject_id}/blocks")
def blocks(subject_id: int = Path(ge=1), skip: int = Query(0, ge=0), limit: int = Query(12, ge=1, le=100), db: Session = Depends(get_db)):
    subject = service.get_subject(db, subject_id)
    return {"context": {"subject": metadata(subject)}, "items": [metadata(x) for x in service.get_blocks(db, subject_id, skip, limit)]}

@router.get("/subjects/{subject_id}/blocks/{block_id}/categories")
def categories(subject_id: int = Path(ge=1), block_id: int = Path(ge=1), skip: int = Query(0, ge=0), limit: int = Query(12, ge=1, le=100), db: Session = Depends(get_db)):
    block = service.get_block(db, subject_id, block_id)
    return {"context": {"subject": metadata(block.subject), "block": metadata(block)}, "items": [{**metadata(x), "availability": availability(db, x.id)} for x in service.get_categories(db, subject_id, block_id, skip, limit)]}

@router.get("/subjects/{subject_id}/blocks/{block_id}/categories/{category_id}")
def category(subject_id: int = Path(ge=1), block_id: int = Path(ge=1), category_id: int = Path(ge=1), db: Session = Depends(get_db)):
    academic = resolve(db, None, category_id, subject_id, block_id)
    return {"academic": academic, "availability": availability(db, category_id)}
