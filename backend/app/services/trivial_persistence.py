"""Internal unit of work for the partial movement engine. No public start/game API.

Caller supplies an actor authenticated by get_current_user; recheck its credential
version here. Each method owns commit/rollback; use a dedicated, clean Session.
"""
from dataclasses import asdict
from random import SystemRandom

from fastapi import HTTPException
from sqlalchemy import select
from pydantic import ValidationError

from app.domain.trivial_movement import MovementEngine, MovementState, Phase, QuestionRequirement, VERSION, load_board
from app.models import User
from app.models.trivial_board import TrivialBoardMatch as Match, TrivialBoardParticipant as Participant, TrivialBoardTurn as Turn, TrivialBoardOperation as Operation
from app.schemas.trivial_board import Board
from app.schemas.trivial_persistence import InternalSetup, MoveCommand, SavedMovementConfiguration
from app.services.pasapalabra import server_now

RULES_VERSION = 'trivial-movement-partial-v1'
RNG = SystemRandom()


def fail(code, status=409):
    raise HTTPException(status, {'code': code})


def clean(db):
    if db.new or db.dirty or db.deleted:
        raise ValueError('Use a dedicated Session without pending writes')


def authenticate(db, actor, *, exclusive=False):
    if not isinstance(actor, User):
        fail('AUTHENTICATION_REQUIRED', 401)
    actor_id, credential_version = actor.id, actor.auth_version
    # Read DB columns without refreshing the authenticated ORM actor in place.
    # The future HTTP boundary must authenticate every request with get_current_user.
    current = db.execute(select(User.id, User.auth_version).where(User.id == actor_id).with_for_update(read=not exclusive)).one_or_none()
    if current is None or current.auth_version != credential_version:
        fail('AUTHENTICATION_REQUIRED', 401)
    return actor


def roster(db, match):
    return list(db.scalars(select(Participant).where(Participant.match_id == match.id).order_by(Participant.slot).execution_options(populate_existing=True)))


def locked(db, actor, match_id):
    match = db.scalar(select(Match).where(Match.id == match_id).execution_options(populate_existing=True).with_for_update())
    if match is None:
        fail('MATCH_NOT_FOUND', 404)
    people = roster(db, match)
    if not (match.owner_id == actor.id if match.play_mode == 'LOCAL' else any(p.user_id == actor.id for p in people)):
        fail('MATCH_NOT_FOUND', 404)
    saved_definition(match, people)
    return match, people


def saved_definition(match, people):
    """Never substitute code's current board/configuration for saved values."""
    if match.rules_version != RULES_VERSION or type(match.state_schema_version) is not int or match.state_schema_version != 1:
        fail('UNSUPPORTED_SAVED_VERSION')
    if match.board_version != VERSION:
        fail('UNSUPPORTED_SAVED_VERSION')
    if not isinstance(match.board_snapshot, dict) or match.board_version != match.board_snapshot.get('version'):
        fail('INVALID_SAVED_BOARD')
    configuration = match.configuration
    if not isinstance(configuration, dict):
        fail('INVALID_SAVED_CONFIGURATION')
    if configuration.get('schema_version', 1) != 1:
        fail('UNSUPPORTED_SAVED_CONFIGURATION')
    try:
        definition = Board.model_validate(match.board_snapshot)
        MovementEngine(definition)
        parsed = SavedMovementConfiguration.model_validate(configuration)
    except (ValidationError, ValueError):
        fail('INVALID_SAVED_CONFIGURATION_OR_BOARD')
    slots = [p.slot for p in people]
    accounts = [p.user_id for p in people if p.user_id is not None]
    if slots != list(range(1, len(people) + 1)) or set(parsed.turn_order) != set(slots):
        fail('INVALID_SAVED_ROSTER')
    if match.play_mode == 'LOCAL':
        valid = 1 <= len(people) <= 4 and accounts == [match.owner_id] and people[0].user_id == match.owner_id
    elif match.play_mode == 'ONLINE':
        valid = 2 <= len(people) <= 4 and len(accounts) == len(people) and len(set(accounts)) == len(accounts) and match.owner_id in accounts
    else:
        valid = False
    if not valid:
        fail('INVALID_SAVED_ROSTER')
    return definition


