"""Manual card lifecycle; synthetic disposable PostgreSQL, never application data."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4
import json

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import User, Question, GameSession, AnswerLog
from app.models.trivial_board import TrivialBoardMatch as Match, TrivialBoardTurn as Turn, TrivialBoardOperation as Operation
from app.models.trivial_content import TrivialPresentation as Presentation, TrivialContentCopy as Copy
from app.models.inmunoquest_content import InmunoQuestDeck as Deck, InmunoQuestDeckState as DeckState, InmunoQuestEvaluation as Evaluation
from app.schemas.inmunoquest_cards import PresentCommand, EvaluateCommand, ReaderQuery
from app.services import inmunoquest_cards as cards, inmunoquest_persistence as service
from test_inmunoquest_persistence_postgres import pg, accounts, create, order, act, reposition, reload, code
from inmunoquest_content_fixtures import seed_open_questions


def ready(pg, *, online=False, size=2, rolls=None, extra=0):
    ids, subject = accounts(pg)
    if extra:
        with Session(pg) as db:
            # The database contains two real synthetic cards for the target deck.
            for index in range(extra):
                db.add(Question(question_type='INMUNOQUEST',subject_id=subject,bank='LYMPHOCYTE',difficulty=1,
                                text=f'Additional synthetic {index}',reference_answer=f'Additional private {index}'))
            db.commit()
    state, _ = create(pg,ids,subject,online=online,size=size)
    return ids,order(pg,ids,state,rolls),subject


def arrival(pg,ids,state,*,position=1,roll=1,bank=None):
    state = reposition(pg,state,position)
    moved, request = act(pg,ids,state,'advance',roll=roll)
    if bank is not None:
        moved,request = act(pg,ids,moved['state'],'choose_bank',bank=bank)
    return moved['state'],request


def presentation_request(state,demand,**extra):
    return PresentCommand(**(dict(operation_id=uuid4(),expected_version=state['version'],
        participant_slot=state['active_participant'],turn_number=state['turn_number'],request_operation_id=demand.operation_id)|extra))


def present(pg,ids,state,demand,*,request=None,who=None,shuffler=None):
    request = request or presentation_request(state,demand)
    who = who or (ids[request.participant_slot-1] if state['play_mode']=='ONLINE' else ids[0])
    with Session(pg) as db:
        result=cards.present_internal(db,db.get(User,who),state['id'],request,shuffler=shuffler)
    return result,request


def evaluation_request(state,correct=True,**extra):
    p=state['presentation']
    return EvaluateCommand(**(dict(operation_id=uuid4(),expected_version=state['version'],
        participant_slot=p['participant_slot'],reader_slot=p['reader_slot'],turn_number=p['turn_number'],
        presentation_id=p['id'],correct=correct)|extra))


def evaluate(pg,ids,state,correct=True,*,request=None,who=None):
    request=request or evaluation_request(state,correct)
    who=who or (ids[request.reader_slot-1] if state['play_mode']=='ONLINE' else ids[0])
    with Session(pg) as db:
        result=cards.evaluate_internal(db,db.get(User,who),state['id'],request)
    return result,request


def private(pg,ids,state,*,who=None,reader=None,presentation=None):
    p=state['presentation']
    reader=reader or p['reader_slot']
    who=who or (ids[reader-1] if state['play_mode']=='ONLINE' else ids[0])
    with Session(pg) as db:
        return cards.reader_view_internal(db,db.get(User,who),state['id'],
                    ReaderQuery(presentation_id=presentation or p['id'],reader_slot=reader))


def deck_state(pg,match_id,bank='LYMPHOCYTE',level=1):
    with Session(pg) as db:
        d=db.get(DeckState,(match_id,bank,level))
        return (d.cycle,list(d.available_order),list(d.discard_order),d.reserved_presentation_id)


def assert_no_private(value):
    raw=json.dumps(value,default=str)
    for forbidden in ('reference_answer','Private synthetic reference','Additional private','initial_order','discard_order','available_order','deadline_at'):
        assert forbidden not in raw


@pytest.mark.parametrize('position,roll,bank,level',[(1,1,'LYMPHOCYTE',1),(57,1,'LYMPHOCYTE',2),(98,1,'MACROPHAGE',3),(123,1,'SPLEEN',4),(128,1,'DNA',4)])
def test_bank_level_frozen_card_and_reload_without_deadline(pg,position,roll,bank,level):
    ids,state,_=ready(pg)
    state,demand=arrival(pg,ids,state,position=position,roll=roll)
    # Expectations follow the versioned board and its level boundaries.
    assert state['question_requirement']['bank']==bank and state['question_requirement']['level']==level
    result,request=present(pg,ids,state,demand)
    p=result['state']['presentation']
    assert (p['bank'],p['difficulty'],p['cell'])==(bank,level,position+roll)
    assert p['arrival_operation_id']==str(demand.operation_id)
    frozen=private(pg,ids,result['state'])
    assert frozen['question']['reference_answer'].startswith('Private synthetic reference')
    assert_no_private(result)
    with Session(pg) as db:
        original=db.scalar(select(Copy.question_id).where(Copy.id==db.get(Presentation,p['id']).copy_id))
        q=db.get(Question,original)
        q.text='Changed live source';q.reference_answer='Changed live reference';q.is_active=False;q.subject_id=None
        db.commit()
    def no_catalog(connection,cursor,statement,parameters,context,executemany):
        assert ' FROM questions ' not in statement.replace('\n',' '), statement
    event.listen(pg,'before_cursor_execute',no_catalog)
    try:
        with patch.object(cards,'server_now',return_value=datetime.now(timezone.utc)+timedelta(days=10)):
            reload(pg,ids,result['state'])
            assert private(pg,ids,result['state'])==frozen
            assert present(pg,ids,state,demand,request=request)[0]==result
    finally:
        event.remove(pg,'before_cursor_execute',no_catalog)
    assert deck_state(pg,state['id'],bank,level)[3]==p['id']
    with Session(pg) as db:
        assert db.get(Presentation,p['id']).deadline_at is None


@pytest.mark.parametrize('bank',['LYMPHOCYTE','MACROPHAGE','SPLEEN','FLASK','DNA'])
def test_brain_requires_choice_then_preserves_arrival_request_and_level(pg,bank):
    ids,state,_=ready(pg)
    state,demand=arrival(pg,ids,state,position=134,roll=1)
    assert state['phase']=='CHOOSE_BANK'
    with pytest.raises(HTTPException) as error: present(pg,ids,state,demand)
    assert code(error)=='QUESTION_NOT_PENDING'
    chosen,choice=act(pg,ids,state,'choose_bank',bank=bank)
    result,_=present(pg,ids,chosen['state'],choice)
    p=result['state']['presentation']
    assert (p['cell'],p['bank'],p['difficulty'])==(135,bank,4)
    assert p['arrival_operation_id']==str(demand.operation_id) and p['request_operation_id']==str(choice.operation_id)


@pytest.mark.parametrize('online',[False,True])
def test_reader_left_follows_seats_not_dice_order_and_roles_are_separate(pg,online):
    ids,state,_=ready(pg,online=online,size=3,rolls=[4,6,2])
    assert state['turn_order']==[2,1,3]
    state,demand=arrival(pg,ids,state)
    result,_=present(pg,ids,state,demand)
    state=result['state']
    assert (state['presentation']['participant_slot'],state['presentation']['reader_slot'])==(2,3)
    assert private(pg,ids,state)['reader_slot']==3
    for who,reader in ((ids[6],3),(ids[0],1)):
        with pytest.raises(HTTPException): private(pg,ids,state,who=who,reader=reader)
    if online:
        for who in (ids[0],ids[1]):
            reload(pg,ids,state,who)
            with pytest.raises(HTTPException) as error: private(pg,ids,state,who=who)
            assert code(error)=='ONLY_READER'
            with pytest.raises(HTTPException) as error: evaluate(pg,ids,state,who=who)
            assert code(error)=='ONLY_READER'
    result,request=evaluate(pg,ids,state,False)
    assert result['state']['active_participant']==1 and result['state']['turn_number']==2
    assert result['state']['participants'][1]['position']==2
    reload(pg,ids,result['state'])
    with Session(pg) as db:
        evaluation=db.get(Evaluation,(state['id'],request.presentation_id))
        assert evaluation.evaluator_slot==3 and evaluation.actor_id==(ids[2] if online else ids[0])
        assert db.get(Presentation,request.presentation_id).participant_slot==2
        assert db.get(Turn,(state['id'],1)).reason=='INCORRECT'
        assert db.scalar(select(func.count()).select_from(GameSession))==0
        assert db.scalar(select(func.count()).select_from(AnswerLog))==0
    assert cards.reader_slot([1,2,3],3)==1


@pytest.mark.parametrize('correct',[False,True])
def test_one_card_educational_repetition_network_replay_and_cycles(pg,correct):
    ids,state,_=ready(pg)
    state,demand=arrival(pg,ids,state)
    first,present_request=present(pg,ids,state,demand)
    state=first['state'];first_id=state['presentation']['id']
    with Session(pg) as db: copy_id=db.get(Presentation,first_id).copy_id
    result,eval_request=evaluate(pg,ids,state,correct)
    assert result['state']['active_participant']==(1 if correct else 2)
    assert deck_state(pg,state['id'])==(1,[] if correct else [copy_id],[copy_id] if correct else [],None)
    assert evaluate(pg,ids,state,request=eval_request)[0]==result
    assert present(pg,ids,state,demand,request=present_request)[0]==first
    assert_no_private(result);assert_no_private(first)
    for new_request in (eval_request.model_copy(update={'operation_id':uuid4()}),eval_request.model_copy(update={'correct':not correct})):
        with pytest.raises(HTTPException) as error: evaluate(pg,ids,state,request=new_request)
        assert code(error) in ('PRESENTATION_ALREADY_EVALUATED','IDEMPOTENCY_CONFLICT')
    with pytest.raises(HTTPException) as error: private(pg,ids,state)
    assert code(error)=='PRESENTATION_NOT_PENDING'
    state,demand=arrival(pg,ids,result['state'])
    calls=[]
    second,_=present(pg,ids,state,demand,shuffler=lambda values:calls.append(tuple(values)))
    assert second['state']['presentation']['id']!=first_id
    with Session(pg) as db:
        assert db.get(Presentation,second['state']['presentation']['id']).copy_id==copy_id
        assert db.scalar(select(func.count()).select_from(Presentation))==2
        assert db.scalar(select(func.count()).select_from(Evaluation))==1
    assert calls==([tuple([copy_id])] if correct else [])
    assert deck_state(pg,state['id'])[0]==(2 if correct else 1)


def test_wrong_card_bottom_and_shared_deck_order_then_recycled_discard(pg):
    ids,state,_=ready(pg,extra=1)
    with Session(pg) as db: initial=list(db.get(Deck,(state['id'],'LYMPHOCYTE',1)).initial_order)
    state,demand=arrival(pg,ids,state)
    state=present(pg,ids,state,demand)[0]['state']
    state=evaluate(pg,ids,state,False)[0]['state']
    assert deck_state(pg,state['id'])[1]==[initial[1],initial[0]]
    state,demand=arrival(pg,ids,state)
    state=present(pg,ids,state,demand)[0]['state']
    with Session(pg) as db: assert db.get(Presentation,state['presentation']['id']).copy_id==initial[1]
    state=evaluate(pg,ids,state,True)[0]['state']
    state,demand=arrival(pg,ids,state)
    state=present(pg,ids,state,demand)[0]['state']
    state=evaluate(pg,ids,state,True)[0]['state']
    assert deck_state(pg,state['id'])[:3]==(1,[],[initial[1],initial[0]])
    state,demand=arrival(pg,ids,state)
    state=present(pg,ids,state,demand,shuffler=lambda values:values.reverse())[0]['state']
    with Session(pg) as db: assert db.get(Presentation,state['presentation']['id']).copy_id==initial[0]
    assert deck_state(pg,state['id'])[:3]==(2,[initial[1]],[])


def test_new_present_aliases_same_demand_without_drawing_or_incrementing_version(pg):
    ids,state,_=ready(pg)
    state,demand=arrival(pg,ids,state)
    first,request=present(pg,ids,state,demand)
    alias,_=present(pg,ids,state,demand)
    assert alias['state']==first['state']
    assert alias['operation']['events']==[{'kind':'PRESENTATION_REUSED','presentation_id':first['state']['presentation']['id']}]
    for updates,expected in (({'request_operation_id':uuid4()},'IDEMPOTENCY_CONFLICT'),
                             ({'participant_slot':2},'IDEMPOTENCY_CONFLICT')):
        with pytest.raises(HTTPException) as error: present(pg,ids,state,demand,request=request.model_copy(update=updates))
        assert code(error)==expected
    with Session(pg) as db: assert db.scalar(select(func.count()).select_from(Presentation))==1


@pytest.mark.parametrize('stage',['present','evaluate'])
def test_real_concurrent_commands_produce_one_reservation_or_verdict(pg,stage):
    ids,state,_=ready(pg)
    state,demand=arrival(pg,ids,state)
    if stage=='evaluate': state=present(pg,ids,state,demand)[0]['state']
    requests=([presentation_request(state,demand) for _ in range(2)] if stage=='present'
              else [evaluation_request(state,value) for value in (True,False)])
    barrier=Barrier(2)
    def worker(request):
        barrier.wait(timeout=10)
        try:
            if stage=='present': return present(pg,ids,state,demand,request=request)[0]
            return evaluate(pg,ids,state,request=request)[0]
        except HTTPException as error: return error.detail['code']
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(worker,requests))
    with Session(pg) as db:
        assert db.scalar(select(func.count()).select_from(Presentation))==1
        assert db.scalar(select(func.count()).select_from(Evaluation))==(1 if stage=='evaluate' else 0)
        recovered=service.read_state(db,db.get(User,ids[0]),state['id'])
    if stage=='present':
        assert all(isinstance(r,dict) for r in results) and results[0]['state']==results[1]['state']
        assert recovered['version']==state['version']+1
    else:
        assert sum(isinstance(r,dict) for r in results)==1 and 'PRESENTATION_ALREADY_EVALUATED' in results
        assert recovered['version']==state['version']+1


@pytest.mark.parametrize('stage',['present','evaluate'])
def test_rollback_includes_card_partition_state_turn_events_and_receipt(pg,stage):
    ids,state,_=ready(pg)
    state,demand=arrival(pg,ids,state)
    if stage=='evaluate': state=present(pg,ids,state,demand)[0]['state']
    before=deck_state(pg,state['id'])
    with Session(pg) as db: operations=db.scalar(select(func.count()).select_from(Operation))
    original=cards._save_receipt
    def fail_after_receipt(*args,**kwargs):
        original(*args,**kwargs)
        raise RuntimeError('Synthetic failure after receipt flush')
    with patch.object(cards,'_save_receipt',side_effect=fail_after_receipt),pytest.raises(RuntimeError):
        if stage=='present': present(pg,ids,state,demand)
        else: evaluate(pg,ids,state,False)
    reload(pg,ids,state)
    assert deck_state(pg,state['id'])==before
    with Session(pg) as db:
        assert db.scalar(select(func.count()).select_from(Operation))==operations
        assert db.scalar(select(func.count()).select_from(Evaluation))==0
        assert db.scalar(select(func.count()).select_from(Presentation))==(1 if stage=='evaluate' else 0)
        assert db.scalar(select(func.count()).select_from(Turn))==1


def test_recycle_invalid_shuffle_rolls_back_to_saved_discard(pg):
    ids,state,_=ready(pg)
    state,demand=arrival(pg,ids,state)
    state=present(pg,ids,state,demand)[0]['state']
    state=evaluate(pg,ids,state)[0]['state']
    state,demand=arrival(pg,ids,state)
    before=deck_state(pg,state['id'])
    with pytest.raises(ValueError): present(pg,ids,state,demand,shuffler=lambda values:values.clear())
    reload(pg,ids,state)
    assert deck_state(pg,state['id'])==before


def test_failure_after_evaluation_flush_rolls_back_verdict_turn_card_and_receipt(pg):
    ids,state,_=ready(pg)
    state,demand=arrival(pg,ids,state)
    state=present(pg,ids,state,demand)[0]['state']
    before=deck_state(pg,state['id'])
    with Session(pg) as db: count=db.scalar(select(func.count()).select_from(Operation))
    original=cards.validate_flow
    def fail_final(db,match,people,current,**kwargs):
        original(db,match,people,current,**kwargs)
        if db.scalar(select(func.count()).select_from(Evaluation)):
            raise RuntimeError('Synthetic post-evaluation-flush failure')
    with patch.object(cards,'validate_flow',side_effect=fail_final),pytest.raises(RuntimeError):
        evaluate(pg,ids,state,False)
    reload(pg,ids,state)
    assert deck_state(pg,state['id'])==before
    with Session(pg) as db:
        assert db.scalar(select(func.count()).select_from(Evaluation))==0
        assert db.scalar(select(func.count()).select_from(Turn))==1
        assert db.scalar(select(func.count()).select_from(Operation))==count


@pytest.mark.parametrize('field,value,expected',[
    ('expected_version',1,'STALE_VERSION'),('participant_slot',2,'PRESENTATION_MISMATCH'),
    ('turn_number',99,'PRESENTATION_MISMATCH'),('reader_slot',1,'READER_MISMATCH'),
    ('presentation_id',99999,'PRESENTATION_NOT_FOUND')])
def test_evaluation_checks_current_presentation_turn_phase_and_version(pg,field,value,expected):
    ids,state,_=ready(pg)
    state,demand=arrival(pg,ids,state)
    state=present(pg,ids,state,demand)[0]['state']
    request=evaluation_request(state).model_copy(update={field:value})
    with pytest.raises(HTTPException) as error: evaluate(pg,ids,state,request=request)
    # Changing respondent also changes the required reader; either check denies.
    assert code(error)==expected or field=='participant_slot' and code(error)=='READER_MISMATCH'
    reload(pg,ids,state)


def test_cannot_evaluate_without_presentation_or_inject_copy_reference_verdict_text(pg):
    ids,state,_=ready(pg)
    state,demand=arrival(pg,ids,state)
    request=EvaluateCommand(operation_id=uuid4(),expected_version=state['version'],participant_slot=1,
                            reader_slot=2,turn_number=1,presentation_id=999,correct=True)
    with pytest.raises(HTTPException) as error: evaluate(pg,ids,state,request=request)
    assert code(error)=='PRESENTATION_NOT_FOUND'
    for extra in ({'copy_id':1},{'reference_answer':'unsafe'},{'order':[1]}):
        with pytest.raises(ValidationError): PresentCommand.model_validate(presentation_request(state,demand).model_dump()|extra)
    for value in ('true',1,None):
        with pytest.raises(ValidationError): EvaluateCommand.model_validate(request.model_dump()|{'correct':value})


def test_reference_never_leaks_in_general_reads_receipts_or_errors_and_stale_credentials_denied(pg):
    ids,state,_=ready(pg,online=True,size=3)
    state,demand=arrival(pg,ids,state)
    first,request=present(pg,ids,state,demand)
    state=first['state']
    for who in ids[:3]: assert_no_private(reload(pg,ids,state,who))
    with Session(pg) as db:
        stale=db.get(User,ids[1]);db.expunge(stale)
    with Session(pg) as db:
        user=db.get(User,ids[1]);user.auth_version+=1;db.commit()
    with Session(pg) as db,pytest.raises(HTTPException) as error:
        cards.reader_view_internal(db,stale,state['id'],ReaderQuery(presentation_id=state['presentation']['id'],reader_slot=2))
    assert error.value.status_code==401
    with pytest.raises(HTTPException) as error: present(pg,ids,state,demand,request=request,who=ids[1])
    assert code(error)=='IDEMPOTENCY_CONFLICT'
    result,_=evaluate(pg,ids,state)
    with Session(pg) as db:
        for receipt in db.scalars(select(Operation)):
            assert_no_private(receipt.result)
            assert 'reference_answer' not in json.dumps(receipt.payload)
    assert_no_private(result)


@pytest.mark.parametrize('table',['trivial_board_presentations','inmunoquest_evaluations'])
def test_presentations_and_evaluations_are_immutable_in_postgresql(pg,table):
    ids,state,_=ready(pg)
    state,demand=arrival(pg,ids,state)
    state=present(pg,ids,state,demand)[0]['state']
    evaluate(pg,ids,state)
    with pytest.raises(DBAPIError),pg.begin() as connection: connection.execute(text(f'DELETE FROM {table}'))


def test_additive_flow_migration_initializes_only_never_drawn_frozen_orders(pg):
    ids,state,_=ready(pg)
    with patch('app.database.engine',pg): command.downgrade(Config('alembic.ini'),'e2ad396eb7fc')
    tables=('trivial_board_matches','trivial_board_participants','trivial_board_turns','trivial_board_operations',
            'trivial_board_content_copies','inmunoquest_decks','questions')
    def snapshot():
        with pg.connect() as db:
            return {t:db.scalar(text(f"SELECT coalesce(jsonb_agg(v ORDER BY v::text),'[]'::jsonb) FROM (SELECT to_jsonb(t) v FROM {t} t) rows")) for t in tables}
    before=snapshot()
    with patch('app.database.engine',pg): command.upgrade(Config('alembic.ini'),'head')
    assert snapshot()==before
    reload(pg,ids,state)
    with Session(pg) as db:
        for deck in db.scalars(select(Deck)):
            assert deck_state(pg,state['id'],deck.bank,deck.difficulty)==(1,deck.initial_order,[],None)
    state,demand=arrival(pg,ids,state)
    present(pg,ids,state,demand)
    with patch('app.database.engine',pg),pytest.raises(RuntimeError,match='Cannot discard InmunoQuest'):
        command.downgrade(Config('alembic.ini'),'e2ad396eb7fc')


def test_unknown_circulation_version_is_not_reinterpreted(pg):
    ids,state,_=ready(pg)
    with Session(pg) as db:
        db.get(DeckState,(state['id'],'LYMPHOCYTE',1)).circulation_version='future';db.commit()
    with Session(pg) as db,pytest.raises(HTTPException) as error:
        service.read_state(db,db.get(User,ids[0]),state['id'])
    assert code(error)=='UNSUPPORTED_CIRCULATION_VERSION'


@pytest.mark.parametrize('same_key',[False,True])
def test_same_evaluation_verdict_retry_concurrently_runs_engine_once(pg,same_key):
    ids,state,_=ready(pg,online=True)
    state,demand=arrival(pg,ids,state)
    state=present(pg,ids,state,demand)[0]['state']
    request=evaluation_request(state,False)
    requests=[request,request if same_key else request.model_copy(update={'operation_id':uuid4()})]
    barrier=Barrier(2)
    def worker(command):
        barrier.wait(timeout=10)
        try: return evaluate(pg,ids,state,request=command)[0]
        except HTTPException as error: return error.detail['code']
    with patch.object(service.ENGINE,'evaluate',wraps=service.ENGINE.evaluate) as engine_call:
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(worker,requests))
        assert engine_call.call_count==1
    if same_key: assert results[0]==results[1]
    else: assert 'PRESENTATION_ALREADY_EVALUATED' in results
    with Session(pg) as db:
        p=db.get(Presentation,request.presentation_id)
        evaluation=db.get(Evaluation,(state['id'],p.id))
        assert p.opened_at<=evaluation.evaluated_at
        assert db.scalar(select(func.count()).select_from(Evaluation))==1
        assert db.scalar(select(func.count()).select_from(Turn))==2


def test_online_reader_may_request_card_but_other_member_cannot_and_replay_checks_actor(pg):
    ids,state,_=ready(pg,online=True,size=3)
    state,demand=arrival(pg,ids,state)
    with pytest.raises(HTTPException) as error: present(pg,ids,state,demand,who=ids[2])
    assert code(error)=='ONLY_PLAYER_OR_READER'
    first,request=present(pg,ids,state,demand,who=ids[1])
    assert present(pg,ids,state,demand,who=ids[1],request=request)[0]==first
    with pytest.raises(HTTPException) as error: present(pg,ids,state,demand,who=ids[0],request=request)
    assert code(error)=='IDEMPOTENCY_CONFLICT'
    state=first['state']
    evaluated,verdict=evaluate(pg,ids,state,False)
    with pytest.raises(HTTPException) as error: evaluate(pg,ids,state,who=ids[0],request=verdict)
    assert code(error)=='IDEMPOTENCY_CONFLICT'
    assert_no_private(evaluated)


def test_wrong_request_turn_and_stale_versions_do_not_draw_any_card(pg):
    ids,state,_=ready(pg)
    state,demand=arrival(pg,ids,state)
    request=presentation_request(state,demand)
    before=deck_state(pg,state['id'])
    for updates,expected in (({'request_operation_id':uuid4()},'QUESTION_REQUEST_MISMATCH'),
                             ({'turn_number':99},'QUESTION_NOT_PENDING'),
                             ({'participant_slot':2},'QUESTION_NOT_PENDING'),
                             ({'expected_version':1},'STALE_VERSION')):
        with pytest.raises(HTTPException) as error: present(pg,ids,state,demand,request=request.model_copy(update=updates))
        assert code(error)==expected
    assert deck_state(pg,state['id'])==before
    with Session(pg) as db: assert db.scalar(select(func.count()).select_from(Presentation))==0


@pytest.mark.parametrize('field,value,expected',[
    ('available_order',[],'INVALID_DECK_CIRCULATION'),
    ('reserved_presentation_id',None,'INVALID_DECK_CIRCULATION')])
def test_recovery_rejects_inconsistent_canonical_reservation(pg,field,value,expected):
    ids,state,_=ready(pg)
    state,demand=arrival(pg,ids,state)
    if field=='reserved_presentation_id': state=present(pg,ids,state,demand)[0]['state']
    with Session(pg) as db:
        setattr(db.get(DeckState,(state['id'],'LYMPHOCYTE',1)),field,value);db.commit()
    with Session(pg) as db,pytest.raises(HTTPException) as error:
        service.read_state(db,db.get(User,ids[0]),state['id'])
    assert code(error)==expected


def test_database_failure_hides_private_parameters_and_reverts_card_operation(pg):
    ids,state,_=ready(pg)
    state,demand=arrival(pg,ids,state)
    with patch.object(cards,'_save_receipt',side_effect=SQLAlchemyError('Private synthetic reference in SQL parameters')):
        with pytest.raises(HTTPException) as error: present(pg,ids,state,demand)
    assert error.value.status_code==500 and code(error)=='CARD_PERSISTENCE_FAILED'
    assert error.value.__suppress_context__ is True
    assert 'Private synthetic' not in str(error.value)
    reload(pg,ids,state)
    with Session(pg) as db: assert db.scalar(select(func.count()).select_from(Presentation))==0
