"""Internal manual persistence. Real PostgreSQL only, guarded synthetic resources."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from threading import Barrier, Lock
from unittest.mock import patch
from uuid import uuid4
import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, select, text, func, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models import User, Subject, GameSession, AnswerLog
from app.models.trivial_board import (
    TrivialBoardMatch as Match, TrivialBoardParticipant as Participant,
    TrivialBoardTurn as Turn, TrivialBoardOperation as Operation,
)
from app.domain.inmunoquest_rules import Phase, Bank
from app.schemas.inmunoquest_persistence import InternalSetup, Command
from app.schemas.trivial_persistence import ParticipantSpec
from app.services import inmunoquest_persistence as service


@pytest.fixture
def pg():
    url = os.environ.get('INMUNOQUEST_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Requires a dedicated synthetic PostgreSQL resource')
    parsed = make_url(url)
    if (parsed.host != 'pg' or parsed.database != 'biogamed_iq_persistence_test' or parsed.username != 'iq_test'
            or not os.environ.get('INMUNOQUEST_TEST_RESOURCE', '').startswith('iq-persistence-')):
        pytest.fail('Refusing writes outside the dedicated manual persistence resource')
    admin = create_engine(url)
    with admin.connect() as connection:
        assert connection.execute(text('SELECT current_database(), current_user')).one() == ('biogamed_iq_persistence_test', 'iq_test')
    schema = 'iq_test_' + uuid4().hex
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
        users = [User(name=f'Synthetic IQ {i}', email=f'iq-{i}@example.test', hashed_password='synthetic-unused-hash') for i in range(7)]
        subject = Subject(name='Synthetic explicit subject', description='No inferred classification')
        db.add_all([*users, subject])
        db.commit()
        return [p.id for p in users], subject.id


def create(engine, ids, subject, *, online=False, size=2, operation=None):
    request = InternalSetup(operation_id=operation or uuid4(), play_mode='ONLINE' if online else 'LOCAL', subject_id=subject,
                            participants=[ParticipantSpec(user_id=ids[0]), *[
                                ParticipantSpec(user_id=ids[i]) if online else ParticipantSpec(guest_name=f'Guest {i}')
                                for i in range(1, size)]])
    with Session(engine) as db:
        return service.create_internal(db, db.get(User, ids[0]), request), request


def request_for(state, kind, *, slot=None, operation=None, **overrides):
    values = dict(operation_id=operation or uuid4(), kind=kind, expected_version=state['version'],
                  participant_slot=slot or state['active_participant'] or state['pending_rollers'][0],
                  turn_number=None if kind == 'order' else state['turn_number'])
    return Command(**(values | overrides))


def act(engine, ids, state, kind, *, roll=1, slot=None, actor=None, **overrides):
    request = request_for(state, kind, slot=slot, **overrides)
    who = actor or (ids[request.participant_slot - 1] if state['play_mode'] == 'ONLINE' else ids[0])
    with Session(engine) as db:
        result = service.execute(db, db.get(User, who), state['id'], request, roller=lambda: roll)
    return result, request


def order(engine, ids, state, rolls=None):
    rolls = rolls or list(range(len(state['participants']), 0, -1))
    for slot, roll in enumerate(rolls, 1):
        state = act(engine, ids, state, 'order', slot=slot, roll=roll)[0]['state']
    return state


def reload(engine, ids, state, who=None):
    with Session(engine) as db:
        recovered = service.read_state(db, db.get(User, who or ids[0]), state['id'])
    assert recovered == state
    return recovered


def reposition(engine, state, position):
    """Synthetic fixture only; there is no reset/teleport action in the service."""
    with Session(engine) as db:
        match = db.get(Match, state['id'])
        people = service.roster(db, match)
        current = service.recover(match, people)
        updated = replace(current, players=tuple(replace(p, position=position) if p.id == current.active_player.id else p for p in current.players))
        match.manual_state = service.encode(updated, ordering_round=match.manual_state['ordering_round'])
        db.commit()
    with Session(engine) as db:
        return service.read_state(db, db.get(User, db.get(Match, state['id']).owner_id), state['id'])


def code(error):
    return error.value.detail['code']


@pytest.mark.parametrize('online,size', [(False, 2), (False, 6), (True, 2), (True, 6)])
def test_creation_closed_roster_and_no_personal_history(pg, online, size):
    ids, subject = accounts(pg)
    state, request = create(pg, ids, subject, online=online, size=size)
    assert state['phase'] == 'ORDERING' and state['turn_order'] is None and state['turn_number'] is None
    assert state['subject'] == {'id': subject, 'name': 'Synthetic explicit subject'}
    reload(pg, ids, state)
    with Session(pg) as db:
        assert service.create_internal(db, db.get(User, ids[0]), request) == state
        assert db.scalar(select(func.count()).select_from(Match)) == 1
        assert db.scalar(select(func.count()).select_from(Turn)) == 0
        assert db.scalar(select(func.count()).select_from(Operation)) == 1
        assert db.scalar(select(func.count()).select_from(GameSession)) == 0
        assert db.scalar(select(func.count()).select_from(AnswerLog)) == 0
        people = list(db.scalars(select(Participant).order_by(Participant.slot)))
        assert len(people) == size
        assert all(p.position is None and p.phase is None and p.skip_next_own_turn is None for p in people)
    # Public state is an allowlist, with no account IDs, secrets or setup payload.
    assert not {'owner_id', 'setup_payload', 'manual_state', 'configuration', 'board_snapshot'} & state.keys()
    assert all(set(p) == {'slot', 'name', 'registered', 'position'} for p in state['participants'])
    assert str(ids[0]) not in str(state)


def test_individual_order_rolls_and_repeated_partial_ties_survive_reload(pg):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject, online=True, size=3)
    state = act(pg, ids, state, 'order', slot=1, roll=6)[0]['state']
    assert reload(pg, ids, state, ids[1])['ordering_rolls'] == {'1': 6}
    state = act(pg, ids, state, 'order', slot=2, roll=6)[0]['state']
    state = act(pg, ids, state, 'order', slot=3, roll=3)[0]['state']
    assert state['order_groups'] == [[1, 2], [3]] and state['ordering_round'] == 2
    reload(pg, ids, state)
    with pytest.raises(HTTPException) as error:
        act(pg, ids, state, 'order', slot=3)
    assert code(error) == 'NOT_IN_TIEBREAK'
    for slot in (1, 2):
        state = act(pg, ids, state, 'order', slot=slot, roll=2)[0]['state']
        reload(pg, ids, state)
    assert state['ordering_round'] == 3 and state['order_groups'] == [[1, 2], [3]]
    state = act(pg, ids, state, 'order', slot=1, roll=1)[0]['state']
    result, _ = act(pg, ids, state, 'order', slot=2, roll=5)
    state = result['state']
    assert state['turn_order'] == [2, 1, 3] and state['active_participant'] == 2
    assert state['participants'][0]['slot'] == 1 and state['turn_number'] == 1
    assert result['operation']['events'][-1] == {'kind': 'TURN_STARTED', 'participant': '2', 'origin': None,
                                               'destination': None, 'die': None, 'bank': None, 'level': None}
    reload(pg, ids, state)
    state = act(pg, ids, state, 'advance', roll=5)[0]['state']
    assert state['active_participant'] == 2 and state['participants'][1]['position'] == 6


def test_syringe_virus_and_next_own_turn_without_old_penalty(pg):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject)
    state = order(pg, ids, state)
    reload(pg, ids, state)
    state = act(pg, ids, state, 'advance', roll=5)[0]['state']
    assert state['phase'] == 'ROLL_AGAIN' and state['active_participant'] == 1
    reload(pg, ids, state)
    state = act(pg, ids, state, 'advance', roll=2)[0]['state']
    assert state['phase'] == 'VIRUS_ROLL' and state['participants'][0]['position'] == 8
    reload(pg, ids, state)
    state = act(pg, ids, state, 'virus', roll=6)[0]['state']
    assert state['phase'] == 'READY' and state['active_participant'] == 2 and state['turn_number'] == 2
    assert state['participants'][0]['position'] == 2 and state['question_requirement'] is None
    reload(pg, ids, state)
    state = act(pg, ids, state, 'advance', roll=5)[0]['state']
    state = act(pg, ids, state, 'advance', roll=2)[0]['state']
    state = act(pg, ids, state, 'virus', roll=1)[0]['state']
    assert state['active_participant'] == 1 and state['turn_number'] == 3
    state = act(pg, ids, state, 'advance', roll=1)[0]['state']
    assert state['phase'] == 'QUESTION' and state['question_requirement']['bank'] == 'MACROPHAGE'
    with Session(pg) as db:
        turns = list(db.scalars(select(Turn).order_by(Turn.number)))
        assert [t.status for t in turns] == ['ENDED', 'ENDED', 'OPEN']
        assert [t.reason for t in turns] == ['VIRUS', 'VIRUS', None]


def test_brain_choice_recovers_and_question_phase_stops_every_action(pg):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject)
    state = order(pg, ids, state)
    state = reposition(pg, state, 94)
    state = act(pg, ids, state, 'advance', roll=1)[0]['state']
    assert state['phase'] == 'CHOOSE_BANK' and state['question_requirement'] is None
    reload(pg, ids, state)
    result, request = act(pg, ids, state, 'choose_bank', bank=Bank.DNA)
    state = result['state']
    assert state['chosen_bank'] == 'DNA' and state['question_requirement'] == {'cell': 95, 'bank': 'DNA', 'level': 2}
    reload(pg, ids, state)
    with Session(pg) as db:
        assert service.execute(db, db.get(User, ids[0]), state['id'], request,
                               roller=lambda: pytest.fail('Bank selection never rolls')) == result
    for kind in ('order', 'advance', 'virus', 'choose_bank'):
        with pytest.raises(HTTPException) as error:
            act(pg, ids, state, kind, bank=Bank.SPLEEN if kind == 'choose_bank' else None, slot=1)
        assert code(error) == 'ACTION_NOT_ALLOWED'


@pytest.mark.parametrize('position,roll', [(139, 1), (138, 6)])
def test_victory_is_persisted_and_recovers_without_final_question(pg, position, roll):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject)
    state = reposition(pg, order(pg, ids, state), position)
    result, request = act(pg, ids, state, 'advance', roll=roll)
    state = result['state']
    assert state['winner'] == 1 and state['phase'] == 'FINISHED'
    assert state['participants'][0]['position'] == 140 and state['question_requirement'] is None
    reload(pg, ids, state)
    with Session(pg) as db:
        assert db.get(Turn, (state['id'], 1)).reason == 'VICTORY'
        assert service.execute(db, db.get(User, ids[0]), state['id'], request,
                               roller=lambda: pytest.fail('No repeated winning die')) == result
    with pytest.raises(HTTPException) as error:
        act(pg, ids, state, 'advance')
    assert code(error) == 'ACTION_NOT_ALLOWED'


def test_139_is_normal_and_dna_is_a_question(pg):
    ids, subject = accounts(pg)
    for position, die, bank in [(138, 1, 'MACROPHAGE'), (3, 6, 'DNA')]:
        state, _ = create(pg, ids, subject)
        state = reposition(pg, order(pg, ids, state), position)
        state = act(pg, ids, state, 'advance', roll=die)[0]['state']
        assert state['phase'] == 'QUESTION' and state['winner'] is None
        assert state['question_requirement']['bank'] == bank
        reload(pg, ids, state)


def test_original_receipts_do_not_roll_again_or_return_newer_state(pg):
    ids, subject = accounts(pg)
    initial, setup_request = create(pg, ids, subject)
    first, request = act(pg, ids, initial, 'order', slot=1, roll=6)
    state = act(pg, ids, first['state'], 'order', slot=2, roll=2)[0]['state']
    with Session(pg) as db:
        actor = db.get(User, ids[0])
        assert service.execute(db, actor, state['id'], request, roller=lambda: pytest.fail('No second die')) == first
        assert service.create_internal(db, actor, setup_request) == initial
        assert service.read_state(db, actor, state['id']) == state
    request2 = request_for(state, 'advance')
    with Session(pg) as db:
        before = db.scalar(select(func.count()).select_from(Operation))
        with pytest.raises(HTTPException) as error:
            service.execute(db, db.get(User, ids[0]), state['id'],
                            request.model_copy(update={'kind': 'advance', 'turn_number': 1}), roller=lambda: pytest.fail('No conflicting roll'))
        assert code(error) == 'IDEMPOTENCY_CONFLICT'
        assert db.scalar(select(func.count()).select_from(Operation)) == before
    result, _ = act(pg, ids, state, 'advance', roll=5, operation=request2.operation_id)
    assert result['state']['phase'] == 'ROLL_AGAIN'


def test_setup_destination_conflict_missing_subject_and_immutable_subject_context(pg):
    ids, subject = accounts(pg)
    state, request = create(pg, ids, subject)
    with Session(pg) as db:
        actor = db.get(User, ids[0])
        with pytest.raises(HTTPException) as error:
            service.create_internal(db, actor, request.model_copy(update={'subject_id': None}))
        assert code(error) == 'IDEMPOTENCY_CONFLICT'
        with pytest.raises(HTTPException) as error:
            service.create_internal(db, actor, request.model_copy(update={'operation_id': uuid4(), 'subject_id': 99999}))
        assert code(error) == 'SUBJECT_NOT_FOUND'
        db.get(Subject, subject).name = 'Synthetic renamed subject'
        db.commit()
    assert reload(pg, ids, state)['subject']['name'] == 'Synthetic explicit subject'
    unclassified, _ = create(pg, ids, None)
    assert unclassified['subject'] is None


@pytest.mark.parametrize('online', [False, True])
def test_membership_participant_actor_and_out_of_turn_permissions(pg, online):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject, online=online)
    with Session(pg) as db:
        outsider = db.get(User, ids[6])
        for call in (lambda: service.read_state(db, outsider, state['id']),
                     lambda: service.execute(db, outsider, state['id'], request_for(state, 'order', slot=1))):
            with pytest.raises(HTTPException) as error:
                call()
            assert code(error) == 'MATCH_NOT_FOUND'
    if online:
        with pytest.raises(HTTPException) as error:
            act(pg, ids, state, 'order', slot=2, actor=ids[0])
        assert code(error) == 'ONLY_OWN_ACTIONS'
    first, receipt = act(pg, ids, state, 'order', slot=1, roll=6)
    if online:
        with pytest.raises(HTTPException) as error:
            act(pg, ids, first['state'], 'order', slot=2, actor=ids[1], operation=receipt.operation_id)
        assert code(error) == 'IDEMPOTENCY_CONFLICT'
        with pytest.raises(HTTPException) as error:
            act(pg, ids, first['state'], 'order', slot=1, actor=ids[1], operation=receipt.operation_id)
        assert code(error) == 'ONLY_OWN_ACTIONS'
    state = act(pg, ids, first['state'], 'order', slot=2, roll=1)[0]['state']
    with pytest.raises(HTTPException) as error:
        act(pg, ids, state, 'advance', slot=2)
    assert code(error) == 'OUT_OF_TURN'
    with pytest.raises(HTTPException) as error:
        act(pg, ids, state, 'advance', slot=6, actor=ids[0])
    assert code(error) == 'INVALID_PARTICIPANT'


def test_account_and_credential_version_checked_even_before_receipt_recovery(pg):
    ids, subject = accounts(pg)
    state, setup_request = create(pg, ids, subject)
    result, request = act(pg, ids, state, 'order', slot=1)
    with Session(pg, expire_on_commit=False) as db:
        stale = db.get(User, ids[0])
        db.expunge(stale)
    with Session(pg) as db:
        db.get(User, ids[0]).auth_version += 1
        db.commit()
    for call in (lambda db: service.read_state(db, stale, state['id']),
                 lambda db: service.execute(db, stale, state['id'], request),
                 lambda db: service.create_internal(db, stale, setup_request)):
        with Session(pg) as db, pytest.raises(HTTPException) as error:
            call(db)
        assert code(error) == 'AUTHENTICATION_REQUIRED'
    with Session(pg) as db:
        for actor in (None, User(id=uuid4(), auth_version=0)):
            with pytest.raises(HTTPException) as error:
                service.read_state(db, actor, state['id'])
            assert code(error) == 'AUTHENTICATION_REQUIRED'


@pytest.mark.parametrize('field,value', [('rules_version', 'future'), ('board_version', 'future'), ('state_schema_version', 99)])
def test_incompatible_saved_versions_rejected_in_read_setup_and_receipt(pg, field, value):
    ids, subject = accounts(pg)
    state, setup_request = create(pg, ids, subject)
    _, request = act(pg, ids, state, 'order', slot=1)
    with Session(pg) as db:
        setattr(db.get(Match, state['id']), field, value)
        db.commit()
    for call in (lambda db: service.read_state(db, db.get(User, ids[0]), state['id']),
                 lambda db: service.execute(db, db.get(User, ids[0]), state['id'], request),
                 lambda db: service.create_internal(db, db.get(User, ids[0]), setup_request)):
        with Session(pg) as db, pytest.raises(HTTPException) as error:
            call(db)
        assert code(error) == 'UNSUPPORTED_SAVED_VERSION'


@pytest.mark.parametrize('field,value,expected', [
    ('board_snapshot', {'version': 'future'}, 'INVALID_SAVED_BOARD'),
    ('board_snapshot', {'version': service.BOARD_VERSION, 'start_cell': True, 'finish_cell': 140}, 'INVALID_SAVED_BOARD'),
    ('manual_state', {}, 'INVALID_SAVED_STATE'),
    ('configuration', {}, 'INVALID_SAVED_CONFIGURATION'),
])
def test_invalid_saved_snapshots_are_not_replaced_with_current_defaults(pg, field, value, expected):
    ids, subject = accounts(pg)
    state, request = create(pg, ids, subject)
    with Session(pg) as db:
        match = db.get(Match, state['id'])
        setattr(match, field, value)
        # Python considers True == 1. Force the synthetic JSON corruption to be
        # written even when ORM equality would otherwise suppress the UPDATE.
        flag_modified(match, field)
        db.commit()
        with pytest.raises(HTTPException) as error:
            service.read_state(db, db.get(User, ids[0]), state['id'])
        assert code(error) == expected


def test_stale_versions_turns_phase_and_repeated_ordering_reject_before_random(pg):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject)
    result, _ = act(pg, ids, state, 'order', slot=1)
    with Session(pg) as db:
        for request, expected in [
            (request_for(state, 'order', slot=2), 'STALE_VERSION'),
            (request_for(result['state'], 'order', slot=1), 'ORDER_ALREADY_ROLLED'),
        ]:
            with pytest.raises(HTTPException) as error:
                service.execute(db, db.get(User, ids[0]), state['id'], request, roller=lambda: pytest.fail('Invalid commands cannot roll'))
            assert code(error) == expected
    state = act(pg, ids, result['state'], 'order', slot=2, roll=2)[0]['state']
    with pytest.raises(HTTPException) as error:
        act(pg, ids, state, 'advance', turn_number=2)
    assert code(error) == 'STALE_TURN'


@pytest.mark.parametrize('roll', [0, 7, True, 1.0, '2'])
def test_invalid_random_source_rolls_back_everything(pg, roll):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject)
    with pytest.raises(ValueError):
        act(pg, ids, state, 'order', slot=1, roll=roll)
    reload(pg, ids, state)
    with Session(pg) as db:
        assert db.scalar(select(func.count()).select_from(Operation)) == 1


@pytest.mark.parametrize('failure', ['projection', 'commit'])
def test_state_turns_events_and_receipt_are_atomic_on_failure(pg, failure):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject)
    state = act(pg, ids, order(pg, ids, state), 'advance', roll=5)[0]['state']
    state = act(pg, ids, state, 'advance', roll=2)[0]['state']
    with Session(pg) as db:
        before = db.scalar(select(func.count()).select_from(Operation))
        actor = db.get(User, ids[0])
        target = patch.object(service, 'public_state', side_effect=RuntimeError('synthetic projection failure')) if failure == 'projection' else patch.object(db, 'commit', side_effect=RuntimeError('synthetic commit failure'))
        with target, pytest.raises(RuntimeError):
            service.execute(db, actor, state['id'], request_for(state, 'virus'), roller=lambda: 3)
        assert db.scalar(select(func.count()).select_from(Operation)) == before
        assert db.scalar(select(func.count()).select_from(Turn)) == 1
    reload(pg, ids, state)


@pytest.mark.parametrize('same_operation', [False, True])
def test_real_row_lock_concurrency_runs_a_single_transition_and_random_draw(pg, same_operation):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject)
    state = order(pg, ids, state)
    first = request_for(state, 'advance')
    second = first if same_operation else request_for(state, 'advance')
    barrier, counter_lock = Barrier(2), Lock()
    draws = []

    def worker(request):
        with Session(pg) as db:
            db.execute(text("SET LOCAL lock_timeout = '5s'"))
            actor = db.get(User, ids[0])
            barrier.wait(timeout=5)

            def draw():
                with counter_lock:
                    draws.append(5)
                return 5

            try:
                return service.execute(db, actor, state['id'], request, roller=draw)
            except HTTPException as error:
                return error.detail['code']

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, request) for request in (first, second)]
        results = [future.result(timeout=15) for future in futures]
    successes = [r for r in results if isinstance(r, dict)]
    assert len(successes) == (2 if same_operation else 1)
    if same_operation:
        assert successes[0] == successes[1]
    else:
        assert 'STALE_VERSION' in results
    assert draws == [5]
    assert successes[0]['state']['phase'] == 'ROLL_AGAIN'
    reload(pg, ids, successes[0]['state'])
    with Session(pg) as db:
        assert db.scalar(select(func.count()).select_from(Operation)) == 4  # setup, two order rolls, one advance


def test_schema_validation_rejects_untrusted_dice_evaluations_and_rosters():
    base = dict(operation_id=uuid4(), kind='advance', expected_version=1, participant_slot=1, turn_number=1)
    for changes in ({'die': 6}, {'kind': 'evaluate'}, {'expected_version': True}, {'participant_slot': 7}, {'bank': Bank.DNA}):
        with pytest.raises(ValidationError):
            Command(**(base | changes))
    host = ParticipantSpec(user_id=uuid4())
    for specs, mode in [([host], 'LOCAL'), ([host] * 7, 'ONLINE'),
                        ([host, ParticipantSpec(user_id=uuid4())], 'LOCAL'),
                        ([host, ParticipantSpec(guest_name='guest')], 'ONLINE')]:
        with pytest.raises(ValidationError):
            InternalSetup(operation_id=uuid4(), play_mode=mode, participants=specs)


def test_migration_preserves_actual_legacy_rows_copies_receipts_and_interpretation(pg):
    from test_trivial_content_postgres import prepare, arrival, present, request_for as presentation_request
    from app.services import trivial_persistence as legacy
    from app.services import trivial_content as historical_content
    # Seed through the existing services, then remove only the new empty columns.
    users, old_state, old_setup, question_ids, topic, empty = prepare(pg)
    old_move, old_move_request = arrival(pg, users, old_state, roll=1)
    old_command = presentation_request(pg, old_move['state'], old_move_request)
    old_presentation = present(pg, users[0], old_move['state'], old_command)
    from app.services.game import start_game_session, submit_game_session
    from app.schemas.game import UserAnswer
    from test_pasapalabra_postgres import setup_match as pasapalabra_setup
    from app.schemas.pasapalabra import Answer
    from app.services import pasapalabra
    # Existing integrated formats and their private/history rows must survive too.
    with Session(pg) as db:
        quiz = start_game_session(db, db.get(User, users[0]), topic_id=topic, category_id=None)
        quiz_id = quiz.session_id
        session = db.get(GameSession, quiz_id)
        submit_game_session(db, db.get(User, users[0]), quiz_id,
                            [UserAnswer(question_id=qid, selected_index=0) for qid in session.question_ids])
    pp_user, pp_state = pasapalabra_setup(pg)
    with Session(pg) as db:
        pasapalabra.execute(db, db.get(User, pp_user), pp_state['id'], 'answer',
                            Answer(operation_id=uuid4(), expected_version=pp_state['version'],
                                   participant=pp_state['active_participant'], number=1, text_answer='Aorta'))
    with patch('app.database.engine', pg):
        command.downgrade(Config('alembic.ini'), 'c08b174c95da')

    tables = ('users', 'topics', 'subjects', 'content_blocks', 'categories', 'questions',
              'trivial_board_matches', 'trivial_board_participants', 'trivial_board_turns',
              'trivial_board_operations', 'trivial_board_content_copies', 'trivial_board_presentations')
    tables += ('game_engine_sessions', 'answer_logs', 'pasapalabra_matches', 'pasapalabra_participants',
               'pasapalabra_questions', 'pasapalabra_commands')

    def snapshot():
        with pg.connect() as connection:
            return {name: connection.scalar(text(
                f"SELECT coalesce(jsonb_agg(v ORDER BY v::text), '[]'::jsonb) FROM (SELECT to_jsonb(t) AS v FROM {name} t) rows")) for name in tables}

    before = snapshot()
    with patch('app.database.engine', pg):
        command.upgrade(Config('alembic.ini'), 'head')
    after = snapshot()
    for row in after['trivial_board_matches']:
        assert row.pop('manual_state') is None
        assert row.pop('subject_id') is None
    assert after == before
    with Session(pg) as db, patch.object(historical_content, 'server_now', return_value=old_presentation['state']['presentation']['server_now']):
        actor = db.get(User, users[0])
        assert legacy.read_state(db, actor, old_state['id']) == old_presentation['state']
        assert historical_content.present_internal(db, actor, old_state['id'], old_command)['operation'] == old_presentation['operation']
        with pytest.raises(HTTPException) as error:
            service.read_state(db, actor, old_state['id'])
        assert code(error) == 'UNSUPPORTED_SAVED_VERSION'
    from app.models import Base
    for name in ('trivial_board_matches', 'trivial_board_participants'):
        assert {c['name']: c['nullable'] for c in inspect(pg).get_columns(name)} == {c.name: c.nullable for c in Base.metadata.tables[name].columns}
    state, _ = create(pg, users, None)
    with patch('app.database.engine', pg), pytest.raises(RuntimeError, match='Cannot discard'):
        command.downgrade(Config('alembic.ini'), 'c08b174c95da')
    reload(pg, users, state)


def test_two_online_ordering_actions_lock_the_shared_state_not_only_the_actor(pg):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject, online=True)
    barrier, counter_lock = Barrier(2), Lock()
    draws = []

    def worker(slot):
        with Session(pg) as db:
            db.execute(text("SET LOCAL lock_timeout = '5s'"))
            actor = db.get(User, ids[slot - 1])
            barrier.wait(timeout=5)

            def draw():
                with counter_lock:
                    draws.append(slot)
                return 5

            try:
                return service.execute(db, actor, state['id'], request_for(state, 'order', slot=slot), roller=draw)
            except HTTPException as error:
                return error.detail['code']

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, slot) for slot in (1, 2)]
        results = [future.result(timeout=15) for future in futures]
    assert len(draws) == 1 and 'STALE_VERSION' in results
    result = next(r for r in results if isinstance(r, dict))
    current = reload(pg, ids, result['state'])
    assert current['phase'] == 'ORDERING' and len(current['pending_rollers']) == 1
    current = act(pg, ids, current, 'order', slot=current['pending_rollers'][0], roll=2)[0]['state']
    assert current['phase'] == 'READY' and current['active_participant'] == draws[0]


def test_default_random_is_server_owned_and_not_called_for_confirmed_retry(pg):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject)
    request = request_for(state, 'order', slot=1)
    with Session(pg) as db, patch.object(service.RNG, 'randint', return_value=4) as random:
        actor = db.get(User, ids[0])
        first = service.execute(db, actor, state['id'], request)
        assert first['operation']['roll'] == 4
        assert service.execute(db, actor, state['id'], request) == first
        random.assert_called_once_with(1, 6)


def test_setup_is_atomic_and_missing_or_different_accounts_cannot_create(pg):
    ids, subject = accounts(pg)
    request = InternalSetup(operation_id=uuid4(), play_mode='ONLINE', subject_id=subject,
                            participants=[ParticipantSpec(user_id=ids[0]), ParticipantSpec(user_id=uuid4())])
    with Session(pg) as db:
        with pytest.raises(HTTPException) as error:
            service.create_internal(db, db.get(User, ids[0]), request)
        assert code(error) == 'ACCOUNT_NOT_FOUND'
        for table in (Match, Participant, Turn, Operation):
            assert db.scalar(select(func.count()).select_from(table)) == 0
        with pytest.raises(HTTPException) as error:
            service.create_internal(db, db.get(User, ids[1]), request)
        assert code(error) == 'HOST_MUST_BE_FIRST'


def test_concurrent_creation_has_one_closed_roster_and_original_receipt(pg):
    ids, subject = accounts(pg)
    request = InternalSetup(operation_id=uuid4(), play_mode='LOCAL', subject_id=subject,
                            participants=[ParticipantSpec(user_id=ids[0]), ParticipantSpec(guest_name='Synthetic guest')])
    barrier = Barrier(2)

    def worker():
        with Session(pg) as db:
            actor = db.get(User, ids[0])
            barrier.wait(timeout=5)
            return service.create_internal(db, actor, request)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker) for _ in range(2)]
        results = [future.result(timeout=15) for future in futures]
    assert results[0] == results[1]
    with Session(pg) as db:
        assert db.scalar(select(func.count()).select_from(Match)) == 1
        assert db.scalar(select(func.count()).select_from(Participant)) == 2
        assert db.scalar(select(func.count()).select_from(Operation)) == 1

@pytest.mark.parametrize('online', [False, True])
def test_receipt_after_ended_turn_keeps_original_actor_content_and_die(pg, online):
    ids, subject = accounts(pg)
    initial, _ = create(pg, ids, subject, online=online)
    state = order(pg, ids, initial)
    syringe, syringe_request = act(pg, ids, state, 'advance', roll=5)
    virus, _ = act(pg, ids, syringe['state'], 'advance', roll=2)
    ended, ended_request = act(pg, ids, virus['state'], 'virus', roll=3)
    assert ended['state']['active_participant'] == 2 and ended['state']['turn_number'] == 2
    with Session(pg) as db:
        actor = db.get(User, ids[0])
        before = db.scalar(select(func.count()).select_from(Operation))
        for request, original in ((syringe_request, syringe), (ended_request, ended)):
            assert service.execute(db, actor, state['id'], request,
                                   roller=lambda: pytest.fail('A closed-turn receipt must not roll again')) == original
        with pytest.raises(HTTPException) as error:
            service.execute(db, actor, state['id'], ended_request.model_copy(update={'kind': 'advance'}),
                            roller=lambda: pytest.fail('Changed receipt content cannot roll'))
        assert code(error) == 'IDEMPOTENCY_CONFLICT'
        assert db.scalar(select(func.count()).select_from(Operation)) == before
    reload(pg, ids, ended['state'])


@pytest.mark.parametrize('corruption', ['missing_previous', 'previous_open', 'future_turn', 'ended_without_timestamp', 'open_with_end'])
def test_incoherent_turn_history_refused_before_state_and_receipt(pg, corruption):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject)
    state = order(pg, ids, state)
    state = act(pg, ids, state, 'advance', roll=5)[0]['state']
    state = act(pg, ids, state, 'advance', roll=2)[0]['state']
    ended, receipt = act(pg, ids, state, 'virus', roll=2)
    state = ended['state']
    with Session(pg) as db:
        previous = db.get(Turn, (state['id'], 1))
        current = db.get(Turn, (state['id'], 2))
        if corruption == 'missing_previous':
            db.delete(previous)
        elif corruption == 'previous_open':
            previous.status, previous.reason, previous.ended_at = 'OPEN', None, None
        elif corruption == 'future_turn':
            db.add(Turn(match_id=state['id'], number=3, participant_slot=1, status='OPEN', started_at=service.server_now(db)))
        elif corruption == 'ended_without_timestamp':
            previous.ended_at = None
        else:
            current.ended_at = service.server_now(db)
        db.commit()
    for call in (lambda db: service.read_state(db, db.get(User, ids[0]), state['id']),
                 lambda db: service.execute(db, db.get(User, ids[0]), state['id'], receipt,
                                            roller=lambda: pytest.fail('Corrupt history cannot execute'))):
        with Session(pg) as db, pytest.raises(HTTPException) as error:
            call(db)
        assert code(error) == 'INVALID_SAVED_TURN'


def test_manual_roster_cannot_also_contain_an_independent_legacy_state(pg):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject)
    with Session(pg) as db:
        participant = db.get(Participant, (state['id'], 1))
        participant.position, participant.phase, participant.skip_next_own_turn = 1, 'READY', False
        db.commit()
        with pytest.raises(HTTPException) as error:
            service.read_state(db, db.get(User, ids[0]), state['id'])
        assert code(error) == 'INVALID_SAVED_ROSTER'
