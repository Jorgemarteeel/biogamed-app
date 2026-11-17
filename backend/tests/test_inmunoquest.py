"""Synthetic PostgreSQL tests. Never use a habitual or demo database URL."""
import os
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func, text
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config
from app.main import app
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, UserRole, Question, Topic
from app.schemas.question import CategoryQuestionCreate, QuestionCreate
from app.services import question_import as imports
from app.services.question import create_question

BANKS=['LYMPHOCYTE','MACROPHAGE','SPLEEN','FLASK','DNA']
RAW='enunciado;respuesta_referencia;banco;dificultad;referencia_apuntes\r\n"¿Qué; célula?";"Linfocito\nT";Linfocito;1;T3\r\n'.encode('utf-8-sig')

@pytest.fixture(scope='module')
def engine():
    url=os.getenv('INMUNOQUEST_TEST_DATABASE_URL','')
    if not url: pytest.skip('Requires explicitly isolated PostgreSQL')
    assert url.startswith('postgresql://iq_test@iqdb/') and url.endswith('/biogamed_iq_test')
    root=create_engine(url)
    with root.connect() as c:
        assert c.scalar(text('select current_database()'))=='biogamed_iq_test'
    schema='iq_'+uuid4().hex
    with root.begin() as c:c.execute(text('CREATE SCHEMA '+schema))
    e=create_engine(url,connect_args={'options':'-csearch_path='+schema})
    with patch('app.database.engine',e):command.upgrade(Config('alembic.ini'),'head')
    yield e
    e.dispose()
    with root.begin() as c:c.execute(text('DROP SCHEMA '+schema+' CASCADE'))
    root.dispose()

@pytest.fixture
def db(engine):
    with Session(engine) as s:yield s

@pytest.fixture
def teacher(db):
    u=User(name='Synthetic teacher',email=uuid4().hex+'@example.test',hashed_password='unused',role=UserRole.TEACHER)
    db.add(u);db.commit();return u

def opened(**extra):
    return QuestionCreate(**{**dict(text='Synthetic question '+uuid4().hex,question_type='INMUNOQUEST',bank='LYMPHOCYTE',difficulty=1,reference_answer='  Reference answer  '),**extra})

def test_open_crud_and_exclusion(db,teacher):
    from app.services.game_questions import playable_question_filter
    q=create_question(db,opened(note_reference=' T3 '));qid=q.id
    assert q.topic_id is None and q.reference_answer=='Reference answer' and q.note_reference=='T3'
    for game in ['TRIVIAL','PASAPALABRA']:
        assert db.scalar(select(func.count()).select_from(Question).where(Question.id==qid,playable_question_filter(game)))==0
    with TestClient(app) as client:
        app.dependency_overrides[get_db]=lambda:db;app.dependency_overrides[get_current_user]=lambda:teacher
        try:
            data=client.get('/questions/catalog/open').json();assert any(r['id']==qid for r in data)
            payload=opened().model_dump();payload['text']='Edited'
            assert client.put('/questions/manage/'+str(qid),json=payload).status_code==200
            assert client.put('/questions/manage/'+str(qid)+'/state',json={'is_active':False}).json()['is_active'] is False
            assert client.put('/questions/manage/'+str(qid)+'/state',json={'is_active':True}).json()['is_active'] is True
        finally:app.dependency_overrides.clear()

@pytest.mark.parametrize('change',[{'bank':None},{'difficulty':None},{'difficulty':0},{'reference_answer':'  '},{'topic_id':1},{'options':['a']},{'letter':'A'},{'bank':'SYRINGE'}])
def test_validation(change):
    from pydantic import ValidationError
    data=dict(text='Text',question_type='INMUNOQUEST',bank='DNA',difficulty=4,reference_answer='Answer');data.update(change)
    with pytest.raises(ValidationError):CategoryQuestionCreate(**data)

@pytest.mark.parametrize('role',[UserRole.STUDENT,UserRole.TEACHER,UserRole.ADMIN])
def test_permissions(db,teacher,role):
    teacher.role=role;db.commit()
    with TestClient(app) as c:
        app.dependency_overrides[get_db]=lambda:db;app.dependency_overrides[get_current_user]=lambda:teacher
        try:
            for path in ['/questions/catalog/open','/question-imports/template','/questions/catalog']:
                assert c.get(path).status_code==(403 if role==UserRole.STUDENT else 200)
            data={'question_type':'INMUNOQUEST','text':'Test','bank':'SPLEEN','difficulty':1,'reference_answer':'Private'}
            assert c.post('/questions/',json=data).status_code==(403 if role==UserRole.STUDENT else 201)
        finally:app.dependency_overrides.clear()

