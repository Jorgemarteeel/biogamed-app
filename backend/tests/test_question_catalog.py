"""Synthetic-only question management: no game creation or real content."""
from uuid import uuid4
from unittest.mock import patch
import pytest
from fastapi import HTTPException, Response
from fastapi.testclient import TestClient
from sqlalchemy import select, func, text
from app.main import app
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Subject, ContentBlock, Category, Topic, Question, UserRole
from app.schemas.question import CategoryQuestionCreate
from app.services.question import create_question
from app.services.question_catalog import catalog, academic_destination
from app.services import question_import as imports
from app.routers.inmunoquest import coverage
from test_inmunoquest import engine, db, teacher, opened, RAW

@pytest.fixture
def hierarchy(db):
    s=Subject(name='Synthetic subject '+uuid4().hex);other=Subject(name='Other synthetic');db.add_all([s,other]);db.flush()
    b=ContentBlock(name='Synthetic block',subject_id=s.id);db.add(b);db.flush()
    c=Category(name='Synthetic category',block_id=b.id);orphan=Category(name='Synthetic unlinked category');db.add_all([c,orphan]);db.commit()
    return s,b,c,other,orphan

def test_destinations_consistency_and_filters(db,teacher,hierarchy):
    s,b,c,other,orphan=hierarchy
    a=create_question(db,opened(subject_id=s.id));d=create_question(db,opened(),category_id=c.id)
    unknown=create_question(db,opened());unlinked=create_question(db,opened(category_id=orphan.id))
    for kwargs in ({'subject_id':s.id},{'block_id':b.id},{'category_id':c.id}):
        rows=catalog(db,mode='INMUNOQUEST',**kwargs)['items']
        assert d.id in [q['id'] for q in rows]
        if 'subject_id' in kwargs: assert a.id in [q['id'] for q in rows]
    assert academic_destination(db,category_id=c.id)==dict(subject_id=s.id,block_id=b.id,category_id=c.id)
    assert d.subject_id==s.id and d.block_id==b.id
    with pytest.raises(HTTPException):academic_destination(db,other.id,b.id,c.id)
    with pytest.raises(HTTPException):academic_destination(db,s.id,b.id,orphan.id)
    with pytest.raises(HTTPException):catalog(db,subject_id=s.id,classification='unassigned')
    with pytest.raises(HTTPException):catalog(db,mode='PASAPALABRA',bank='DNA')
    with pytest.raises(HTTPException):catalog(db,difficulty=1,difficulty_unknown=True)
    # Narrow by unique question IDs without relying on other test data.
    ids={q['id'] for q in catalog(db,classification='unassigned',limit=100)['items']}
    assert unknown.id in ids and unlinked.id in ids and a.id not in ids
    assert a.id in {q['id'] for q in catalog(db,subject_id=s.id,classification='uncategorized')['items']}
    assert catalog(db,subject_id=other.id)['total']==0
    rows=catalog(db,subject_id=s.id,limit=1)
    assert rows['total']==2 and len(rows['items'])==1
    assert rows['items'][0]['id'] != catalog(db,subject_id=s.id,skip=1,limit=1)['items'][0]['id']

def test_automatic_coverage_no_targets_and_no_solutions(db,teacher,hierarchy):
    s,b,c,other,_=hierarchy
    for n in range(31):create_question(db,opened(subject_id=s.id,bank='DNA',difficulty=4))
    create_question(db,opened(),category_id=c.id)
    create_question(db,opened(subject_id=other.id,bank='SPLEEN'))
    create_question(db,opened(bank='SPLEEN'))
    retired=create_question(db,opened(subject_id=s.id,bank='SPLEEN'));retired.is_active=False;db.commit()
    result=coverage(Response(),s.id,db)
    assert len(result['decks'])==20 and result['empty_decks']==18
    assert sum(d['available'] for d in result['decks'])==32
    assert next(d for d in result['decks'] if (d['bank'],d['difficulty'])==('DNA',4))['available']==31
    assert not result['can_start'] and 'target' not in str(result) and 'Reference answer' not in str(result)
    with TestClient(app) as client:
        app.dependency_overrides[get_db]=lambda:db;app.dependency_overrides[get_current_user]=lambda:teacher
        try:
            assert client.get('/inmunoquest/configurations').status_code==404
            assert client.get('/inmunoquest/coverage',params={'subject_id':s.id}).status_code==200
            assert client.get('/inmunoquest/coverage').status_code==422
        finally:app.dependency_overrides.clear()

