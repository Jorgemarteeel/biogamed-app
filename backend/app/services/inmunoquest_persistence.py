"""Internal manual movement coordinator; no routes, cards, evaluation or GameSession.

The boundary MUST authenticate with get_current_user and pass that actor. A User
object alone is not proof of login. Each entry point rechecks the current account
and credential version, then membership and authorization, including receipt reads.
Methods own commit/rollback and require a dedicated Session without pending writes.
"""
from copy import deepcopy
from dataclasses import asdict
from random import SystemRandom

from sqlalchemy import select, func, case, or_, and_

from app.domain.inmunoquest_rules import (
    InmunoQuestEngine, State, Player, Phase, Bank, integer,
    RULES_VERSION, BOARD_VERSION, START_CELL, FINISH_CELL,
)
from app.models import Subject, User
from app.models.trivial_board import (
    TrivialBoardMatch as Match, TrivialBoardParticipant as Participant,
    TrivialBoardTurn as Turn, TrivialBoardOperation as Operation,
)
from app.schemas.inmunoquest_persistence import InternalSetup, Command
from app.services.trivial_persistence import (
    authenticate, authorized_participant, clean, fail, roster,
)
from app.utils.server_time import server_now

STATE_SCHEMA = 2
RNG = SystemRandom()
ENGINE = InmunoQuestEngine()


def board_manifest():
    return {'version': BOARD_VERSION, 'start_cell': START_CELL, 'finish_cell': FINISH_CELL}


def encode(state, *, pending_rolls=None, ordering_round=1):
    """Only canonical state; winner/order/question are derived, not stored twice."""
    return {
        'players': [asdict(p) for p in state.players],
        'order_groups': [list(g) for g in state.order_groups],
        'phase': state.phase.value, 'active_index': state.active_index,
        'chosen_bank': state.chosen_bank.value if state.chosen_bank else None,
        'pending_rolls': dict(pending_rolls or {}), 'ordering_round': ordering_round,
    }


def recover(match, people):
    """Dispatch only the saved supported version; never upgrade a legacy state."""
    if (match.rules_version != RULES_VERSION or match.board_version != BOARD_VERSION
            or type(match.state_schema_version) is not int or match.state_schema_version != STATE_SCHEMA):
        fail('UNSUPPORTED_SAVED_VERSION')
    if (match.board_snapshot != board_manifest()
            or type(match.board_snapshot.get('start_cell')) is not int
            or type(match.board_snapshot.get('finish_cell')) is not int):
        fail('INVALID_SAVED_BOARD')
    raw = match.manual_state
    expected_keys = {'players', 'order_groups', 'phase', 'active_index', 'chosen_bank', 'pending_rolls', 'ordering_round'}
    try:
        if not isinstance(raw, dict) or set(raw) != expected_keys:
            raise ValueError('Invalid saved state fields')
        if type(raw['players']) is not list or type(raw['order_groups']) is not list:
            raise ValueError('Invalid saved collections')
        if any(type(g) is not list for g in raw['order_groups']):
            raise ValueError('Invalid saved order groups')
        state = State(
            players=tuple(Player(**p) for p in raw['players']),
            order_groups=tuple(tuple(g) for g in raw['order_groups']),
            phase=Phase(raw['phase']), active_index=raw['active_index'],
            chosen_bank=Bank(raw['chosen_bank']) if raw['chosen_bank'] is not None else None,
            rules_version=match.rules_version, board_version=match.board_version,
        )
        integer(raw['ordering_round'], 1, 2**31 - 1)
        pending = raw['pending_rolls']
        if not isinstance(pending, dict) or not set(pending) <= set(state.pending_rollers):
            raise ValueError('Invalid unfinished ordering round')
        for roll in pending.values():
            integer(roll, 1, 6)
        if pending and set(pending) == set(state.pending_rollers):
            raise ValueError('A completed round must already have been resolved')
        if [p.id for p in state.players] != [str(p.slot) for p in people]:
            raise ValueError('State and closed roster disagree')
    except (TypeError, ValueError, KeyError):
        fail('INVALID_SAVED_STATE')
    accounts = [p.user_id for p in people if p.user_id is not None]
    valid_roster = (
        [p.slot for p in people] == list(range(1, len(people) + 1))
        and 2 <= len(people) <= 6 and people[0].user_id == match.owner_id
        and all(p.position is None and p.phase is None and p.skip_next_own_turn is None for p in people)
    )
    if match.play_mode == 'LOCAL':
        valid_roster = valid_roster and accounts == [match.owner_id]
    elif match.play_mode == 'ONLINE':
        valid_roster = valid_roster and len(accounts) == len(people) == len(set(accounts))
    else:
        valid_roster = False
    if not valid_roster:
        fail('INVALID_SAVED_ROSTER')
    config = match.configuration
    if (not isinstance(config, dict) or set(config) != {'schema_version', 'scope', 'participants_closed', 'subject'}
            or type(config.get('schema_version')) is not int or config['schema_version'] != STATE_SCHEMA
            or config.get('scope') != 'MANUAL_MOVEMENT_ONLY' or config.get('participants_closed') is not True):
        fail('INVALID_SAVED_CONFIGURATION')
    subject = config['subject']
    if match.subject_id is None:
        if subject is not None:
            fail('INVALID_SAVED_CONFIGURATION')
    elif (not isinstance(subject, dict) or set(subject) != {'id', 'name'}
          or type(subject['id']) is not int or subject['id'] != match.subject_id
          or not isinstance(subject['name'], str) or not subject['name'].strip()):
        fail('INVALID_SAVED_CONFIGURATION')
    return state


