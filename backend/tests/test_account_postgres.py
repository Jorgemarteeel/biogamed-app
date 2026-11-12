from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
from unittest.mock import patch
import pytest
from sqlalchemy import select,text
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from test_pasapalabra_postgres import postgres
from app.models import User
from app.schemas.user import OwnPasswordUpdate
from app.services.account import change_password
from app.utils.security import get_password_hash,verify_password


def test_concurrent_password_changes_cannot_overwrite(postgres):
    with Session(postgres) as db:
        u=User(name='Account race',email='account-race@example.com',hashed_password=get_password_hash('old-password-123'));db.add(u);db.commit();uid=u.id
    barrier=Barrier(2)
    def execute(index):
        with Session(postgres) as db:
            expected=db.get(User,uid).auth_version
            barrier.wait(timeout=10)
            new=f'new-password-{index}-ñ'
            try:
                change_password(db,uid,expected,OwnPasswordUpdate(current_password='old-password-123',new_password=new,confirmation=new));return index
            except HTTPException as e:
                db.rollback();return e.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(execute,[0,1]))
    assert result.count(409)==1
    winner=next(v for v in result if v!=409)
    with Session(postgres) as db:
        u=db.get(User,uid);assert u.auth_version==1 and verify_password(f'new-password-{winner}-ñ',u.hashed_password)
    with patch('app.database.engine',postgres):command.check(Config('alembic.ini'))