def test_direct_import_receipt_proof_scope_and_duplicates(db,teacher,hierarchy):
    s,b,c,other,_=hierarchy
    raw=RAW.replace('¿Qué; célula?'.encode(),uuid4().hex.encode());args=(s.id,0,0,None,'INMUNOQUEST')
    v=imports.validate(db,teacher,raw,*args);assert v['proof']
    with pytest.raises(HTTPException):imports.confirm(db,teacher,raw,other.id,0,0,None,'INMUNOQUEST',v['proof'],uuid4())
    op=uuid4();result=imports.confirm(db,teacher,raw,*args,v['proof'],op)
    assert imports.confirm(db,teacher,raw,*args,v['proof'],op)==result
    assert imports.read_receipt(db,teacher,s.id,0,0,op)['status']=='confirmed'
    assert imports.read_receipt(db,teacher,other.id,0,0,op)['status']=='unknown'
    q=db.get(Question,result['question_ids'][0]);assert q.subject_id==s.id and q.category_id is None
    assert imports.validate(db,teacher,raw,*args)['errors']
    assert not imports.validate(db,teacher,raw,other.id,0,0,None,'INMUNOQUEST')['errors']
    # A late row error means no rows, not a partial import.
    bad=raw+('Another;Reference;ADN;9;T1\r\n').encode();assert imports.validate(db,teacher,bad,*args)['proof'] is None


def test_pasapalabra_direct_subject_import_legacy_eligibility(db,teacher,hierarchy):
    from app.services.game_questions import selectable_questions
    s,b,c,_,_=hierarchy;t=Topic(name='Explicit synthetic Topic');db.add(t);db.commit()
    raw=b'enunciado;letra;solucion;alternativas;dificultad\nEmpieza por L: synthetic;L;Luma;;2\n'
    args=(s.id,0,0,t.id,'PASAPALABRA');v=imports.validate(db,teacher,raw,*args)
    out=imports.confirm(db,teacher,raw,*args,v['proof'],uuid4());q=db.get(Question,out['question_ids'][0])
    assert q.subject_id==s.id and q.topic_id==t.id and q.question_type=='PASAPALABRA'
    assert q.id in [row.id for row in db.scalars(selectable_questions(t.id,'PASAPALABRA',db=db))]

@pytest.mark.parametrize('role',[UserRole.STUDENT,UserRole.TEACHER,UserRole.ADMIN])
def test_catalog_permissions_destinations_and_mutations(db,teacher,hierarchy,role):
    s,b,c,_,_=hierarchy;q=create_question(db,opened(subject_id=s.id));teacher.role=role;db.commit()
    with TestClient(app) as client:
        app.dependency_overrides[get_db]=lambda:db;app.dependency_overrides[get_current_user]=lambda:teacher
        try:
            expected=403 if role==UserRole.STUDENT else 200
            for path in ['/questions/catalog','/questions/destinations?kind=subject',f'/inmunoquest/coverage?subject_id={s.id}']:
                response=client.get(path);assert response.status_code==expected
                if expected==403: assert 'Reference answer' not in response.text
            payload=opened(subject_id=s.id).model_dump()
            assert client.put(f'/questions/manage/{q.id}',json=payload).status_code==expected
            assert client.put(f'/questions/manage/{q.id}/state',json={'is_active':False}).status_code==expected
        finally:app.dependency_overrides.clear()

