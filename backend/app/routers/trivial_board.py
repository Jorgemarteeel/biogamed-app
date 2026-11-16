"""Staff-only read-only review; POST computes coverage but never persists it."""
from typing import Literal
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_content_staff
from app.schemas.trivial_board import CoverageRequest
from app.services import trivial_board as service

router=APIRouter(prefix='/trivial-board',tags=['Trivial board review'],dependencies=[Depends(require_content_staff)])

@router.get('')
def definition(response: Response, db: Session=Depends(get_db)):
    response.headers['Cache-Control']='no-store'
    return {'board':service.board().model_dump(),'coverage':service.coverage(db,CoverageRequest())}

@router.get('/destinations')
def destinations(response: Response,kind:Literal['category','topic'],skip:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100),db:Session=Depends(get_db)):
    response.headers['Cache-Control']='no-store'
    return service.options(db,kind,skip,limit)

@router.post('/coverage')
def coverage(request: CoverageRequest,response: Response,db:Session=Depends(get_db)):
    response.headers['Cache-Control']='no-store'
    return service.coverage(db,request)
