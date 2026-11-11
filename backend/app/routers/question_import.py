from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_content_staff
from app.models import User
from app.schemas.question import QuestionType
from app.services import question_import as service

router = APIRouter(prefix="/subjects/{subject_id}/blocks/{block_id}/categories/{category_id}/imports", tags=["Question imports"])

@router.get("/template")
def template(subject_id: int, block_id: int, category_id: int, mode: QuestionType,
             db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    service.get_category(db, subject_id, block_id, category_id)
    return Response("\ufeff" + ";".join(service.COLUMNS[mode]) + "\r\n", media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="plantilla-{mode.lower()}.csv"', "Cache-Control": "no-store"})

@router.post("/validate")
async def validate(subject_id: int, block_id: int, category_id: int, mode: QuestionType = Form(...), topic_id: int = Form(..., gt=0),
                   file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    return service.validate(db, user, await file.read(service.MAX_BYTES + 1), subject_id, block_id, category_id, topic_id, mode)

@router.post("/confirm")
async def confirm(subject_id: int, block_id: int, category_id: int, mode: QuestionType = Form(...), topic_id: int = Form(..., gt=0),
                  proof: str = Form(...), operation_id: UUID = Form(...), file: UploadFile = File(...),
                  db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    return service.confirm(db, user, await file.read(service.MAX_BYTES + 1), subject_id, block_id, category_id, topic_id, mode, proof, operation_id)


@router.get("/receipts/{operation_id}")
def receipt(subject_id: int, block_id: int, category_id: int, operation_id: UUID, response: Response,
            db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    response.headers["Cache-Control"] = "no-store"
    return service.read_receipt(db, user, subject_id, block_id, category_id, operation_id)