@pytest.mark.parametrize('bank',['Linfocito','Macrófago','Bazo','Matraz','ADN'])
def test_csv_banks_unicode(db,teacher,bank):
    raw=('enunciado;respuesta_referencia;banco;dificultad\n"¿Qué; célula?";"Respuesta\ncon ñ";'+bank+';2\n').encode('utf-8-sig')
    v=imports.validate(db,teacher,raw,0,0,0,None,'INMUNOQUEST');assert not v['errors'];assert v['preview'][0]['reference_answer']=='Respuesta\ncon ñ'

@pytest.mark.parametrize('header',['enunciado;banco;dificultad','enunciado;respuesta_referencia;banco;dificultad;extra','enunciado;respuesta_referencia;banco;dificultad;banco'])
def test_headers(db,teacher,header):
    with pytest.raises(HTTPException) as e:imports.validate(db,teacher,(header+'\n').encode(),0,0,0,None,'INMUNOQUEST')
    assert e.value.status_code==422 and 'plantilla' in e.value.detail

def test_confirm_replay_recovery_duplicates_and_rollback(db,teacher):
    raw=RAW.replace('¿Qué; célula?'.encode(),('Q'+uuid4().hex).encode())
    args=(0,0,0,None,'INMUNOQUEST');v=imports.validate(db,teacher,raw,*args);assert v['proof']
    before=db.scalar(select(func.count()).select_from(Question));op=uuid4()
    assert imports.read_receipt(db,teacher,0,0,0,op)=={'status':'unknown'}
    result=imports.confirm(db,teacher,raw,*args,v['proof'],op)
    for _ in range(2):assert imports.confirm(db,teacher,raw,*args,v['proof'],op)==result
    assert imports.read_receipt(db,teacher,0,0,0,op)=={'status':'confirmed','count':1}
    assert db.scalar(select(func.count()).select_from(Question))==before+1
    q=db.get(Question,result['question_ids'][0]);q.is_active=False;db.commit()
    assert imports.validate(db,teacher,raw,*args)['errors']
    other=User(name='Other',email=uuid4().hex+'@example.test',hashed_password='unused',role=UserRole.TEACHER);db.add(other);db.commit()
    assert imports.read_receipt(db,other,0,0,0,op)=={'status':'unknown'}
    with pytest.raises(HTTPException):imports.confirm(db,teacher,raw+b'\n',*args,v['proof'],op)
    fresh=raw.replace(b'Q',b'NEW',1);proof=imports.validate(db,teacher,fresh,*args)['proof']
    with patch.object(db,'commit',side_effect=RuntimeError('Synthetic failure')):
        with pytest.raises(RuntimeError):imports.confirm(db,teacher,fresh,*args,proof,uuid4())
    assert db.scalar(select(func.count()).select_from(Question))==before+1

@pytest.mark.parametrize('assigned',[False,True])
def test_concurrent_imports(engine,db,teacher,assigned):
    from app.models import Subject
    subject=Subject(name='Synthetic concurrency scope') if assigned else None
    if subject:db.add(subject);db.commit()
    raw=RAW.replace('¿Qué; célula?'.encode(),uuid4().hex.encode());args=(subject.id if subject else 0,0,0,None,'INMUNOQUEST');proof=imports.validate(db,teacher,raw,*args)['proof'];uid=teacher.id;db.commit();barrier=Barrier(2);op=uuid4()
    def run(_):
        with Session(engine) as session:
            u=session.get(User,uid);barrier.wait(10)
            return imports.confirm(session,u,raw,*args,proof,op)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,range(2)))
    assert results[0]==results[1] and results[0]['count']==1


