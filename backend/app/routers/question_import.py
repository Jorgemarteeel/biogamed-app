from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_content_staff
from app.models import User
from app.schemas.question import ContentType
from app.services import question_import as service

router = APIRouter(prefix="/subjects/{subject_id}/blocks/{block_id}/categories/{category_id}/imports", tags=["Question imports"])

@router.get("/template")
def template(subject_id: int, block_id: int, category_id: int, mode: ContentType,
             db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    service.get_category(db, subject_id, block_id, category_id)
    return Response("\ufeff" + ";".join(service.COLUMNS[mode]) + "\r\n", media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="plantilla-{mode.lower()}.csv"', "Cache-Control": "no-store"})

@router.post("/validate")
async def validate(subject_id: int, block_id: int, category_id: int, mode: ContentType = Form(...), topic_id: int | None = Form(None, gt=0),
                   file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    return service.validate(db, user, await file.read(service.MAX_BYTES + 1), subject_id, block_id, category_id, topic_id, mode)

@router.post("/confirm")
async def confirm(subject_id: int, block_id: int, category_id: int, mode: ContentType = Form(...), topic_id: int | None = Form(None, gt=0),
                  proof: str = Form(...), operation_id: UUID = Form(...), file: UploadFile = File(...),
                  db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    return service.confirm(db, user, await file.read(service.MAX_BYTES + 1), subject_id, block_id, category_id, topic_id, mode, proof, operation_id)


@router.get("/receipts/{operation_id}")
def receipt(subject_id: int, block_id: int, category_id: int, operation_id: UUID, response: Response,
            db: Session = Depends(get_db), user: User = Depends(require_content_staff)):
    response.headers["Cache-Control"] = "no-store"
    return service.read_receipt(db, user, subject_id, block_id, category_id, operation_id)


# Same validation, proofs, receipts and transaction for optional academic destinations.
unclassified_router = APIRouter(prefix="/question-imports", tags=["Question imports"])

@unclassified_router.get("/template")
def open_template(mode: ContentType = "INMUNOQUEST", db: Session=Depends(get_db), user: User=Depends(require_content_staff)):
    return Response("\ufeff" + ";".join(service.COLUMNS[mode]) + "\r\n", media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="plantilla-{mode.lower()}.csv"', "Cache-Control":"no-store"})

@unclassified_router.post("/validate")
async def open_validate(file: UploadFile=File(...), mode: ContentType=Form("INMUNOQUEST"),
                        subject_id: int=Form(0, ge=0), block_id: int=Form(0, ge=0), category_id: int=Form(0, ge=0), topic_id: int | None=Form(None, gt=0),
                        db: Session=Depends(get_db), user: User=Depends(require_content_staff)):
    return service.validate(db,user,await file.read(service.MAX_BYTES+1),subject_id,block_id,category_id,topic_id,mode)

@unclassified_router.post("/confirm")
async def open_confirm(file: UploadFile=File(...), proof: str=Form(...), operation_id: UUID=Form(...), mode: ContentType=Form("INMUNOQUEST"),
                       subject_id: int=Form(0, ge=0), block_id: int=Form(0, ge=0), category_id: int=Form(0, ge=0), topic_id: int | None=Form(None, gt=0),
                       db: Session=Depends(get_db), user: User=Depends(require_content_staff)):
    return service.confirm(db,user,await file.read(service.MAX_BYTES+1),subject_id,block_id,category_id,topic_id,mode,proof,operation_id)

@unclassified_router.get("/receipts/{operation_id}")
def open_receipt(operation_id: UUID, response: Response, subject_id: int=0, block_id: int=0, category_id: int=0,
                 db: Session=Depends(get_db), user: User=Depends(require_content_staff)):
    response.headers["Cache-Control"]="no-store"
    return service.read_receipt(db,user,subject_id,block_id,category_id,operation_id)
