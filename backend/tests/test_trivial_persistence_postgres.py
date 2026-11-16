"""Real PostgreSQL integration, guarded against every existing environment."""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, select, text, func, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.models import User, UserRole, GameSession, AnswerLog
from app.models.trivial_board import TrivialBoardMatch as Match, TrivialBoardParticipant as Participant, TrivialBoardTurn as Turn, TrivialBoardOperation as Operation
from app.schemas.trivial_persistence import InternalSetup, ParticipantSpec, MoveCommand
from app.services import trivial_persistence as service


@pytest.fixture
def pg():
    url = os.environ.get('TRIVIAL_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Requires an explicitly isolated PostgreSQL')
    parsed = make_url(url)
    if (parsed.host != 'pg' or parsed.database != 'biogamed_trivial_test' or parsed.username != 'trivial_test'
            or not os.environ.get('TRIVIAL_TEST_RESOURCE', '').startswith('trivial-persistence-')):
        pytest.fail('Refusing writes: not the dedicated Trivial test resource')
    admin = create_engine(url)
    with admin.connect() as connection:
        assert connection.execute(text('SELECT current_database(),current_user')).one() == ('biogamed_trivial_test', 'trivial_test')
    schema = 'trivial_test_' + uuid4().hex
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={'options': f'-csearch_path={schema}'})
    try:
        with patch('app.database.engine', engine):
            command.upgrade(Config('alembic.ini'), 'head')
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def accounts(engine):
    with Session(engine) as db:
        people = [User(name=f'Synthetic {i}', email=f'trivial-{i}@example.test', hashed_password='not-a-real-password-hash', role=role)
                  for i, role in enumerate([UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN, UserRole.STUDENT, UserRole.STUDENT])]
        db.add_all(people)
        db.commit()
        return [p.id for p in people]


def setup(engine, ids, *, online=False, size=2, operation=None):
    specs = [ParticipantSpec(user_id=ids[0])]
    specs += [ParticipantSpec(user_id=ids[i]) if online else ParticipantSpec(guest_name=f'Guest {i}') for i in range(1, size)]
    request = InternalSetup(operation_id=operation or uuid4(), play_mode='ONLINE' if online else 'LOCAL', participants=specs)
    with Session(engine) as db:
        return service.create_internal(db, db.get(User, ids[0]), request), request


def move(engine, user, state, roll=6, operation=None, slot=None, **overrides):
    request = MoveCommand(operation_id=operation or uuid4(), expected_version=state['version'],
                          participant_slot=slot or state['active_participant'], turn_number=state['turn_number'])
    if overrides:
        request = MoveCommand.model_validate(request.model_dump() | overrides)
    with Session(engine) as db:
        result = service.execute_move(db, db.get(User, user), state['id'], request, roller=lambda: roll)
        return result, request


def set_positions(engine, match_id, value):
    # Synthetic controlled starting positions only; there is no production reset action.
    with Session(engine) as db:
        for p in db.scalars(select(Participant).where(Participant.match_id == match_id)):
            p.position = value
        db.commit()


def code(error):
    return error.value.detail['code']


@pytest.mark.parametrize('online,size', [(False,1),(False,4),(True,2),(True,4)])
def test_closed_roster_recovery_and_setup_retry(pg, online, size):
    ids = accounts(pg)
    state, request = setup(pg, ids, online=online, size=size)
    with Session(pg) as db:
        owner = db.get(User, ids[0])
        assert service.read_state(db, owner, state['id']) == state
        assert service.create_internal(db, owner, request) == state
        assert db.scalar(select(func.count()).select_from(Match)) == 1
        assert db.scalar(select(func.count()).select_from(Participant)) == size
        assert db.scalar(select(func.count()).select_from(GameSession)) == 0
        assert db.scalar(select(func.count()).select_from(AnswerLog)) == 0
        assert [p.user_id is not None for p in db.scalars(select(Participant).order_by(Participant.slot))] == ([True]*size if online else [True]+[False]*(size-1))
        changed = list(request.participants)
        # Keep the same host while changing a destination participant or guest name.
        if online:
            changed[0] = request.participants[0]
            changed[-1] = ParticipantSpec(user_id=ids[4])
        elif size == 1:
            changed = [request.participants[0], ParticipantSpec(guest_name='Different guest')]
        else:
            changed[0] = request.participants[0]
            changed[-1] = ParticipantSpec(guest_name='Different guest')
        conflicting = InternalSetup(operation_id=request.operation_id, play_mode=request.play_mode, participants=changed)
        with pytest.raises(HTTPException) as caught:
            service.create_internal(db, owner, conflicting)
        assert code(caught) == 'IDEMPOTENCY_CONFLICT'


