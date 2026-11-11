import csv, io
from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from fastapi import HTTPException
from app.models import Question, UserRole
from app.services import question_import as service
from test_content_metadata_editing import hierarchy

def raw(mode='TRIVIAL', count=1):
    out=io.StringIO(newline=''); w=csv.writer(out,delimiter=';')
    w.writerow(service.COLUMNS[mode])
    for i in range(count):
        w.writerow([f'Ficticia ñ; "cita"\nsalto {i}','A','B','C','D','B',''] if mode=='TRIVIAL' else [f'Empieza por L: Ficticia {i}','L','Luma','Lumita\nLuma azul','2'])
    return ('\ufeff'+out.getvalue()).encode()

def setup(db,user,hierarchy,topic):
    user.role=UserRole.TEACHER;db.commit()
    s,b,c=hierarchy
    return s.id,b.id,c.id,topic.id

@pytest.mark.parametrize('mode',['TRIVIAL','PASAPALABRA'])
def test_atomic_import_replay_and_duplicates(db,test_user,hierarchy,topic,mode):
    args=setup(db,test_user,hierarchy,topic); data=raw(mode,2)
    before=db.scalar(select(func.count()).select_from(Question))
    checked=service.validate(db,test_user,data,*args,mode)
    assert checked['proof'] and not checked['errors'] and checked['total']==2
    assert db.scalar(select(func.count()).select_from(Question))==before
    op=uuid4(); result=service.confirm(db,test_user,data,*args,mode,checked['proof'],op)
    assert result['count']==2
    assert service.confirm(db,test_user,data,*args,mode,checked['proof'],op)==result
    assert db.scalar(select(func.count()).select_from(Question))==before+2
    db.get(Question,result['question_ids'][0]).is_active=False;db.commit()
    duplicate=service.validate(db,test_user,data,*args,mode)
    assert not duplicate['proof'] and len(duplicate['errors'])==2
    test_user.role=UserRole.STUDENT;db.commit()
    with pytest.raises(HTTPException) as e:service.confirm(db,test_user,data,*args,mode,checked['proof'],op)
    assert e.value.status_code==403


def test_errors_limits_and_changed_confirmation(db,test_user,hierarchy,topic,monkeypatch):
    args=setup(db,test_user,hierarchy,topic); data=raw(); mode='TRIVIAL'
    checked=service.validate(db,test_user,data,*args,mode)
    before=db.scalar(select(func.count()).select_from(Question))
    for content in [b'',b'x'*(service.MAX_BYTES+1),raw(count=501),b'\xff',raw().replace(b'Ficticia', b'Ficticia\x00'),b'enunciado;enunciado\nA;B',b'enunciado\n"unterminated']:
        with pytest.raises(HTTPException): service.validate(db,test_user,content,*args,mode)
    malformed=raw().decode('utf-8-sig').replace(';B;\r\n',';Z;\r\n').encode()
    assert service.validate(db,test_user,malformed,*args,mode)['errors']
    twice=data+data.decode('utf-8-sig').split('\r\n',1)[1].encode()
    assert service.validate(db,test_user,twice,*args,mode)['errors']
    for proof,content in [('invalid',data),(checked['proof'],raw(count=2))]:
        with pytest.raises(HTTPException):service.confirm(db,test_user,content,*args,mode,proof,uuid4())
    current=service.now();monkeypatch.setattr(service,'now',lambda:current+timedelta(minutes=16))
    with pytest.raises(HTTPException,match='409'):service.confirm(db,test_user,data,*args,mode,checked['proof'],uuid4())
    assert db.scalar(select(func.count()).select_from(Question))==before


def test_conflict_before_confirmation_and_rollback(db,test_user,hierarchy,topic,monkeypatch):
    args=setup(db,test_user,hierarchy,topic);data=raw(count=2);checked=service.validate(db,test_user,data,*args,'TRIVIAL')
    original=service.build_question; calls=[]
    def broken(*a):
        calls.append(1)
        if len(calls)==2:raise RuntimeError('controlled failure')
        return original(*a)
    monkeypatch.setattr(service,'build_question',broken)
    before=db.scalar(select(func.count()).select_from(Question))
    with pytest.raises(RuntimeError):service.confirm(db,test_user,data,*args,'TRIVIAL',checked['proof'],uuid4())
    assert db.scalar(select(func.count()).select_from(Question))==before
    monkeypatch.setattr(service,'build_question',original)
    service.confirm(db,test_user,data,*args,'TRIVIAL',checked['proof'],uuid4())
    with pytest.raises(HTTPException) as e:service.confirm(db,test_user,data,*args,'TRIVIAL',checked['proof'],uuid4())
    assert e.value.status_code==409