def authorized_participant(match, people, actor, slot):
    participant = next((p for p in people if p.slot == slot), None)
    if participant is None:
        fail('INVALID_PARTICIPANT', 422)
    if match.play_mode == 'ONLINE' and participant.user_id != actor.id:
        fail('ONLY_OWN_ACTIONS', 403)
    return participant


def movement_state(match, participant, definition):
    phase = Phase(participant.phase)
    cell = definition.cells[participant.position - 1]
    pending = ('BRAIN_PENDING' if cell.kind == 'BRAIN' else 'BAZO_PENDING') if phase == Phase.RULE_PENDING else None
    question = QuestionRequirement(cell.id, cell.bank, cell.level) if phase == Phase.QUESTION_REQUIRED or pending == 'BAZO_PENDING' else None
    return MovementState(position=participant.position, board_version=match.board_version,
                         phase=phase, skip_next_own_turn=participant.skip_next_own_turn,
                         question=question, pending_rule=pending)


def store(participant, state):
    participant.position = state.position
    participant.phase = state.phase.value
    participant.skip_next_own_turn = state.skip_next_own_turn


def view(db, match, people):
    definition = saved_definition(match, people)
    turn = db.get(Turn, (match.id, match.current_turn))
    states = [movement_state(match, p, definition) for p in people]
    active = people[turn.participant_slot - 1]
    state = states[turn.participant_slot - 1]
    return {'id': match.id, 'version': match.version, 'play_mode': match.play_mode,
            'scope': 'MOVEMENT_ONLY', 'board_version': match.board_version,
            'rules_version': match.rules_version, 'state_schema_version': match.state_schema_version,
            'configuration': match.configuration, 'phase': state.phase.value,
            'active_participant': active.slot, 'turn_number': turn.number, 'turn_status': turn.status,
            'question_requirement': asdict(state.question) if state.question else None,
            'pending_rule': state.pending_rule,
            'participants': [{'slot': p.slot, 'name': p.name, 'registered': p.user_id is not None,
                              'position': p.position, 'phase': p.phase, 'skip_next_own_turn': p.skip_next_own_turn} for p in people]}


def create_internal(db, actor, request: InternalSetup):
    """Create a closed movement fixture/aggregate, NOT a playable match.

    List order is an explicit pre-established order from a trusted future caller.
    This method does not implement the prototype's initial ordering dice or ties.
    """
    clean(db)
    try:
        request = InternalSetup.model_validate(request.model_dump())
        actor = authenticate(db, actor, exclusive=True)
        if request.participants[0].user_id != actor.id:
            fail('HOST_MUST_BE_FIRST', 403)
        # Serialize idempotent setup by owner (same lock order as commands).
        payload = request.model_dump(mode='json', exclude={'operation_id'})
        existing = db.scalar(select(Match).where(Match.owner_id == actor.id, Match.setup_operation_id == str(request.operation_id)).with_for_update().execution_options(populate_existing=True))
        if existing:
            if existing.setup_payload != payload:
                fail('IDEMPOTENCY_CONFLICT')
            existing, people = locked(db, actor, existing.id)
            result = view(db, existing, people)
            db.commit()
            return result
        definition = load_board()
        MovementEngine(definition)
        now = server_now(db)
        match = Match(owner_id=actor.id, setup_operation_id=str(request.operation_id), setup_payload=payload,
                      play_mode=request.play_mode, version=1, current_turn=1, board_version=definition.version,
                      rules_version=RULES_VERSION, state_schema_version=1, board_snapshot=definition.model_dump(),
                      configuration={'schema_version': 1, 'scope': 'MOVEMENT_ONLY', 'participants_closed': True,
                                     'turn_order': list(range(1, len(request.participants) + 1)),
                                     'pending_rules': ['BAZO', 'BRAIN', 'CORRECT_TURN', 'EXHAUSTION', 'ABANDONMENT']}, created_at=now)
        db.add(match)
        db.flush()
        people = []
        for slot, spec in enumerate(request.participants, 1):
            account = db.get(User, spec.user_id) if spec.user_id else None
            if spec.user_id and account is None:
                fail('ACCOUNT_NOT_FOUND', 422)
            p = Participant(match_id=match.id, slot=slot, user_id=spec.user_id,
                            name=account.name if account else spec.guest_name.strip(),
                            position=1, phase=Phase.READY.value, skip_next_own_turn=False)
            db.add(p)
            people.append(p)
        db.flush()
        db.add(Turn(match_id=match.id, number=1, participant_slot=1, status='OPEN', started_at=now))
        db.flush()
        result = view(db, match, people)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def read_state(db, actor, match_id):
    clean(db)
    try:
        actor = authenticate(db, actor)
        match, people = locked(db, actor, match_id)
        result = view(db, match, people)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def next_turn(db, match, people, previous, engine, definition, now, events):
    order = match.configuration['turn_order']
    slot = previous.slot
    # At most each participant's pending flag is consumed once, then one is READY.
    for _ in range(len(people) + 1):
        slot = order[(order.index(slot) + 1) % len(order)]
        participant = people[slot - 1]
        match.current_turn += 1
        turn = Turn(match_id=match.id, number=match.current_turn, participant_slot=slot, status='OPEN', started_at=now)
        db.add(turn)
        state = movement_state(match, participant, definition)
        if state.phase == Phase.TURN_ENDED:
            transition = engine.begin_own_turn(state)
            store(participant, transition.state)
            events.extend({'participant_slot': slot, 'turn_number': turn.number, **asdict(e)} for e in transition.events)
            if transition.state.phase == Phase.TURN_ENDED:
                turn.status, turn.reason, turn.ended_at = 'SKIPPED', 'VIRUS_PENALTY', now
                continue
        elif state.phase != Phase.READY:
            fail('UNRESOLVED_PARTICIPANT')
        return
    fail('INVALID_TURN_STATE')


