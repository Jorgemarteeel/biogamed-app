"""Focused review; SQLite in memory, no running DB/service or HTTP authentication substitute."""
from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import Base, User
from app.models.trivial_board import TrivialBoardMatch as Match, TrivialBoardTurn as Turn, TrivialBoardOperation as Operation
from app.schemas.trivial_persistence import MoveCommand
from app.services import trivial_persistence as service
from test_trivial_persistence_postgres import accounts, setup, move, set_positions, code


@pytest.fixture
def memory():
    engine = create_engine('sqlite:///:memory:', poolclass=StaticPool)
    assert engine.url.database == ':memory:'
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_all_recovery_paths_use_saved_copy_and_configuration(memory):
    ids=accounts(memory); state,request=setup(memory,ids,size=3)
    set_positions(memory,state['id'],2)
    with Session(memory) as db:
        match=db.get(Match,state['id'])
        saved=deepcopy(match.board_snapshot); saved['width']+=1
        match.board_snapshot=saved
        config=deepcopy(match.configuration); config['turn_order']=[1,3,2]
        match.configuration=config; db.commit()
    with patch.object(service,'load_board',side_effect=AssertionError('No current board for an existing match')):
        with Session(memory) as db:
            actor=db.get(User,ids[0])
            before=service.read_state(db,actor,state['id'])
            assert before['configuration']==config
            assert service.create_internal(db,actor,request)==before
        result,command=move(memory,ids[0],before)
        assert result['state']['active_participant']==3
        assert result['state']['configuration']==config
        with Session(memory) as db:
            assert db.get(Turn,(state['id'],2)).participant_slot==3
            assert db.get(Match,state['id']).board_snapshot==saved
            assert service.read_state(db,db.get(User,ids[0]),state['id'])==result['state']
            retry=service.execute_move(db,db.get(User,ids[0]),state['id'],command,roller=lambda:pytest.fail('No reroll'))
            assert retry['operation']==result['operation']
            assert retry['state']==result['state']


@pytest.mark.parametrize('field,bad,expected',[
    ('state_schema_version',2,'UNSUPPORTED_SAVED_VERSION'),
    ('rules_version','future-rules','UNSUPPORTED_SAVED_VERSION'),
    ('board_version','future-board','UNSUPPORTED_SAVED_VERSION'),
    ('configuration',{'schema_version':2},'UNSUPPORTED_SAVED_CONFIGURATION'),
])
@pytest.mark.parametrize('path',['read','move','receipt','setup'])
def test_incompatible_versions_rejected_in_every_path(memory,field,bad,expected,path):
    ids=accounts(memory); state,setup_request=setup(memory,ids)
    result,command=move(memory,ids[0],state,roll=1)
    with Session(memory) as db:
        match=db.get(Match,state['id']); setattr(match,field,bad); db.commit()
    with Session(memory) as db:
        actor=db.get(User,ids[0])
        with pytest.raises(HTTPException) as caught:
            if path=='read': service.read_state(db,actor,state['id'])
            elif path=='setup': service.create_internal(db,actor,setup_request)
            elif path=='receipt': service.execute_move(db,actor,state['id'],command,roller=lambda:pytest.fail('No reroll'))
            else:
                fresh=MoveCommand(operation_id=uuid4(),expected_version=2,participant_slot=1,turn_number=1)
                service.execute_move(db,actor,state['id'],fresh,roller=lambda:pytest.fail('Version check before RNG'))
        assert code(caught)==expected
        assert db.scalar(select(func.count()).select_from(Operation))==1
        assert db.get(Match,state['id']).version==2


