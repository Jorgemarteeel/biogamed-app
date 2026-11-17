"""Automatic availability, not a named activity or playable match."""
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_content_staff
from app.models import Question
from app.services.question_catalog import academic_destination

BANKS = [("LYMPHOCYTE", "Linfocito"), ("MACROPHAGE", "Macrófago"), ("SPLEEN", "Bazo"), ("FLASK", "Matraz"), ("DNA", "ADN")]
router = APIRouter(prefix="/inmunoquest", tags=["InmunoQuest availability"], dependencies=[Depends(require_content_staff)])

@router.get("/coverage")
def coverage(response: Response, subject_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    academic_destination(db, subject_id)
    response.headers["Cache-Control"] = "no-store"
    rows = db.execute(select(Question.bank, Question.difficulty, func.count()).where(
        Question.question_type == "INMUNOQUEST", Question.subject_id == subject_id,
        Question.is_active.is_(True), func.length(func.trim(Question.text)) > 0,
        func.length(func.trim(Question.reference_answer)) > 0,
        Question.difficulty.between(1, 4), Question.bank.in_([b for b, _ in BANKS]), Question.topic_id.is_(None),
    ).group_by(Question.bank, Question.difficulty))
    counts = {(b, n): count for b, n, count in rows}
    decks = [{"bank": b, "name": name, "difficulty": n, "available": counts.get((b, n), 0)} for b, name in BANKS for n in range(1, 5)]
    return {"subject_id": subject_id, "decks": decks, "empty_decks": sum(d["available"] == 0 for d in decks), "can_start": False,
            "reason": "Disponibilidad de contenido; no permite iniciar partidas ni acredita suficiencia pedagógica."}
