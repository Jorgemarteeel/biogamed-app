from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func, or_, text
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_admin
from app.models import User, UserRole
from app.models.role_change import RoleChange

class AdminAccount(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: UUID
    name: str
    email: str  # Preserve stored legacy addresses without revalidating them on read.
    role: UserRole

router=APIRouter(prefix='/admin/users',tags=['User administration'])
class RoleUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_role: UserRole
    role: UserRole

@router.get('')
def users(search:str=Query('',max_length=255),role:UserRole|None=None,skip:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),actor:User=Depends(require_admin)):
    criteria=[]
    if search.strip():
        pattern='%'+search.strip().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        criteria.append(or_(User.name.ilike(pattern,escape='\\'),User.email.ilike(pattern,escape='\\')))
    if role is not None:criteria.append(User.role==role)
    total=db.scalar(select(func.count()).select_from(User).where(*criteria))
    rows=db.execute(select(User.id,User.name,User.email,User.role).where(*criteria).order_by(func.lower(User.name),User.id).offset(skip).limit(limit)).mappings().all()
    return {'total':total,'items':[dict(r) for r in rows]}

def change_role(db:Session,actor_id:UUID,target_id:UUID,request:RoleUpdate):
    # All role writers share one transaction lock; re-read actor AFTER waiting.
    if db.bind.dialect.name=='postgresql':db.execute(text('SELECT pg_advisory_xact_lock(702641903)'))
    actor=db.get(User,actor_id,populate_existing=True)
    if actor is None or actor.role!=UserRole.ADMIN:raise HTTPException(403,'Ya no tienes permisos de administrador.')
    if actor_id==target_id:raise HTTPException(403,'No puedes cambiar tu propio rol.')
    target=db.get(User,target_id,populate_existing=True,with_for_update=True)
    if target is None:raise HTTPException(404,'Cuenta no encontrada.')
    if target.role!=request.expected_role:raise HTTPException(409,'El rol ha cambiado. Recarga la lista y confirma de nuevo.')
    if target.role==request.role:return target
    if target.role==UserRole.ADMIN and db.scalar(select(func.count()).select_from(User).where(User.role==UserRole.ADMIN))<=1:
        raise HTTPException(409,'Debe quedar al menos un administrador.')
    db.add(RoleChange(actor_id=actor_id,target_id=target_id,previous_role=target.role.value,new_role=request.role.value))
    target.role=request.role
    db.commit();db.refresh(target)
    return target

@router.patch('/{user_id}/role',response_model=AdminAccount)
def update_role(user_id:UUID,request:RoleUpdate,db:Session=Depends(get_db),actor:User=Depends(require_admin)):
    return change_role(db,actor.id,user_id,request)