def locked(db, actor, match_id):
    match = db.scalar(select(Match).where(Match.id == match_id)
                      .execution_options(populate_existing=True).with_for_update())
    if match is None:
        fail('MATCH_NOT_FOUND', 404)
    people = roster(db, match)
    belongs = (match.owner_id == actor.id if match.play_mode == 'LOCAL'
               else match.play_mode == 'ONLINE' and any(p.user_id == actor.id for p in people))
    if not belongs:
        fail('MATCH_NOT_FOUND', 404)
    state = recover(match, people)
    validate_turn(db, match, state)
    return match, people, state


def validate_turn(db, match, state):
    turn = db.get(Turn, (match.id, match.current_turn), populate_existing=True)
    # Check the saved log too, not just the currently referenced row. Aggregate
    # in SQL rather than loading every historical turn into the coordinator.
    invalid_metadata = or_(
        Turn.status == 'SKIPPED',
        and_(Turn.status == 'OPEN', or_(Turn.reason.is_not(None), Turn.ended_at.is_not(None))),
        and_(Turn.status == 'ENDED', or_(Turn.reason.is_(None), Turn.ended_at.is_(None))),
        and_(Turn.number < match.current_turn, Turn.reason != 'VIRUS'),
    )
    total, last, open_count, invalid_count = db.execute(
        select(func.count(), func.max(Turn.number),
               func.coalesce(func.sum(case((Turn.status == 'OPEN', 1), else_=0)), 0),
               func.coalesce(func.sum(case((invalid_metadata, 1), else_=0)), 0))
        .select_from(Turn).where(Turn.match_id == match.id)
    ).one()
    if state.phase == Phase.ORDERING:
        if total != 0 or match.current_turn != 1:
            fail('INVALID_SAVED_TURN')
    elif (turn is None or total != match.current_turn or last != match.current_turn
          or open_count != (0 if state.phase == Phase.FINISHED else 1) or invalid_count
          or str(turn.participant_slot) != state.active_player.id
          or turn.status != ('ENDED' if state.phase == Phase.FINISHED else 'OPEN')
          or (state.phase == Phase.FINISHED and turn.reason != 'VICTORY')):
        fail('INVALID_SAVED_TURN')