def test_saved_board_used_and_reload_not_reexecute(pg):
    ids = accounts(pg)
    state, _ = setup(pg, ids)
    result, request = move(pg, ids[0], state, roll=1)
    assert result['state']['phase'] == 'QUESTION_REQUIRED'
    with Session(pg) as db, patch.object(service, 'load_board', side_effect=AssertionError('Must use saved copy')):
        recovered = service.read_state(db, db.get(User, ids[0]), state['id'])
        assert recovered == result['state']
        assert recovered['question_requirement'] == {'cell': 2, 'bank': 'LYMPHOCYTE', 'level': 1}
        retried = service.execute_move(db, db.get(User, ids[0]), state['id'], request, roller=lambda: pytest.fail('No second die'))
        assert retried['operation'] == result['operation']
        assert db.scalar(select(func.count()).select_from(Operation)) == 1
        stored = db.get(Match, state['id'])
        assert stored.board_snapshot['version'] == stored.board_version
        assert stored.configuration['participants_closed'] is True
        assert stored.rules_version == service.RULES_VERSION
    with pytest.raises(HTTPException) as caught:
        move(pg, ids[0], recovered, roll=2)
    assert code(caught) == 'ARRIVAL_UNRESOLVED'


@pytest.mark.parametrize('roll,rule', [(6,'BRAIN_PENDING'), (3,'BAZO_PENDING')])
def test_pending_rules_remain_blocked_after_reconnect(pg, roll, rule):
    ids = accounts(pg)
    state, _ = setup(pg, ids)
    result, _ = move(pg, ids[0], state, roll=roll)
    assert result['state']['pending_rule'] == rule
    with Session(pg) as db:
        assert service.read_state(db, db.get(User, ids[0]), state['id']) == result['state']
    with pytest.raises(HTTPException) as caught:
        move(pg, ids[0], result['state'])
    assert code(caught) == 'ARRIVAL_UNRESOLVED'


def test_local_guest_attribution_and_unique_penalty_consumption(pg):
    ids = accounts(pg)
    state, _ = setup(pg, ids)
    set_positions(pg, state['id'], 2)
    first, _ = move(pg, ids[0], state)  # host -> Virus; guest gets turn
    assert first['state']['active_participant'] == 2
    assert first['state']['participants'][0]['skip_next_own_turn']
    second, request = move(pg, ids[0], first['state'])  # guest -> Virus; both penalties consumed
    assert second['operation']['actor_id'] == str(ids[0]) and second['operation']['participant_slot'] == 2
    assert second['state']['active_participant'] == 1 and second['state']['turn_number'] == 5
    assert all(not p['skip_next_own_turn'] for p in second['state']['participants'])
    with Session(pg) as db:
        owner = db.get(User, ids[0])
        assert service.execute_move(db, owner, state['id'], request, roller=lambda: pytest.fail('retry'))['operation'] == second['operation']
        turns = list(db.scalars(select(Turn).order_by(Turn.number)))
        assert [t.status for t in turns] == ['ENDED','ENDED','SKIPPED','SKIPPED','OPEN']
        assert [t.participant_slot for t in turns] == [1,2,1,2,1]
        assert db.scalar(select(func.count()).select_from(GameSession)) == 0
        assert db.scalar(select(func.count()).select_from(AnswerLog)) == 0
        assert db.scalar(select(func.count()).select_from(Operation)) == 2


