from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from sqlalchemy import select,func,text
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config
from test_pasapalabra_postgres import postgres
from test_content_metadata_editing import hierarchy
from test_question_import import raw,setup
from app.models import User,Topic,Question,UserRole
from app.schemas.question import CategoryQuestionCreate
from app.services import question_import as service
from app.services.question import create_category_question

@pytest.mark.parametrize('race',['same_operation','distinct_operations','manual'])
def test_real_import_concurrency(postgres,race):
    with Session(postgres) as db:
        u=User(name='Import fixture',email='import@example.test',hashed_password='unused',role=UserRole.TEACHER);t=Topic(name='Fixture')
        db.add_all([u,t]);db.commit()
        h=hierarchy.__wrapped__(db,t);args=setup(db,u,h,t);uid=u.id
        data=raw();proof=service.validate(db,u,data,*args,'TRIVIAL')['proof'];initial=db.scalar(select(func.count()).select_from(Question))
    barrier=Barrier(2);op=uuid4()
    def run(index):
        with Session(postgres) as db:
            user=db.get(User,uid);barrier.wait(timeout=10)
            try:
                if race=='manual' and index:
                    row=service.parse(data,'TRIVIAL',args[3])[0][0][1]
                    return create_category_question(db,*args[:3],row).id
                return service.confirm(db,user,data,*args,'TRIVIAL',proof,op if race=='same_operation' else uuid4())
            except HTTPException as e:
                db.rollback();return e.status_code
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(run,[0,1]))
    with Session(postgres) as db:
        count=db.scalar(select(func.count()).select_from(Question))
        if race=='same_operation':assert results[0]==results[1] and count==initial+1
        elif race=='distinct_operations':assert 409 in results and count==initial+1
        else:
            # Manual creation keeps its existing duplicate policy. If it commits first,
            # the import must reject; otherwise both insertions are legitimate.
            assert count==initial+(1 if 409 in results else 2)
            assert any(isinstance(v,int) and v!=409 for v in results)


def test_import_migration_preserves_existing_tables(postgres):
    with postgres.connect() as c:
        assert c.scalar(text('select version_num from alembic_version'))=='d53e62f74085'
    with patch('app.database.engine',postgres):command.check(Config('alembic.ini'))

def test_receipt_lookup_while_commit_in_flight(postgres):
    from threading import Event
    entered,release=Event(),Event()
    with Session(postgres) as db:
        u=User(name='Receipt fixture',email='receipt@example.test',hashed_password='unused',role=UserRole.TEACHER);t=Topic(name='Fixture');db.add_all([u,t]);db.commit()
        args=setup(db,u,hierarchy.__wrapped__(db,t),t);uid=u.id;data=raw();proof=service.validate(db,u,data,*args,'TRIVIAL')['proof'];op=uuid4()
    def execute():
        with Session(postgres) as db:
            commit=db.commit
            def delayed_commit():
                db.flush();entered.set();assert release.wait(15);commit()
            db.commit=delayed_commit
            return service.confirm(db,db.get(User,uid),data,*args,'TRIVIAL',proof,op)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(execute)
        try:
            assert entered.wait(10)
            with Session(postgres) as db:assert service.read_receipt(db,db.get(User,uid),*args[:3],op)=={'status':'unknown'}
        finally:release.set()
        assert future.result()['count']==1
    with Session(postgres) as db:
        for _ in range(3):assert service.read_receipt(db,db.get(User,uid),*args[:3],op)=={'status':'confirmed','count':1}