def test_edit_preserves_historical_json_and_filters(db,teacher,hierarchy):
    from app.models import GameSession
    s,b,c,_,_=hierarchy
    q=create_question(db,opened(),category_id=c.id)
    snapshot={'version':1,'questions':[{'id':q.id,'text':'Historical immutable content'}]}
    session=GameSession(user_id=teacher.id,game_mode='TRIVIAL',score=0,is_completed=True,question_ids=[q.id],question_snapshot=snapshot,content_context={'academic':{'subject_name':'Historical name'}})
    db.add(session);db.commit();sid=session.id
    with TestClient(app) as client:
        app.dependency_overrides[get_db]=lambda:db;app.dependency_overrides[get_current_user]=lambda:teacher
        try:
            assert client.put(f'/questions/manage/{q.id}',json=opened(subject_id=s.id,category_id=c.id).model_dump()).status_code==200
            assert client.get('/questions/catalog',params={'subject_id':s.id,'state':'retired'}).json()['total']==0
            assert client.put(f'/questions/manage/{q.id}/state',json={'is_active':False}).status_code==200
            assert client.get('/questions/catalog',params={'subject_id':s.id,'state':'retired'}).json()['total']==1
        finally:app.dependency_overrides.clear()
    db.expire_all();saved=db.get(GameSession,sid)
    assert saved.question_snapshot==snapshot and saved.content_context['academic']['subject_name']=='Historical name'


def test_migration_backfills_only_real_relationships(engine):
    from sqlalchemy import create_engine
    from alembic import command
    from alembic.config import Config
    schema='migration_'+uuid4().hex
    with engine.begin() as connection:connection.execute(text('CREATE SCHEMA '+schema))
    isolated=create_engine(str(engine.url),connect_args={'options':'-csearch_path='+schema})
    try:
        with patch('app.database.engine',isolated):command.upgrade(Config('alembic.ini'),'b97a063b84c9')
        with isolated.begin() as c:
            c.execute(text("INSERT INTO subjects(id,name) VALUES(1,'Explicit synthetic subject')"))
            c.execute(text("INSERT INTO content_blocks(id,subject_id,name) VALUES(1,1,'Block')"))
            c.execute(text("INSERT INTO categories(id,block_id,name) VALUES(1,1,'Linked'),(2,NULL,'Unlinked')"))
            c.execute(text("INSERT INTO topics(id,name) VALUES(1,'Explicit synthetic subject')"))
            c.execute(text("INSERT INTO questions(id,topic_id,category_id,text,correct_answer,question_type,is_active) VALUES(1,1,1,'A','A','TRIVIAL',true),(2,1,2,'B','B','TRIVIAL',true),(3,1,NULL,'C','C','TRIVIAL',false)"))
            # Synthetic unused configurations were never game histories.
            c.execute(text("INSERT INTO inmunoquest_configurations(id,name,version,definition,created_at) VALUES(1,'Unused synthetic',1,'{}',now())"))
            before=c.execute(text('SELECT id,topic_id,category_id,text,correct_answer,question_type,is_active FROM questions ORDER BY id')).all()
        with patch('app.database.engine',isolated):command.upgrade(Config('alembic.ini'),'head')
        with isolated.connect() as c:
            assert before==c.execute(text('SELECT id,topic_id,category_id,text,correct_answer,question_type,is_active FROM questions ORDER BY id')).all()
            assert c.execute(text('SELECT id,subject_id,block_id FROM questions ORDER BY id')).all()==[(1,1,1),(2,None,None),(3,None,None)]
            assert c.scalar(text("SELECT to_regclass('inmunoquest_configurations')")) is None
            assert c.scalar(text('SELECT version_num FROM alembic_version'))=='c08b174c95da'
    finally:
        isolated.dispose()
        with engine.begin() as c:c.execute(text('DROP SCHEMA '+schema+' CASCADE'))


def test_linking_unclassified_category_updates_only_demonstrable_destinations(db,teacher,hierarchy):
    from app.services.subject import link_category
    s,b,c,other,orphan=hierarchy
    q=create_question(db,opened(category_id=orphan.id,subject_id=other.id))
    with pytest.raises(HTTPException) as error:link_category(db,s.id,b.id,orphan.id)
    assert error.value.status_code==409
    db.expire_all();assert db.get(Category,orphan.id).block_id is None and db.get(Question,q.id).subject_id==other.id
    q.subject_id=None;db.commit();link_category(db,s.id,b.id,orphan.id);db.expire_all()
    assert db.get(Question,q.id).subject_id==s.id and db.get(Question,q.id).block_id==b.id