def test_single_local_virus_turn_skip_and_retry(pg):
    ids = accounts(pg)
    state, _ = setup(pg, ids, size=1)
    set_positions(pg, state['id'], 2)
    result, request = move(pg, ids[0], state)
    assert result['state']['turn_number'] == 3 and result['state']['phase'] == 'READY'
    assert result['state']['participants'][0]['position'] == 5
    assert not result['state']['participants'][0]['skip_next_own_turn']
    with Session(pg) as db:
        service.execute_move(db, db.get(User, ids[0]), state['id'], request, roller=lambda: pytest.fail('retry'))
        assert db.scalar(select(func.count()).select_from(Turn)) == 3


def test_online_identity_permissions_and_receipt_actor_conflict(pg):
    ids = accounts(pg)
    state, _ = setup(pg, ids, online=True)
    with Session(pg) as db:
        for uid in ids[:2]:
            assert service.read_state(db, db.get(User, uid), state['id']) == state
        with pytest.raises(HTTPException) as caught:
            service.read_state(db, db.get(User, ids[2]), state['id'])
        assert caught.value.status_code == 404
    with pytest.raises(HTTPException) as caught:
        move(pg, ids[1], state, slot=1)
    assert code(caught) == 'ONLY_OWN_ACTIONS'
    with pytest.raises(HTTPException) as caught:
        move(pg, ids[1], state, slot=2)
    assert code(caught) == 'OUT_OF_TURN'
    result, request = move(pg, ids[0], state, roll=1)
    with Session(pg) as db:
        with pytest.raises(HTTPException) as caught:
            service.execute_move(db, db.get(User, ids[1]), state['id'], request)
        assert code(caught) == 'IDEMPOTENCY_CONFLICT'
        with pytest.raises(HTTPException) as caught:
            service.execute_move(db, db.get(User, ids[0]), state['id'], request.model_copy(update={'participant_slot':2}))
        assert code(caught) == 'IDEMPOTENCY_CONFLICT'


def test_local_outsider_and_revoked_actor(pg):
    ids = accounts(pg)
    state, _ = setup(pg, ids)
    with Session(pg) as db:
        with pytest.raises(HTTPException) as caught:
            service.read_state(db, db.get(User, ids[1]), state['id'])
        assert caught.value.status_code == 404
        actor = db.get(User, ids[0])
        actor.auth_version  # retain the authenticated version in this session
        with Session(pg) as other:
            user = other.get(User, ids[0]); user.auth_version += 1; other.commit()
        with pytest.raises(HTTPException) as caught:
            service.read_state(db, actor, state['id'])
        assert caught.value.status_code == 401


@pytest.mark.parametrize('race', ['distinct','same'])
def test_real_simultaneous_moves(pg, race):
    ids = accounts(pg)
    state, _ = setup(pg, ids)
    set_positions(pg, state['id'], 2)
    barrier = Barrier(2)
    operation = uuid4()
    rolls = []
    def run(index):
        with Session(pg) as db:
            actor = db.get(User, ids[0])
            request = MoveCommand(operation_id=operation if race=='same' else uuid4(), expected_version=1, participant_slot=1, turn_number=1)
            barrier.wait(timeout=10)
            try:
                return service.execute_move(db, actor, state['id'], request, roller=lambda: (rolls.append(index) or 6))
            except HTTPException as exc:
                return exc.detail['code']
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, [0,1]))
    assert len(rolls) == 1
    if race == 'same':
        assert results[0]['operation'] == results[1]['operation']
    else:
        assert sum(isinstance(r,dict) for r in results) == 1 and 'STALE_VERSION' in results
    with Session(pg) as db:
        recovered = service.read_state(db, db.get(User, ids[0]), state['id'])
        assert recovered['version'] == 2 and recovered['turn_number'] == 2
        assert db.scalar(select(func.count()).select_from(Operation)) == 1
        assert db.scalar(select(func.count()).select_from(Turn)) == 2