def public_state(match, people, state):
    # Explicit allowlist: never serialize ORM objects, credentials or private payloads.
    positions = {p.id: p.position for p in state.players}
    return {
        'id': match.id, 'version': match.version, 'play_mode': match.play_mode,
        'rules_version': match.rules_version, 'board_version': match.board_version,
        'state_schema_version': match.state_schema_version, 'scope': 'MANUAL_MOVEMENT_ONLY',
        'subject': deepcopy(match.configuration['subject']), 'phase': state.phase.value,
        'participants': [{'slot': p.slot, 'name': p.name, 'registered': p.user_id is not None,
                          'position': positions[str(p.slot)]} for p in people],
        'turn_order': [int(p) for p in state.turn_order] if state.phase != Phase.ORDERING else None,
        'order_groups': [[int(p) for p in g] for g in state.order_groups],
        'pending_rollers': [int(p) for p in state.pending_rollers if p not in match.manual_state['pending_rolls']],
        'ordering_rolls': {k: v for k, v in match.manual_state['pending_rolls'].items()},
        'ordering_round': match.manual_state['ordering_round'],
        'active_participant': int(state.active_player.id) if state.active_player else None,
        'turn_number': None if state.phase == Phase.ORDERING else match.current_turn,
        'chosen_bank': state.chosen_bank.value if state.chosen_bank else None,
        'question_requirement': asdict(state.question) if state.question else None,
        'winner': int(state.winner) if state.winner else None,
    }


def read_state(db, actor, match_id):
    clean(db)
    try:
        actor = authenticate(db, actor)
        match, people, state = locked(db, actor, match_id)
        result = public_state(match, people, state)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def create_internal(db, actor, request: InternalSetup):
    clean(db)
    try:
        request = InternalSetup.model_validate(request.model_dump())
        actor = authenticate(db, actor, exclusive=True)
        if request.participants[0].user_id != actor.id:
            fail('HOST_MUST_BE_FIRST', 403)
        payload = {'kind': 'setup', **request.model_dump(mode='json', exclude={'operation_id'})}
        match = db.scalar(select(Match).where(Match.owner_id == actor.id,
                          Match.setup_operation_id == str(request.operation_id))
                          .execution_options(populate_existing=True).with_for_update())
        if match is not None:
            if match.setup_payload != payload:
                fail('IDEMPOTENCY_CONFLICT')
            match, people, state = locked(db, actor, match.id)
            receipt = db.get(Operation, (match.id, str(request.operation_id)))
            if (receipt is None or receipt.actor_id != actor.id or receipt.payload != payload
                    or receipt.participant_slot != 1):
                fail('INVALID_SAVED_RECEIPT')
            result = deepcopy(receipt.result['state'])
            db.commit()
            return result
        subject = None
        if request.subject_id is not None:
            row = db.scalar(select(Subject).where(Subject.id == request.subject_id).with_for_update(read=True))
            if row is None:
                fail('SUBJECT_NOT_FOUND', 422)
            subject = {'id': row.id, 'name': row.name}
        now = server_now(db)
        state = ENGINE.prepare(tuple(str(slot) for slot in range(1, len(request.participants) + 1)))
        match = Match(
            owner_id=actor.id, setup_operation_id=str(request.operation_id), setup_payload=payload,
            play_mode=request.play_mode, subject_id=request.subject_id, version=1, current_turn=1,
            board_version=BOARD_VERSION, rules_version=RULES_VERSION, state_schema_version=STATE_SCHEMA,
            board_snapshot=board_manifest(), manual_state=encode(state),
            configuration={'schema_version': STATE_SCHEMA, 'scope': 'MANUAL_MOVEMENT_ONLY',
                           'participants_closed': True, 'subject': subject}, created_at=now,
        )
        db.add(match)
        db.flush()
        people = []
        for slot, spec in enumerate(request.participants, 1):
            account = db.get(User, spec.user_id) if spec.user_id is not None else None
            if spec.user_id is not None and account is None:
                fail('ACCOUNT_NOT_FOUND', 422)
            person = Participant(match_id=match.id, slot=slot, user_id=spec.user_id,
                                 name=account.name if account else spec.guest_name.strip(),
                                 position=None, phase=None, skip_next_own_turn=None)
            db.add(person)
            people.append(person)
        db.flush()
        result = public_state(match, people, recover(match, people))
        db.add(Operation(match_id=match.id, operation_id=str(request.operation_id), actor_id=actor.id,
                         participant_slot=1, payload=payload, result={'state': result}, created_at=now))
        db.flush()
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def store_transition(db, match, transition, now):
    """Project only explicit engine turn events; never recalculate game effects."""
    for event in transition.events:
        if event.kind in ('TURN_ENDED', 'VICTORY'):
            turn = db.get(Turn, (match.id, match.current_turn))
            if turn is None or turn.status != 'OPEN' or str(turn.participant_slot) != event.participant:
                fail('INVALID_SAVED_TURN')
            turn.status, turn.ended_at = 'ENDED', now
            turn.reason = 'VICTORY' if event.kind == 'VICTORY' else 'VIRUS'
        elif event.kind == 'TURN_STARTED':
            if db.get(Turn, (match.id, match.current_turn)) is not None:
                match.current_turn += 1
            db.add(Turn(match_id=match.id, number=match.current_turn, participant_slot=int(event.participant),
                        status='OPEN', started_at=now))
    match.manual_state = encode(transition.state, ordering_round=match.manual_state['ordering_round'])