def execute_move(db, actor, match_id, request: MoveCommand, *, roller=None):
    clean(db)
    try:
        request = MoveCommand.model_validate(request.model_dump())
        actor = authenticate(db, actor)
        match, people = locked(db, actor, match_id)
        payload = {'kind': 'move', **request.model_dump(mode='json', exclude={'operation_id'})}
        previous = db.get(Operation, (match.id, str(request.operation_id)))
        if previous:
            if previous.actor_id != actor.id or previous.payload != payload:
                fail('IDEMPOTENCY_CONFLICT')
            # A receipt is not a new move: validate its original participant/turn,
            # not that this historical turn is still the current open turn.
            participant = authorized_participant(match, people, actor, request.participant_slot)
            original_turn = db.get(Turn, (match.id, request.turn_number))
            if previous.participant_slot != participant.slot or original_turn is None or original_turn.participant_slot != participant.slot:
                fail('INVALID_SAVED_RECEIPT')
            result = {'operation': previous.result, 'state': view(db, match, people)}
            db.commit()
            return result
        if request.expected_version != match.version:
            fail('STALE_VERSION')
        if request.turn_number != match.current_turn:
            fail('STALE_TURN')
        turn = db.get(Turn, (match.id, match.current_turn))
        participant = authorized_participant(match, people, actor, request.participant_slot)
        if turn.participant_slot != participant.slot:
            fail('OUT_OF_TURN')
        if participant.phase != Phase.READY.value or turn.status != 'OPEN':
            fail('ARRIVAL_UNRESOLVED')
        definition = saved_definition(match, people)
        engine = MovementEngine(definition)
        before = movement_state(match, participant, definition)
        roll = roller() if roller is not None else RNG.randint(1, 6)
        transition = engine.move(before, roll)
        now = server_now(db)
        store(participant, transition.state)
        events = [{'participant_slot': participant.slot, 'turn_number': turn.number, **asdict(e)} for e in transition.events]
        if transition.state.phase == Phase.TURN_ENDED:
            turn.status, turn.reason, turn.ended_at = 'ENDED', 'VIRUS', now
            next_turn(db, match, people, participant, engine, definition, now, events)
        elif transition.state.phase == Phase.GOAL_REACHED:
            turn.status, turn.reason, turn.ended_at = 'ENDED', 'GOAL_IDENTIFIED', now
        match.version += 1
        receipt = {'operation_id': str(request.operation_id), 'actor_id': str(actor.id),
                   'participant_slot': participant.slot, 'turn_number': request.turn_number,
                   'roll': roll, 'events': events, 'version': match.version}
        db.add(Operation(match_id=match.id, operation_id=str(request.operation_id), actor_id=actor.id,
                         participant_slot=participant.slot, payload=payload, result=receipt, created_at=now))
        db.flush()
        result = {'operation': receipt, 'state': view(db, match, people)}
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
