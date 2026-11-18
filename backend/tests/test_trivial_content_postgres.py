"""Private copies and occurrences: only the guarded synthetic PostgreSQL fixture."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select,func,text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User,Topic,Question,Category,Subject,ContentBlock,GameSession,AnswerLog
from app.models.trivial_content import TrivialContentCopy as Copy,TrivialPresentation as Presentation
from app.models.trivial_board import TrivialBoardMatch as Match,TrivialBoardOperation as Operation
from app.schemas.trivial_board import Binding
from app.schemas.trivial_persistence import InternalSetup,ParticipantSpec,PresentationCommand
from app.services import trivial_content as content,trivial_persistence as persistence
from test_trivial_persistence_postgres import pg,accounts,move,code


@pytest.fixture
def clock(monkeypatch):
    now=[datetime(2035,1,1,tzinfo=timezone.utc)]
    monkeypatch.setattr(content,'server_now',lambda db:now[0])
    monkeypatch.setattr(persistence,'server_now',lambda db:now[0])
    return now


def prepare(pg,*,online=False,bank='LYMPHOCYTE'):
    users=accounts(pg)
    with Session(pg) as db:
        t1=Topic(name='Synthetic independent topic A');t2=Topic(name='Synthetic independent topic B')
        subject=Subject(name='Synthetic subject');db.add_all([t1,t2,subject]);db.flush()
        block=ContentBlock(name='Synthetic block',subject_id=subject.id);db.add(block);db.flush()
        category=Category(name='Not inferred from a bank name',block_id=block.id)
        empty=Category(name='Linfocito');db.add_all([category,empty]);db.flush()
        qs=[]
        for i,(topic,level,active,mode,fields,cat) in enumerate([
            (t1,1,True,'TRIVIAL',True,category),(t2,1,True,'TRIVIAL',True,category),
            (t1,2,True,'TRIVIAL',True,category),(t2,None,True,'TRIVIAL',True,category),
            (t1,1,False,'TRIVIAL',True,category),(t1,1,True,'PASAPALABRA',True,category),
            (t1,1,True,'TRIVIAL',False,category),(t1,1,True,'TRIVIAL',True,empty)]):
            q=Question(topic_id=topic.id,category_id=cat.id,text=f'Synthetic historical text {i}',correct_answer='Private solution',
                       question_type=mode,options=['Option A','Option B'] if fields else None,correct_option_index=1 if fields else None,
                       difficulty=level,is_active=active)
            db.add(q);qs.append(q)
        db.commit();qids=[q.id for q in qs];cid=category.id;eid=empty.id;tid=t1.id
    specs=[ParticipantSpec(user_id=users[0]),ParticipantSpec(user_id=users[1]) if online else ParticipantSpec(guest_name='Synthetic guest')]
    setup=InternalSetup(operation_id=uuid4(),play_mode='ONLINE' if online else 'LOCAL',participants=specs,
                        bindings=[Binding(bank=bank,kind='category',id=cid)])
    with Session(pg) as db:
        state=persistence.create_internal(db,db.get(User,users[0]),setup)
    return users,state,setup,qids,tid,eid


def arrival(pg,users,state,roll=1):
    return move(pg,users[0],state,roll=roll)


def request_for(pg,state,arrival_request,*,copy_id=None):
    required=state['question_requirement']
    with Session(pg) as db:
        if copy_id is None:
            copy_id=db.scalar(select(Copy.id).where(Copy.match_id==state['id'],Copy.bank==required['bank'],Copy.difficulty==required['level']).order_by(Copy.id))
    return PresentationCommand(operation_id=uuid4(),expected_version=state['version'],participant_slot=state['active_participant'],
                               turn_number=state['turn_number'],arrival_operation_id=arrival_request.operation_id,
                               cell=required['cell'],bank=required['bank'],level=required['level'],copy_id=copy_id)


def present(pg,user,state,request):
    with Session(pg) as db:
        return content.present_internal(db,db.get(User,user),state['id'],request)


def test_frozen_filters_multi_topic_context_and_source_edits(pg,clock):
    users,state,setup,qids,tid,eid=prepare(pg)
    with Session(pg) as db:
        copies=list(db.scalars(select(Copy).where(Copy.match_id==state['id']).order_by(Copy.question_id)))
        assert [c.question_id for c in copies]==qids[:4]
        assert [c.difficulty for c in copies]==[1,1,2,None]
        frozen_id=copies[0].id
        saved=deepcopy(copies[0].snapshot);classification=deepcopy(copies[0].classification)
        assert classification['subject_name']=='Synthetic subject'
        assert classification['block_name']=='Synthetic block' and classification['category_name']=='Not inferred from a bank name'
        assert copies[0].binding_snapshot['id']==setup.bindings[0].id
        q=db.get(Question,qids[0]);q.text='Edited source';q.options=['changed'];q.correct_option_index=0;q.is_active=False;q.difficulty=4
        category=db.get(Category,q.category_id);category.name='Renamed current category'
        db.commit()
        stored=db.scalar(select(Copy).where(Copy.match_id==state['id'],Copy.question_id==qids[0]))
        assert stored.snapshot==saved and stored.classification==classification and stored.difficulty==1
        # Retrying setup must not re-freeze an edited/retired source bank.
        persistence.create_internal(db,db.get(User,users[0]),setup)
        assert db.scalar(select(func.count()).select_from(Copy))==4
    result,move_request=arrival(pg,users,state)
    request=request_for(pg,result['state'],move_request,copy_id=frozen_id)
    public=present(pg,users[0],result['state'],request)['state']['presentation']
    assert public['question']=={'text':saved['text'],'options':saved['options']}
    assert public['deadline_at']-public['opened_at']==timedelta(seconds=60)
    with Session(pg) as db:
        assert db.scalar(select(func.count()).select_from(GameSession))==0
        assert db.scalar(select(func.count()).select_from(AnswerLog))==0


def test_same_deadline_expiration_and_retry_no_resolution(pg,clock):
    users,state,setup,*_=prepare(pg)
    result,moved=arrival(pg,users,state); state=result['state']; request=request_for(pg,state,moved)
    first=present(pg,users[0],state,request); deadline=first['state']['presentation']['deadline_at']
    clock[0]+=timedelta(seconds=60)
    pg.dispose()  # Close pooled physical connections before recovery.
    with Session(pg) as db:
        recovered=persistence.read_state(db,db.get(User,users[0]),state['id'])
        assert recovered['presentation']['deadline_at']==deadline and recovered['presentation']['expired']
        assert recovered['phase']=='QUESTION_REQUIRED' and recovered['turn_status']=='OPEN'
        assert recovered['version']==first['state']['version']
    retry=present(pg,users[0],state,request)
    assert retry['operation']==first['operation'] and retry['state']['presentation']['deadline_at']==deadline
    fresh=request.model_copy(update={'operation_id':uuid4(),'expected_version':retry['state']['version']})
    with pytest.raises(HTTPException) as caught:present(pg,users[0],state,fresh)
    assert code(caught)=='PRESENTATION_EXISTS'
    with Session(pg) as db:
        assert db.scalar(select(func.count()).select_from(Presentation))==1
        assert db.scalar(select(func.count()).select_from(Operation))==2


def test_private_projection_and_online_ownership(pg,clock):
    users,state,*_=prepare(pg,online=True)
    result,moved=arrival(pg,users,state);state=result['state'];request=request_for(pg,state,moved)
    with pytest.raises(HTTPException) as caught:present(pg,users[1],state,request)
    assert caught.value.status_code==403
    owner=present(pg,users[0],state,request)
    forbidden=['correct_option_index','exact_word','accepted_answers','classification','binding_snapshot','copy_id','snapshot','Private solution']
    assert not any(word in str(owner) for word in forbidden)
    with Session(pg) as db:
        rival=persistence.read_state(db,db.get(User,users[1]),state['id'])
        assert rival['presentation']['question'] is None
        assert rival['presentation']['deadline_at']==owner['state']['presentation']['deadline_at']
    with pytest.raises(HTTPException) as caught:present(pg,users[2],state,request)
    assert caught.value.status_code==404
    with pytest.raises(HTTPException) as caught:present(pg,users[1],state,request)
    assert code(caught)=='IDEMPOTENCY_CONFLICT'
    altered=request.model_copy(update={'copy_id':request.copy_id+1})
    with pytest.raises(HTTPException) as caught:present(pg,users[0],state,altered)
    assert code(caught)=='IDEMPOTENCY_CONFLICT'


@pytest.mark.parametrize('field,value,expected',[
    ('bank','FLASK','QUESTION_REQUIREMENT_MISMATCH'),('level',2,'QUESTION_REQUIREMENT_MISMATCH'),
    ('cell',3,'QUESTION_REQUIREMENT_MISMATCH'),('turn_number',2,'STALE_TURN'),
    ('participant_slot',2,'OUT_OF_TURN'),('expected_version',1,'STALE_VERSION'),
    ('arrival_operation_id',uuid4(),'ARRIVAL_MISMATCH'),('copy_id',999999,'COPY_NOT_IN_MATCH')])
def test_requirement_mismatches(pg,clock,field,value,expected):
    users,state,*_=prepare(pg);result,moved=arrival(pg,users,state);state=result['state']
    request=request_for(pg,state,moved).model_copy(update={field:value})
    with pytest.raises(HTTPException) as caught:present(pg,users[0],state,request)
    assert code(caught)==expected
    with Session(pg) as db:assert db.scalar(select(func.count()).select_from(Presentation))==0


def test_wrong_level_copy_and_other_match_copy(pg,clock):
    users,state,setup,*_=prepare(pg);result,moved=arrival(pg,users,state);state=result['state']
    with Session(pg) as db:
        wrong=db.scalar(select(Copy.id).where(Copy.match_id==state['id'],Copy.difficulty==2))
        other=persistence.create_internal(db,db.get(User,users[0]),setup.model_copy(update={'operation_id':uuid4()}))
        foreign=db.scalar(select(Copy.id).where(Copy.match_id==other['id']))
    for copy_id,expected in [(wrong,'COPY_REQUIREMENT_MISMATCH'),(foreign,'COPY_NOT_IN_MATCH')]:
        with pytest.raises(HTTPException) as caught:present(pg,users[0],state,request_for(pg,state,moved,copy_id=copy_id))
        assert code(caught)==expected


@pytest.mark.parametrize('roll',[3,6])
def test_pending_rule_cannot_present(pg,clock,roll):
    users,state,*_=prepare(pg)
    result,moved=arrival(pg,users,state,roll=roll);state=result['state']
    with Session(pg) as db:copy_id=db.scalar(select(Copy.id).where(Copy.match_id==state['id']))
    request=PresentationCommand(operation_id=uuid4(),expected_version=state['version'],participant_slot=1,turn_number=1,
                                arrival_operation_id=moved.operation_id,cell=state['participants'][0]['position'],bank='LYMPHOCYTE',level=1,copy_id=copy_id)
    with pytest.raises(HTTPException) as caught:present(pg,users[0],state,request)
    assert code(caught)=='ARRIVAL_UNRESOLVED'


@pytest.mark.parametrize('race',['same','distinct'])
def test_presentations_real_concurrency(pg,clock,race):
    users,state,*_=prepare(pg);result,moved=arrival(pg,users,state);state=result['state'];request=request_for(pg,state,moved)
    barrier=Barrier(2)
    def run(index):
        command=request if race=='same' else request.model_copy(update={'operation_id':uuid4()})
        barrier.wait(timeout=10)
        try:return present(pg,users[0],state,command)
        except HTTPException as exc:return exc.detail['code']
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,[0,1]))
    if race=='same':assert results[0]['operation']==results[1]['operation']
    else:assert sum(isinstance(r,dict) for r in results)==1 and 'STALE_VERSION' in results
    with Session(pg) as db:
        assert db.scalar(select(func.count()).select_from(Presentation))==1
        assert db.scalar(select(func.count()).select_from(Operation))==2
        assert db.get(Match,state['id']).version==3


@pytest.mark.parametrize('fault',['receipt','commit'])
def test_presentation_atomic_rollback(pg,clock,fault):
    users,state,*_=prepare(pg);result,moved=arrival(pg,users,state);state=result['state'];request=request_for(pg,state,moved)
    with Session(pg) as db:
        actor=db.get(User,users[0])
        context=patch.object(Operation,'__init__',side_effect=RuntimeError('injected')) if fault=='receipt' else patch.object(db,'commit',side_effect=RuntimeError('injected'))
        with context,pytest.raises(RuntimeError,match='injected'):
            content.present_internal(db,actor,state['id'],request)
    with Session(pg) as db:
        assert db.scalar(select(func.count()).select_from(Presentation))==0
        assert db.scalar(select(func.count()).select_from(Operation))==1
        assert db.get(Match,state['id']).version==2
    assert present(pg,users[0],state,request)['state']['presentation'] is not None


def test_binding_validation_bazo_no_inference_and_atomic_freeze(pg,clock):
    users,state,setup,qids,tid,eid=prepare(pg)
    for bindings in [[Binding(bank='LYMPHOCYTE',kind='category',id=999999)]]:
        with Session(pg) as db,pytest.raises(HTTPException) as caught:
            persistence.create_internal(db,db.get(User,users[0]),setup.model_copy(update={'operation_id':uuid4(),'bindings':tuple(bindings)}))
        assert caught.value.status_code==404
    with pytest.raises(ValidationError):Binding(bank='SPLEEN',kind='topic',id=tid)
    with Session(pg) as db:
        # A category named Linfocito contains only its one explicit question; no name-based expansion.
        other=persistence.create_internal(db,db.get(User,users[0]),setup.model_copy(update={'operation_id':uuid4(),'bindings':(Binding(bank='FLASK',kind='category',id=eid),)}))
        assert db.scalar(select(func.count()).select_from(Copy).where(Copy.match_id==other['id']))==1
        # Existing playable filter admits non-null but malformed arrays; fail whole freeze, never skip silently.
        q=db.get(Question,qids[0]);q.options=[];db.commit()
        before=db.scalar(select(func.count()).select_from(Match))
        with pytest.raises(HTTPException) as caught:
            persistence.create_internal(db,db.get(User,users[0]),setup.model_copy(update={'operation_id':uuid4()}))
        assert code(caught)=='INVALID_ELIGIBLE_QUESTION'
        assert db.scalar(select(func.count()).select_from(Match))==before
        assert db.scalar(select(func.count()).select_from(Copy))==5


def test_database_immutability_copies_and_deadlines(pg,clock):
    users,state,*_=prepare(pg);result,moved=arrival(pg,users,state);state=result['state']
    shown=present(pg,users[0],state,request_for(pg,state,moved))
    for table,change in [('trivial_board_content_copies','difficulty=4'),('trivial_board_presentations',"deadline_at=deadline_at+interval '60 seconds'")]:
        for statement in [f'UPDATE {table} SET {change}',f'DELETE FROM {table}']:
            with pg.connect() as conn,pytest.raises(IntegrityError,match='immutable'):
                conn.execute(text(statement))
    with Session(pg) as db:
        assert persistence.read_state(db,db.get(User,users[0]),state['id'])['presentation']['deadline_at']==shown['state']['presentation']['deadline_at']


def test_topic_binding_overlap_is_explicit_and_wrong_bank_copy_rejected(pg,clock):
    users,state,setup,qids,tid,eid=prepare(pg)
    bound=setup.model_copy(update={'operation_id':uuid4(),'bindings':(
        Binding(bank='LYMPHOCYTE',kind='topic',id=tid),Binding(bank='FLASK',kind='topic',id=tid))})
    with Session(pg) as db:
        other=persistence.create_internal(db,db.get(User,users[0]),bound)
        copies=list(db.scalars(select(Copy).where(Copy.match_id==other['id'])))
        assert {c.bank for c in copies}=={'LYMPHOCYTE','FLASK'}
        assert {c.question_id for c in copies}=={qids[0],qids[2],qids[7]}
        assert len(copies)==6  # same source in two explicitly requested banks; no inferred mapping
        wrong=next(c.id for c in copies if c.bank=='FLASK' and c.difficulty==1)
    result,moved=arrival(pg,users,other);state=result['state']
    with pytest.raises(HTTPException) as caught:present(pg,users[0],state,request_for(pg,state,moved,copy_id=wrong))
    assert code(caught)=='COPY_REQUIREMENT_MISMATCH'
    duplicate=bound.model_copy(update={'operation_id':uuid4(),'bindings':(bound.bindings[0],bound.bindings[0])})
    with Session(pg) as db,pytest.raises(ValidationError):
        persistence.create_internal(db,db.get(User,users[0]),duplicate)


def test_guest_presentation_belongs_to_guest_not_host(pg,clock):
    from app.models.trivial_board import TrivialBoardParticipant
    users,state,*_=prepare(pg)
    with Session(pg) as db:
        host=db.get(TrivialBoardParticipant,(state['id'],1));host.position=2;db.commit()
    first,_=arrival(pg,users,state,roll=6)  # Virus gives guest the turn.
    second,moved=arrival(pg,users,first['state'],roll=1)
    state=second['state'];request=request_for(pg,state,moved)
    shown=present(pg,users[0],state,request)
    assert shown['state']['presentation']['participant_slot']==2
    with Session(pg) as db:
        record=db.scalar(select(Presentation))
        assert record.participant_slot==2 and record.turn_number==2
        receipt=db.get(Operation,(state['id'],str(request.operation_id)))
        assert receipt.actor_id==users[0] and receipt.participant_slot==2
        assert db.scalar(select(func.count()).select_from(GameSession))==0
        assert db.scalar(select(func.count()).select_from(AnswerLog))==0


def test_revoked_actor_cannot_open_presentation(pg,clock):
    users,state,*_=prepare(pg);result,moved=arrival(pg,users,state);state=result['state'];request=request_for(pg,state,moved)
    with Session(pg) as auth:
        actor=auth.get(User,users[0]);assert actor.auth_version==0;auth.expunge(actor)
    with Session(pg) as db:
        current=db.get(User,users[0]);current.auth_version+=1;db.commit()
    with Session(pg) as db,pytest.raises(HTTPException) as caught:
        content.present_internal(db,actor,state['id'],request)
    assert caught.value.status_code==401
    with Session(pg) as db:assert db.scalar(select(func.count()).select_from(Presentation))==0


def test_freezing_and_setup_are_one_transaction(pg,clock):
    users,state,setup,*_=prepare(pg)
    with Session(pg) as db:
        actor=db.get(User,users[0])
        with patch.object(db,'commit',side_effect=RuntimeError('injected freeze rollback')),pytest.raises(RuntimeError):
            persistence.create_internal(db,actor,setup.model_copy(update={'operation_id':uuid4()}))
    with Session(pg) as db:
        assert db.scalar(select(func.count()).select_from(Copy))==4
        assert db.scalar(select(func.count()).select_from(Match))==1


def test_migration_keeps_previous_movement_and_no_backfill(pg,clock):
    from alembic import command
    from alembic.config import Config
    from test_trivial_persistence_postgres import setup
    from migration_fixtures import origin_schema, copy_synthetic_rows, snapshot
    users=accounts(pg);state,_=setup(pg,users)
    moved,_=move(pg,users[0],state,roll=6)
    tables=('trivial_board_matches','trivial_board_participants','trivial_board_turns','trivial_board_operations')
    with origin_schema(pg,'f75e841962a7') as historical:
        copy_synthetic_rows(pg,historical,('users',*tables))
        before=snapshot(historical,tables)
        with patch('app.database.engine',historical):
            command.upgrade(Config('alembic.ini'),'a86f952a73b8')
        assert snapshot(historical,tables)==before
        with historical.connect() as connection:
            assert connection.scalar(text('SELECT version_num FROM alembic_version'))=='a86f952a73b8'
            assert connection.scalar(text('SELECT count(*) FROM trivial_board_content_copies'))==0
            assert connection.scalar(text('SELECT count(*) FROM trivial_board_presentations'))==0
        # Current ORM columns are checked only after their migrations exist.
        with patch('app.database.engine',historical):
            command.upgrade(Config('alembic.ini'),'head')
        with Session(historical) as db:
            assert db.scalar(select(func.count()).select_from(Copy))==0
            assert db.scalar(select(func.count()).select_from(Presentation))==0
            assert persistence.read_state(db,db.get(User,users[0]),state['id'])==moved['state']


def test_freeze_refreshes_cached_question_under_lock(pg,clock):
    users,state,setup,qids,*_=prepare(pg)
    with Session(pg) as db:
        actor=db.get(User,users[0])
        cached=db.get(Question,qids[0])
        assert cached.text=='Synthetic historical text 0'
        with Session(pg) as editor:
            q=editor.get(Question,qids[0]);q.text='New synthetic version before freezing';q.options=['Updated A','Updated B'];q.correct_option_index=0;editor.commit()
        new=persistence.create_internal(db,actor,setup.model_copy(update={'operation_id':uuid4()}))
        stored=db.scalar(select(Copy).where(Copy.match_id==new['id'],Copy.question_id==qids[0]))
        assert stored.snapshot['text']=='New synthetic version before freezing'
        assert stored.snapshot['options']==['Updated A','Updated B'] and stored.snapshot['correct_option_index']==0