def test_api_permissions_template_and_validation(client,db,test_user,auth_headers,hierarchy,topic):
    s,b,c=hierarchy;base=f'/subjects/{s.id}/blocks/{b.id}/categories/{c.id}/imports'
    for path in ['validate','confirm']:
        assert client.post(base+'/'+path,headers=auth_headers).status_code==403
        assert client.post(base+'/'+path).status_code==401
    setup(db,test_user,hierarchy,topic)
    template=client.get(base+'/template',params={'mode':'TRIVIAL'},headers=auth_headers)
    assert template.status_code==200 and template.content.startswith(b'\xef\xbb\xbf') and len(template.text.splitlines())==1
    checked=client.post(base+'/validate',headers=auth_headers,data={'mode':'TRIVIAL','topic_id':topic.id},files={'file':('a.csv',raw(),'text/csv')})
    assert checked.status_code==200 and checked.json()['proof']

def test_versions_expired_replay_and_saved_history(db,test_user,hierarchy,topic,monkeypatch):
    from copy import deepcopy
    from app.models import GameSession, AnswerLog
    from app.services import game
    from app.schemas.game import UserAnswer
    args=setup(db,test_user,hierarchy,topic)
    state=game.start_game_session(db,test_user,topic_id=None,subject_id=args[0],block_id=args[1],category_id=args[2])
    game.submit_game_session(db,test_user,state.session_id,[UserAnswer(question_id=q.id,selected_index=0) for q in state.questions])
    def stored(model):return [deepcopy({c.name:getattr(row,c.name) for c in model.__table__.columns}) for row in db.scalars(select(model))]
    before={m:stored(m) for m in (Question,GameSession,AnswerLog)}
    data=raw();proof=service.validate(db,test_user,data,*args,'TRIVIAL')['proof'];op=uuid4()
    result=service.confirm(db,test_user,data,*args,'TRIVIAL',proof,op)
    changed=data.replace(b';B;\r\n',b';A;\r\n')
    version=service.validate(db,test_user,changed,*args,'TRIVIAL');assert version['proof']
    with pytest.raises(HTTPException) as e:service.confirm(db,test_user,changed,*args,'TRIVIAL',version['proof'],op)
    assert e.value.status_code==409
    current=service.now();monkeypatch.setattr(service,'now',lambda:current+timedelta(minutes=16))
    assert service.confirm(db,test_user,data,*args,'TRIVIAL',proof,op)==result
    assert stored(GameSession)==before[GameSession] and stored(AnswerLog)==before[AnswerLog]
    existing={row['id']:row for row in stored(Question)}
    assert all(existing[row['id']]==row for row in before[Question])

def test_maximum_rows_structure_and_rollback_after_insert(db,test_user,hierarchy,topic,monkeypatch):
    args=setup(db,test_user,hierarchy,topic)
    assert len(service.parse(raw(count=500),'TRIVIAL',topic.id)[0])==500
    malformed=';'.join(service.COLUMNS['TRIVIAL']).encode()+b'\r\n"unterminated'
    with pytest.raises(HTTPException):service.parse(malformed,'TRIVIAL',topic.id)
    data=raw();proof=service.validate(db,test_user,data,*args,'TRIVIAL')['proof']
    before=db.scalar(select(func.count()).select_from(Question))
    flush=db.flush
    def fail_after_insert(*a,**kw):
        flush(*a,**kw)
        raise RuntimeError('failure after database insert')
    monkeypatch.setattr(db,'flush',fail_after_insert)
    with pytest.raises(RuntimeError):service.confirm(db,test_user,data,*args,'TRIVIAL',proof,uuid4())
    monkeypatch.setattr(db,'flush',flush)
    assert db.scalar(select(func.count()).select_from(Question))==before