def execute(db, actor, match_id, request: Command, *, roller=None):
    clean(db)
    try:
        request = Command.model_validate(request.model_dump())
        actor = authenticate(db, actor)
        match, people, state = locked(db, actor, match_id)
        participant = authorized_participant(match, people, actor, request.participant_slot)
        payload = request.model_dump(mode='json', exclude={'operation_id'})
        previous = db.get(Operation, (match.id, str(request.operation_id)))
        if previous is not None:
            if previous.actor_id != actor.id or previous.payload != payload or previous.participant_slot != participant.slot:
                fail('IDEMPOTENCY_CONFLICT')
            result = deepcopy(previous.result)
            db.commit()
            return result
        if request.expected_version != match.version:
            fail('STALE_VERSION')
        phase_map = {'order': (Phase.ORDERING,), 'advance': (Phase.READY, Phase.ROLL_AGAIN),
                     'virus': (Phase.VIRUS_ROLL,), 'choose_bank': (Phase.CHOOSE_BANK,)}
        if state.phase not in phase_map[request.kind]:
            fail('ACTION_NOT_ALLOWED')
        if request.kind != 'order':
            if request.turn_number != match.current_turn:
                fail('STALE_TURN')
            if state.active_player.id != str(participant.slot):
                fail('OUT_OF_TURN')
        elif str(participant.slot) not in state.pending_rollers:
            fail('NOT_IN_TIEBREAK')
        elif str(participant.slot) in match.manual_state['pending_rolls']:
            fail('ORDER_ALREADY_ROLLED')
        roll = None
        if request.kind != 'choose_bank':
            roll = roller() if roller is not None else RNG.randint(1, 6)
            integer(roll, 1, 6)
        now = server_now(db)
        ordering_round = match.manual_state['ordering_round'] if request.kind == 'order' else None
        events = []
        if request.kind == 'order':
            pending = {**match.manual_state['pending_rolls'], str(participant.slot): roll}
            if set(pending) == set(state.pending_rollers):
                transition = ENGINE.order_rolls(state, pending)
                store_transition(db, match, transition, now)
                events = [asdict(e) for e in transition.events]
                if transition.state.phase == Phase.ORDERING:
                    match.manual_state = {**match.manual_state, 'ordering_round': match.manual_state['ordering_round'] + 1}
            else:
                match.manual_state = {**match.manual_state, 'pending_rolls': pending}
        else:
            transition = (ENGINE.advance(state, roll) if request.kind == 'advance' else
                          ENGINE.retreat_virus(state, roll) if request.kind == 'virus' else
                          ENGINE.choose_bank(state, request.bank))
            store_transition(db, match, transition, now)
            events = [asdict(e) for e in transition.events]
        match.version += 1
        db.flush()
        recovered = recover(match, people)
        validate_turn(db, match, recovered)
        result = {
            'operation': {'operation_id': str(request.operation_id), 'participant_slot': participant.slot,
                          'kind': request.kind, 'roll': roll, 'ordering_round': ordering_round,
                          'events': events, 'version': match.version},
            'state': public_state(match, people, recovered),
        }
        db.add(Operation(match_id=match.id, operation_id=str(request.operation_id), actor_id=actor.id,
                         participant_slot=participant.slot, payload=payload, result=result, created_at=now))
        db.flush()
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