@pytest.mark.parametrize('fault', ['receipt','commit'])
def test_atomic_rollback_of_position_turns_and_receipt(pg, fault):
    ids = accounts(pg)
    state, _ = setup(pg, ids)
    set_positions(pg, state['id'], 2)
    with Session(pg) as db:
        actor = db.get(User, ids[0])
        request = MoveCommand(operation_id=uuid4(),expected_version=1,participant_slot=1,turn_number=1)
        target = service.Operation if fault=='receipt' else None
        context = patch.object(target, '__init__', side_effect=RuntimeError('injected failure')) if target else patch.object(db,'commit',side_effect=RuntimeError('injected failure'))
        with context, pytest.raises(RuntimeError,match='injected failure'):
            service.execute_move(db, actor, state['id'], request, roller=lambda:6)
    with Session(pg) as db:
        restored = service.read_state(db, db.get(User, ids[0]), state['id'])
        assert restored['version']==1 and restored['turn_number']==1
        assert restored['participants'][0]['position']==2 and restored['phase']=='READY'
        assert db.scalar(select(func.count()).select_from(Operation))==0
        assert db.scalar(select(func.count()).select_from(Turn))==1


def test_versions_phase_turn_and_rng_validation(pg):
    ids=accounts(pg); state,_=setup(pg,ids)
    for override, expected in [({'expected_version':2},'STALE_VERSION'),({'turn_number':2},'STALE_TURN'),({'participant_slot':2},'OUT_OF_TURN'),({'participant_slot':4},'INVALID_PARTICIPANT')]:
        with pytest.raises(HTTPException) as caught:
            move(pg, ids[0], state, **override)
        assert code(caught)==expected
    with pytest.raises(ValueError):
        move(pg,ids[0],state,roll=7)
    with Session(pg) as db:
        assert db.scalar(select(func.count()).select_from(Operation))==0
        match=db.get(Match,state['id']); match.rules_version='unknown'; db.commit()
        with pytest.raises(HTTPException) as caught:
            service.read_state(db,db.get(User,ids[0]),state['id'])
        assert code(caught)=='UNSUPPORTED_SAVED_VERSION'


@pytest.mark.parametrize('mode,people', [
    ('LOCAL',[]),('LOCAL',[{'guest_name':'nobody'}]),
    ('LOCAL',[{'user_id':str(uuid4())},{'user_id':str(uuid4())}]),
    ('ONLINE',[{'user_id':str(uuid4())}]),
    ('ONLINE',[{'user_id':str(uuid4())},{'guest_name':'guest'}]),
    ('LOCAL',[{'user_id':str(uuid4())}]+[{'guest_name':'x'}]*4),
    ('LOCAL',[{'user_id':str(uuid4())},{'guest_name':'   '}]),
])
def test_invalid_rosters(mode,people):
    with pytest.raises(ValidationError):
        InternalSetup(operation_id=uuid4(),play_mode=mode,participants=people)


def test_no_client_die_and_distinct_accounts():
    account=uuid4()
    with pytest.raises(ValidationError):
        InternalSetup(operation_id=uuid4(),play_mode='ONLINE',participants=[{'user_id':account}]*2)
    with pytest.raises(ValidationError):
        MoveCommand(operation_id=uuid4(),expected_version=1,participant_slot=1,turn_number=1,roll=6)


def test_setup_race_has_one_aggregate(pg):
    ids=accounts(pg)
    request=InternalSetup(operation_id=uuid4(),play_mode='LOCAL',participants=[ParticipantSpec(user_id=ids[0])])
    barrier=Barrier(2)
    def run(_):
        with Session(pg) as db:
            actor=db.get(User,ids[0]); barrier.wait(timeout=10)
            return service.create_internal(db,actor,request)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(run,[0,1]))
    assert results[0]==results[1]
    with Session(pg) as db:
        assert db.scalar(select(func.count()).select_from(Match))==1
        assert db.scalar(select(func.count()).select_from(Turn))==1