def test_migration_preserves_old_rows(engine):
    schema='prior_'+uuid4().hex
    with engine.begin() as c:c.execute(text('CREATE SCHEMA '+schema))
    e=create_engine(str(engine.url),connect_args={'options':'-csearch_path='+schema})
    try:
        with patch('app.database.engine',e):command.upgrade(Config('alembic.ini'),'a86f952a73b8')
        with e.begin() as c:
            c.execute(text("INSERT INTO topics (id,name) VALUES (1,'Synthetic legacy')"))
            c.execute(text("INSERT INTO users (id,name,email,hashed_password,role) VALUES (:id,'Synthetic','prior@example.test','untouched-hash','STUDENT')"),{'id':str(uuid4())})
            c.execute(text("INSERT INTO questions (id,topic_id,text,correct_answer,question_type,is_active,options,correct_option_index) VALUES (1,1,'Old','A','TRIVIAL',true,'[\"A\",\"B\",\"C\",\"D\"]',0)"))
            c.exec_driver_sql("INSERT INTO game_engine_sessions (id,user_id,topic_id,score,is_completed,created_at,question_ids,game_mode,question_snapshot) SELECT 1,id,1,1,true,now(),'[1]','TRIVIAL','{\"version\":1,\"questions\":[]}' FROM users LIMIT 1")
            c.execute(text("INSERT INTO answer_logs (game_session_id,question_id,question_text,question_type,options,selected_index,correct_option_index,is_correct,response_time_ms,answered_at) VALUES (1,1,'Historical text','TRIVIAL','[\"A\",\"B\",\"C\",\"D\"]',0,0,true,100,now())"))
            columns={t:[r[0] for r in c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema=:s AND table_name=:t ORDER BY ordinal_position"),{'s':schema,'t':t})] for t in ['users','topics','questions','game_engine_sessions','answer_logs','trivial_board_content_copies']}
            before={t:c.execute(text('SELECT '+','.join('"'+col+'"' for col in cols)+' FROM '+t+' ORDER BY 1')).all() for t,cols in columns.items()}
        with patch('app.database.engine',e):command.upgrade(Config('alembic.ini'),'head')
        with e.connect() as c:
            for t,cols in columns.items():assert before[t]==c.execute(text('SELECT '+','.join('"'+col+'"' for col in cols)+' FROM '+t+' ORDER BY 1')).all()
            assert c.scalar(text('SELECT reference_answer IS NULL AND bank IS NULL AND note_reference IS NULL FROM questions WHERE id=1'))
    finally:
        e.dispose()
        with engine.begin() as c:c.execute(text('DROP SCHEMA '+schema+' CASCADE'))

@pytest.mark.parametrize('case',['invalid_level','duplicate','limit','expired','changed_user','different_operations'])
def test_import_failures(engine,db,teacher,case):
    import jwt
    from app.utils.security import SECRET_KEY,ALGORITHM
    raw=RAW.replace('¿Qué; célula?'.encode(),uuid4().hex.encode());args=(0,0,0,None,'INMUNOQUEST')
    before=db.scalar(select(func.count()).select_from(Question))
    if case=='invalid_level':
        v=imports.validate(db,teacher,raw.replace(b';1;T3',b';;T3'),*args);assert v['proof'] is None and v['errors'][0]['column']=='dificultad'
    elif case=='duplicate':
        v=imports.validate(db,teacher,raw+raw.split(b'\r\n',1)[1],*args);assert v['proof'] is None
    elif case=='limit':
        with pytest.raises(HTTPException) as err:imports.validate(db,teacher,b'x'*(2*1024*1024+1),*args)
        assert err.value.status_code==413
        with pytest.raises(HTTPException):imports.parse(b'enunciado;respuesta_referencia;banco;dificultad\n'+b'Q;A;ADN;1\n'*501,'INMUNOQUEST',None)
    elif case=='expired':
        v=imports.validate(db,teacher,raw,*args);claims=jwt.decode(v['proof'],SECRET_KEY,algorithms=[ALGORITHM]);claims['exp']=0
        with pytest.raises(HTTPException) as err:imports.confirm(db,teacher,raw,*args,jwt.encode(claims,SECRET_KEY,algorithm=ALGORITHM),uuid4())
        assert err.value.status_code==409
    elif case=='changed_user':
        v=imports.validate(db,teacher,raw,*args);teacher.role=UserRole.STUDENT;db.commit()
        with pytest.raises(HTTPException) as err:imports.confirm(db,teacher,raw,*args,v['proof'],uuid4())
        assert err.value.status_code==403
    else:
        v=imports.validate(db,teacher,raw,*args);uid=teacher.id;db.commit();barrier=Barrier(2)
        def run(_):
            with Session(engine) as s:
                u=s.get(User,uid);barrier.wait(10)
                try:return imports.confirm(s,u,raw,*args,v['proof'],uuid4())
                except HTTPException as error:s.rollback();return error.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,[0,1]))
        assert 409 in results
        return
    assert db.scalar(select(func.count()).select_from(Question))==before


def test_categorized_open_import_and_invalid_hierarchy(db,teacher):
    from app.models import Subject,ContentBlock,Category
    subject=Subject(name='Explicit synthetic subject');db.add(subject);db.flush()
    block=ContentBlock(name='Explicit block',subject_id=subject.id);db.add(block);db.flush()
    category=Category(name='Explicit category',block_id=block.id);db.add(category);db.commit()
    ids=(subject.id,block.id,category.id);raw=RAW.replace('¿Qué; célula?'.encode(),uuid4().hex.encode())
    v=imports.validate(db,teacher,raw,*ids,None,'INMUNOQUEST');result=imports.confirm(db,teacher,raw,*ids,None,'INMUNOQUEST',v['proof'],uuid4())
    q=db.get(Question,result['question_ids'][0]);assert q.category_id==category.id and q.topic_id is None
    with pytest.raises(HTTPException):imports.validate(db,teacher,raw,subject.id+999,block.id,category.id,None,'INMUNOQUEST')
    with pytest.raises(HTTPException):imports.validate(db,teacher,raw,*ids,1,'INMUNOQUEST')