@pytest.mark.parametrize('path',['read','move','receipt','setup'])
def test_current_account_required_including_receipt_and_setup_retry(memory,path):
    ids=accounts(memory); state,setup_request=setup(memory,ids)
    result,command=move(memory,ids[0],state,roll=1)
    with Session(memory) as auth:
        actor=auth.get(User,ids[0]); assert actor.auth_version==0
        auth.expunge(actor)  # Saved identity from the already-authenticated boundary.
    with Session(memory) as db:
        user=db.get(User,ids[0]); user.auth_version=1; db.commit()
    with Session(memory) as db:
        with pytest.raises(HTTPException) as caught:
            if path=='read': service.read_state(db,actor,state['id'])
            elif path=='setup': service.create_internal(db,actor,setup_request)
            elif path=='receipt': service.execute_move(db,actor,state['id'],command,roller=lambda:pytest.fail('No roll'))
            else:
                fresh=MoveCommand(operation_id=uuid4(),expected_version=2,participant_slot=1,turn_number=1)
                service.execute_move(db,actor,state['id'],fresh,roller=lambda:pytest.fail('No roll'))
        assert caught.value.status_code==401
        assert actor.auth_version==0
        assert db.scalar(select(func.count()).select_from(Operation))==1


def test_receipt_authorization_and_old_turn_remains_recoverable(memory):
    ids=accounts(memory); state,_=setup(memory,ids,online=True)
    set_positions(memory,state['id'],2)
    result,command=move(memory,ids[0],state)
    assert result['state']['active_participant']==2
    with Session(memory) as db:
        retried=service.execute_move(db,db.get(User,ids[0]),state['id'],command,roller=lambda:pytest.fail('No reroll'))
        assert retried['operation']==result['operation']
        assert retried['state']['turn_number']==2  # Original command referred to turn 1.
        with pytest.raises(HTTPException) as caught:
            service.execute_move(db,db.get(User,ids[1]),state['id'],command)
        assert code(caught)=='IDEMPOTENCY_CONFLICT'
        with pytest.raises(HTTPException) as caught:
            service.execute_move(db,db.get(User,ids[2]),state['id'],command)
        assert caught.value.status_code==404
        assert db.scalar(select(func.count()).select_from(Operation))==1
        receipt=db.get(Operation,(state['id'],str(command.operation_id)))
        receipt.participant_slot=2; db.commit()
        with pytest.raises(HTTPException) as caught:
            service.execute_move(db,db.get(User,ids[0]),state['id'],command)
        assert code(caught)=='INVALID_SAVED_RECEIPT'


def test_original_unversioned_configuration_stays_unchanged(memory):
    ids=accounts(memory); state,request=setup(memory,ids)
    with Session(memory) as db:
        match=db.get(Match,state['id']); config=deepcopy(match.configuration)
        del config['schema_version']; match.configuration=config; db.commit()
        recovered=service.create_internal(db,db.get(User,ids[0]),request)
        assert recovered['configuration']==config
        assert 'schema_version' not in db.get(Match,state['id']).configuration


@pytest.mark.parametrize('change',[{'turn_order':[1,1]}, {'turn_order':[1,3]}, {'scope':'FULL_GAME'}, {'pending_rules':[]}])
def test_invalid_saved_configuration_rejected_without_replacing_it(memory,change):
    ids=accounts(memory); state,_=setup(memory,ids)
    with Session(memory) as db:
        match=db.get(Match,state['id']); original=deepcopy(match.configuration)
        broken=original|change; match.configuration=broken; db.commit()
        with pytest.raises(HTTPException):
            service.read_state(db,db.get(User,ids[0]),state['id'])
        assert db.get(Match,state['id']).configuration==broken


# Reuse the existing assertions without starting another PostgreSQL service.
# These cases do not claim to re-test PostgreSQL row-lock semantics.
import test_trivial_persistence_postgres as original


@pytest.mark.parametrize('case', [
    original.test_saved_board_used_and_reload_not_reexecute,
    original.test_local_guest_attribution_and_unique_penalty_consumption,
    original.test_single_local_virus_turn_skip_and_retry,
    original.test_online_identity_permissions_and_receipt_actor_conflict,
    original.test_local_outsider_and_revoked_actor,
    original.test_versions_phase_turn_and_rng_validation,
    original.test_goal_identification_has_no_result_and_cannot_move,
    original.test_invalid_setup_account_and_host_roll_back,
], ids=lambda case: case.__name__)
def test_reused_service_regressions(memory, case):
    case(memory)


@pytest.mark.parametrize('fault', ['receipt','commit'])
def test_reused_atomicity(memory, fault):
    original.test_atomic_rollback_of_position_turns_and_receipt(memory,fault)