def test_goal_identification_has_no_result_and_cannot_move(pg):
    ids=accounts(pg); state,_=setup(pg,ids)
    set_positions(pg,state['id'],131)
    result,_=move(pg,ids[0],state)
    assert result['state']['phase']=='GOAL_REACHED' and result['state']['turn_status']=='ENDED'
    assert [e['kind'] for e in result['operation']['events']]==['ROLLED','LANDED','DNA_ADVANCE','LANDED','GOAL_REACHED']
    assert 'winner' not in result['state']
    with pytest.raises(HTTPException) as caught:
        move(pg,ids[0],result['state'])
    assert code(caught)=='ARRIVAL_UNRESOLVED'


def test_invalid_setup_account_and_host_roll_back(pg):
    ids=accounts(pg)
    request=InternalSetup(operation_id=uuid4(),play_mode='ONLINE',participants=[ParticipantSpec(user_id=ids[0]),ParticipantSpec(user_id=uuid4())])
    with Session(pg) as db:
        with pytest.raises(HTTPException) as caught:
            service.create_internal(db,db.get(User,ids[0]),request)
        assert code(caught)=='ACCOUNT_NOT_FOUND'
        assert db.scalar(select(func.count()).select_from(Match))==0
        assert db.scalar(select(func.count()).select_from(Participant))==0
        with pytest.raises(HTTPException) as caught:
            service.create_internal(db,db.get(User,ids[1]),request)
        assert code(caught)=='HOST_MUST_BE_FIRST'


def test_additive_migration_preserves_existing_rows_and_guards_data(pg):
    from app.models import Topic, Question
    from datetime import datetime, timezone
    with patch('app.database.engine',pg):
        command.downgrade(Config('alembic.ini'),'e64f73085196')
    ids=accounts(pg)
    with Session(pg) as db:
        topic=Topic(name='Synthetic existing bank'); db.add(topic); db.flush()
        q=Question(topic_id=topic.id,text='Synthetic historical question',correct_answer='A',question_type='TRIVIAL',options=['A','B'],correct_option_index=0,is_active=False)
        db.add(q); db.flush()
        session=GameSession(user_id=ids[0],topic_id=topic.id,score=1,is_completed=True,question_ids=[q.id],game_mode='TRIVIAL')
        db.add(session); db.flush()
        db.add(AnswerLog(game_session_id=session.id,question_id=q.id,question_text='Synthetic historical copy',question_type='TRIVIAL',options=['A','B'],selected_index=0,correct_option_index=0,is_correct=True))
        db.commit()
        # Existing shared Pasapalabra state and its private copies must also survive.
        db.add_all([Question(topic_id=topic.id,text=f'Synthetic Pasapalabra {i}',correct_answer='Aorta',exact_word='Aorta',letter='A',question_type='PASAPALABRA') for i in range(40)])
        db.commit()
        from app.services import pasapalabra
        from app.schemas.pasapalabra import LocalStart, Answer
        shared=pasapalabra.start_local(db,db.get(User,ids[0]),LocalStart(operation_id=uuid4(),topic_id=topic.id,guest_name='Synthetic historical guest'))
        participant=shared['active_participant']
        pasapalabra.execute(db,db.get(User,ids[0]),shared['id'],'answer',Answer(operation_id=uuid4(),expected_version=shared['version'],participant=participant,number=1,text_answer='Aorta'))
    def snapshot():
        with pg.connect() as connection:
            return {name:connection.scalar(text(f'SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY id),\'[]\'::jsonb) FROM {name} t'))
                    for name in ('users','topics','questions','game_engine_sessions','answer_logs','pasapalabra_matches','pasapalabra_participants','pasapalabra_questions','pasapalabra_commands')}
    before=snapshot()
    with patch('app.database.engine',pg):
        command.upgrade(Config('alembic.ini'),'f75e841962a7')
    assert snapshot()==before
    with pg.connect() as connection:
        assert connection.scalar(text('SELECT version_num FROM alembic_version'))=='f75e841962a7'
    from app.models import Base
    for name in ('trivial_board_matches','trivial_board_participants','trivial_board_turns','trivial_board_operations'):
        actual={c['name']:c['nullable'] for c in inspect(pg).get_columns(name)}
        assert actual=={c.name:c.nullable for c in Base.metadata.tables[name].columns}
    # Current services require current head; preserve the explicit f75 schema
    # assertions above, then upgrade before exercising the runtime adapter.
    with patch('app.database.engine',pg):
        command.upgrade(Config('alembic.ini'),'head')
    state,_=setup(pg,ids)
    with patch('app.database.engine',pg),pytest.raises(RuntimeError,match='Cannot discard'):
        command.downgrade(Config('alembic.ini'),'e64f73085196')
    with Session(pg) as db:
        assert service.read_state(db,db.get(User,ids[0]),state['id'])==state