def test_signed_destinations_and_administrator(db,test_user,hierarchy,topic):
    from app.models import Category, Topic
    args=setup(db,test_user,hierarchy,topic);test_user.role=UserRole.ADMIN;db.commit()
    data=raw();proof=service.validate(db,test_user,data,*args,'TRIVIAL')['proof']
    other_category=Category(name='Otro destino',block_id=args[1]);other_topic=Topic(name='Otra temática')
    db.add_all([other_category,other_topic]);db.commit()
    for changed in [(args[0],args[1],other_category.id,args[3]),(*args[:3],other_topic.id)]:
        with pytest.raises(HTTPException) as e:service.confirm(db,test_user,data,*changed,'TRIVIAL',proof,uuid4())
        assert e.value.status_code==422
    assert service.confirm(db,test_user,data,*args,'TRIVIAL',proof,uuid4())['count']==1

def test_duplicate_fingerprint_only_normalizes_actual_line_endings():
    q=service.parse(raw(),'TRIVIAL',1)[0][0][1]
    assert service.canonical(q.model_copy(update={'text':'A\r\nB'}))==service.canonical(q.model_copy(update={'text':'A\nB'}))
    assert service.canonical(q.model_copy(update={'text':r'A\rB'}))!=service.canonical(q.model_copy(update={'text':r'A\nB'}))

def test_committed_response_lost_then_fresh_validation_has_no_recovery_proof(client,db,test_user,auth_headers,hierarchy,topic):
    args=setup(db,test_user,hierarchy,topic)
    base=f'/subjects/{args[0]}/blocks/{args[1]}/categories/{args[2]}/imports'
    data={'mode':'TRIVIAL','topic_id':topic.id}
    def upload(path,fields):return client.post(base+path,headers=auth_headers,data=fields,files={'file':('fixture.csv',raw(),'text/csv')})
    validation=upload('/validate',data).json()
    command={**data,'proof':validation['proof'],'operation_id':str(uuid4())}
    before=db.scalar(select(func.count()).select_from(Question))
    # Server commits. Treat this response as lost to the original browser.
    assert upload('/confirm',command).status_code==200
    fresh=upload('/validate',data).json()
    assert fresh['proof'] is None and fresh['errors']
    assert upload('/confirm',command).json()['count']==1
    assert db.scalar(select(func.count()).select_from(Question))==before+1

@pytest.mark.parametrize('headers,fragment',[(['enunciado'],'Columnas obligatorias ausentes'),(['enunciado','desconocida'],'Columnas desconocidas'),(['enunciado','enunciado'],'Cabeceras repetidas')])
def test_detailed_headers(headers,fragment):
    with pytest.raises(HTTPException) as e:service.parse((';'.join(headers)+'\n').encode(),'TRIVIAL',1)
    assert fragment in e.value.detail and 'Descarga la plantilla' in e.value.detail


def test_receipt_lookup_owned_scoped_and_read_only(client,db,test_user,auth_headers,hierarchy,topic):
    from app.models import User
    args=setup(db,test_user,hierarchy,topic);base=f'/subjects/{args[0]}/blocks/{args[1]}/categories/{args[2]}/imports'
    data=raw();proof=service.validate(db,test_user,data,*args,'TRIVIAL')['proof'];op=uuid4()
    assert service.read_receipt(db,test_user,*args[:3],op)=={'status':'unknown'}
    result=service.confirm(db,test_user,data,*args,'TRIVIAL',proof,op)
    before=db.scalar(select(func.count()).select_from(Question))
    for _ in range(3):assert client.get(base+f'/receipts/{op}',headers=auth_headers).json()=={'status':'confirmed','count':1}
    other=User(name='Other',email='other-receipt@example.test',hashed_password='unused',role=UserRole.ADMIN);db.add(other);db.commit()
    assert service.read_receipt(db,other,*args[:3],op)=={'status':'unknown'}
    test_user.role=UserRole.STUDENT;db.commit()
    assert client.get(base+f'/receipts/{op}',headers=auth_headers).status_code==403
    assert client.get(base+f'/receipts/{op}').status_code==401
    assert db.scalar(select(func.count()).select_from(Question))==before