def test_metadata_pins_selected_values_and_rejects_conflicting_filters(db,teacher,hierarchy):
    s,b,c,other,_=hierarchy
    with TestClient(app) as client:
        app.dependency_overrides[get_db]=lambda:db;app.dependency_overrides[get_current_user]=lambda:teacher
        try:
            response=client.get('/questions/destinations',params={'kind':'category','subject_id':s.id,'selected_id':c.id,'limit':1})
            assert response.status_code==200 and response.headers['cache-control']=='no-store'
            assert response.json()['selected']['subject_id']==s.id
            assert s.name in response.json()['selected']['display_name']
            assert client.get('/questions/destinations',params={'kind':'category','subject_id':other.id,'block_id':b.id}).status_code==422
            assert client.get('/questions/catalog',params={'mode':'PASAPALABRA','bank':'DNA'}).status_code==422
        finally:app.dependency_overrides.clear()


def test_manual_creation_serializes_with_direct_subject_import(engine,db,teacher,hierarchy):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from sqlalchemy.orm import Session
    from app.models import User
    from app.services.question import build_question, lock_question_destination
    s,_,_,_,_=hierarchy;uid=teacher.id;raw=RAW.replace('¿Qué; célula?'.encode(),uuid4().hex.encode())
    args=(s.id,0,0,None,'INMUNOQUEST');proof=imports.validate(db,teacher,raw,*args)['proof'];db.commit()
    acquired=Event();release=Event()
    def manual():
        with Session(engine) as session:
            lock_question_destination(session,None)
            q=imports.parse(raw,'INMUNOQUEST',None)[0][0][1]
            session.add(build_question(q,academic=dict(subject_id=s.id,block_id=None,category_id=None)))
            session.flush();acquired.set();assert release.wait(10);session.commit()
    def imported():
        with Session(engine) as session:
            u=session.get(User,uid)
            try:return imports.confirm(session,u,raw,*args,proof,uuid4())
            except HTTPException as error:session.rollback();return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        writer=pool.submit(manual);assert acquired.wait(10);reader=pool.submit(imported);release.set();writer.result();assert reader.result()==409
    assert db.scalar(select(func.count()).select_from(Question).where(Question.subject_id==s.id))==1


def test_import_with_only_block_resolves_subject_before_checking_duplicates(db,teacher,hierarchy):
    s,b,_,_,_=hierarchy
    raw=RAW.replace('¿Qué; célula?'.encode(),uuid4().hex.encode());args=(0,b.id,0,None,'INMUNOQUEST')
    proof=imports.validate(db,teacher,raw,*args)['proof'];assert proof
    result=imports.confirm(db,teacher,raw,*args,proof,uuid4())
    q=db.get(Question,result['question_ids'][0]);assert q.subject_id==s.id and q.block_id==b.id
    assert imports.validate(db,teacher,raw,*args)['proof'] is None


def test_destination_lock_refreshes_a_previously_cached_category(engine,db,teacher,hierarchy):
    from sqlalchemy.orm import Session
    from sqlalchemy import update
    s,b,c,other,orphan=hierarchy
    other_block=ContentBlock(name='Explicit other block',subject_id=other.id);db.add(other_block);db.commit()
    # The destination was read before another transaction established its parent.
    assert db.get(Category,orphan.id).block_id is None
    with Session(engine) as writer:
        writer.execute(update(Category).where(Category.id==orphan.id).values(block_id=other_block.id));writer.commit()
    before=db.scalar(select(func.count()).select_from(Question))
    with pytest.raises(HTTPException) as error:create_question(db,opened(subject_id=s.id,category_id=orphan.id))
    assert error.value.status_code==422
    assert db.scalar(select(func.count()).select_from(Question))==before