@pytest.mark.parametrize('field,bad,expected', [
    ('state_schema_version',2,'UNSUPPORTED_SAVED_VERSION'),
    ('rules_version','future-rules','UNSUPPORTED_SAVED_VERSION'),
    ('board_version','future-board','UNSUPPORTED_SAVED_VERSION'),
    ('configuration',{'schema_version':2},'UNSUPPORTED_SAVED_CONFIGURATION'),
])
def test_review_setup_versions_postgres(pg,field,bad,expected):
    # Same assertions as the focused SQLite review, now against migrated PostgreSQL.
    from test_trivial_persistence_review import test_incompatible_versions_rejected_in_every_path
    test_incompatible_versions_rejected_in_every_path(pg,field,bad,expected,'setup')


def test_review_saved_copies_postgres(pg):
    from test_trivial_persistence_review import test_all_recovery_paths_use_saved_copy_and_configuration
    test_all_recovery_paths_use_saved_copy_and_configuration(pg)


@pytest.mark.parametrize('online', [False,True], ids=['local','online'])
def test_review_virus_custom_order_and_consumption_postgres(pg,online):
    from copy import deepcopy
    ids=accounts(pg)
    state,_=setup(pg,ids,online=online,size=3)
    set_positions(pg,state['id'],2)
    with Session(pg) as db:
        match=db.get(Match,state['id'])
        config=deepcopy(match.configuration); config['turn_order']=[1,3,2]
        match.configuration=config; db.commit()
    results=[]
    for slot in [1,3,2]:
        actor=ids[slot-1] if online else ids[0]
        result,request=move(pg,actor,state)
        assert result['operation']['participant_slot']==slot
        assert result['operation']['actor_id']==str(actor)
        results.append(result)
        with Session(pg) as db:
            retried=service.execute_move(db,db.get(User,actor),state['id'],request,roller=lambda:pytest.fail('No extra roll on retry'))
            assert retried['operation']==result['operation']
            assert retried['state']==result['state']
        state=result['state']
    assert [r['state']['active_participant'] for r in results]==[3,2,1]
    assert state['version']==4 and state['turn_number']==7
    assert state['phase']=='READY'
    assert all(not p['skip_next_own_turn'] and p['position']==5 for p in state['participants'])
    with Session(pg) as db:
        turns=list(db.scalars(select(Turn).where(Turn.match_id==state['id']).order_by(Turn.number)))
        assert [t.participant_slot for t in turns]==[1,3,2,1,3,2,1]
        assert [t.status for t in turns]==['ENDED','ENDED','ENDED','SKIPPED','SKIPPED','SKIPPED','OPEN']
        assert [t.reason for t in turns if t.status=='SKIPPED']==['VIRUS_PENALTY']*3
        assert db.scalar(select(func.count()).select_from(Operation))==3
        assert db.scalar(select(func.count()).select_from(GameSession))==0
        assert db.scalar(select(func.count()).select_from(AnswerLog))==0
