"""Internal manual card flow. Never expose a private reader value or raw ORM row.

The future HTTP boundary must authenticate with get_current_user and pass its
actor. A User object is not authentication. Each entry owns commit/rollback and
rechecks current credentials, membership, mode and the original action's role.
"""
from copy import deepcopy
from dataclasses import asdict

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError

from app.domain.inmunoquest_rules import Phase
from app.models.trivial_board import TrivialBoardOperation as Operation
from app.models.trivial_content import TrivialPresentation as Presentation, TrivialContentCopy as Copy
from app.models.inmunoquest_content import InmunoQuestDeck as Deck, InmunoQuestDeckState as DeckState, InmunoQuestEvaluation as Evaluation
from app.schemas.inmunoquest_content import StoredOpenQuestion
from app.schemas.inmunoquest_cards import PresentCommand, EvaluateCommand, ReaderQuery
from app.services import inmunoquest_content as content, inmunoquest_persistence as persistence
from app.utils.server_time import server_now, utc

CIRCULATION_VERSION = 'inmunoquest-circulation-v1'


def fail(code, status=409):
    raise HTTPException(status, {'code': code})


def reader_slot(people, participant_slot):
    """Seats clockwise, facing the centre: left = next seat, wrapping N -> 1."""
    if type(participant_slot) is not int or not 1 <= participant_slot <= len(people):
        fail('INVALID_PARTICIPANT', 422)
    return participant_slot % len(people) + 1


def initialize_decks(db, match):
    """Creation only. Existing prepared games are initialized by the migration."""
    if db.scalar(select(func.count()).select_from(DeckState).where(DeckState.match_id == match.id)):
        fail('CIRCULATION_ALREADY_INITIALIZED')
    for deck in db.execute(select(Deck.bank, Deck.difficulty, Deck.initial_order).where(Deck.match_id == match.id)):
        db.add(DeckState(match_id=match.id, bank=deck.bank, difficulty=deck.difficulty,
                         circulation_version=CIRCULATION_VERSION, cycle=1,
                         available_order=list(deck.initial_order), discard_order=[], reserved_presentation_id=None))
    db.flush()


def _pending(db, match_id):
    return list(db.scalars(select(Presentation).outerjoin(Evaluation,
                (Evaluation.match_id == Presentation.match_id) & (Evaluation.presentation_id == Presentation.id))
                .where(Presentation.match_id == match_id, Presentation.presentation_version == 2,
                       Evaluation.presentation_id.is_(None))))


def validate_flow(db, match, people, state, *, decks=None):
    """Metadata/partition integrity only; no reference answers or live catalog."""
    if 'content_preparation_version' not in match.configuration:
        return
    decks = decks if decks is not None else list(db.execute(
        select(Deck.bank, Deck.difficulty, Deck.initial_order).where(Deck.match_id == match.id)))
    initial = {(d.bank, d.difficulty): set(d.initial_order) for d in decks}
    states = list(db.scalars(select(DeckState).where(DeckState.match_id == match.id).execution_options(populate_existing=True)))
    if len(states) != len(content.KEYS) or {(s.bank,s.difficulty) for s in states} != set(initial):
        fail('INVALID_DECK_CIRCULATION')
    pending = _pending(db, match.id)
    if len(pending) > 1:
        fail('INVALID_PENDING_PRESENTATION')
    pending_by_id = {p.id:p for p in pending}
    reserved_ids = []
    for deck in states:
        if deck.circulation_version != CIRCULATION_VERSION:
            fail('UNSUPPORTED_CIRCULATION_VERSION')
        available, discard = deck.available_order, deck.discard_order
        if (type(available) is not list or type(discard) is not list
                or any(type(x) is not int for x in [*available,*discard])
                or len(available) != len(set(available)) or len(discard) != len(set(discard))):
            fail('INVALID_DECK_CIRCULATION')
        held = set()
        if deck.reserved_presentation_id is not None:
            reserved_ids.append(deck.reserved_presentation_id)
            p = pending_by_id.get(deck.reserved_presentation_id)
            if p is None or p.deck_cycle != deck.cycle:
                fail('INVALID_DECK_RESERVATION')
            held.add(p.copy_id)
            if p.copy_id not in initial[(deck.bank,deck.difficulty)]:
                fail('INVALID_DECK_RESERVATION')
        groups = (set(available),set(discard),held)
        if (groups[0] & groups[1] or groups[0] & held or groups[1] & held
                or set.union(*groups) != initial[(deck.bank,deck.difficulty)]):
            fail('INVALID_DECK_CIRCULATION')
    if set(reserved_ids) != set(pending_by_id) or len(reserved_ids) != len(set(reserved_ids)):
        fail('INVALID_DECK_RESERVATION')
    if pending:
        p = pending[0]
        required = state.question
        if (state.phase != Phase.QUESTION or required is None or match.current_turn != p.turn_number
                or state.active_player.id != str(p.participant_slot) or required.cell != p.cell
                or p.reader_slot != reader_slot(people,p.participant_slot)):
            fail('INVALID_PENDING_PRESENTATION')
        copy = db.execute(select(Copy.bank,Copy.difficulty,Copy.snapshot_version).where(Copy.id == p.copy_id,Copy.match_id == match.id)).one_or_none()
        if copy is None or copy.snapshot_version != 2 or (copy.bank,copy.difficulty) != (required.bank.value,required.level):
            fail('INVALID_PENDING_PRESENTATION')


def _stored(db, match_id, presentation):
    row = db.execute(select(Copy.snapshot,Copy.snapshot_version,Copy.question_id,Copy.bank,Copy.difficulty)
                     .where(Copy.id == presentation.copy_id,Copy.match_id == match_id)).one_or_none()
    if row is None or row.snapshot_version != 2:
        fail('INVALID_PRIVATE_CONTENT')
    invalid = False
    try:
        question = StoredOpenQuestion.model_validate(row.snapshot)
    except ValidationError:
        invalid = True
    if invalid or question.id != row.question_id:
        fail('INVALID_PRIVATE_CONTENT')
    return question, row.bank, row.difficulty


def public_presentation(db, match, state):
    if state.phase != Phase.QUESTION or 'content_preparation_version' not in match.configuration:
        return None
    pending = _pending(db,match.id)
    if not pending:
        return None
    p = pending[0]
    question,bank,level = _stored(db,match.id,p)
    # Current question is audible to all participants. Never serialize the DTO,
    # its answer, a future question or any deck order in this public allowlist.
    return {'id':p.id,'participant_slot':p.participant_slot,'reader_slot':p.reader_slot,
            'turn_number':p.turn_number,'arrival_operation_id':p.arrival_operation_id,
            'request_operation_id':p.request_operation_id,'cell':p.cell,'bank':bank,'difficulty':level,
            'opened_at':utc(p.opened_at).isoformat(),
            'question':{'text':question.text,'note_reference':question.note_reference}}


def _request(db, match, state, request_id):
    latest = db.scalar(select(Operation).where(Operation.match_id == match.id,
                        Operation.payload['kind'].as_string().in_(['advance','choose_bank']),
                        Operation.result['state']['phase'].as_string() == 'QUESTION')
                        .order_by(Operation.result['operation']['version'].as_integer().desc()).limit(1))
    if latest is None or latest.operation_id != str(request_id):
        fail('QUESTION_REQUEST_MISMATCH')
    saved = latest.result.get('state',{})
    requirement = asdict(state.question) if state.question else None
    if (saved.get('question_requirement') != requirement or saved.get('turn_number') != match.current_turn
            or saved.get('active_participant') != int(state.active_player.id)):
        fail('QUESTION_REQUEST_MISMATCH')
    arrival = latest
    if latest.payload['kind'] == 'choose_bank':
        arrival = db.scalar(select(Operation).where(Operation.match_id == match.id,
            Operation.participant_slot == latest.participant_slot,Operation.payload['kind'].as_string() == 'advance',
            Operation.result['state']['phase'].as_string() == 'CHOOSE_BANK',
            Operation.result['state']['turn_number'].as_integer() == match.current_turn,
            Operation.result['operation']['version'].as_integer() < latest.result['operation']['version'])
            .order_by(Operation.result['operation']['version'].as_integer().desc()).limit(1))
        if arrival is None or arrival.result['state']['participants'][latest.participant_slot-1]['position'] != state.question.cell:
            fail('QUESTION_REQUEST_MISMATCH')
    return latest,arrival


def _present_authority(match, people, actor, slot):
    left = reader_slot(people,slot)
    if match.play_mode == 'ONLINE' and actor.id not in (people[slot-1].user_id,people[left-1].user_id):
        fail('ONLY_PLAYER_OR_READER',403)
    return left


def _reader_authority(match, people, actor, slot, requested_reader):
    left = reader_slot(people,slot)
    if requested_reader != left:
        fail('READER_MISMATCH',403)
    if match.play_mode == 'ONLINE' and people[left-1].user_id != actor.id:
        fail('ONLY_READER',403)
    return left


def _presentation(db, match, presentation_id):
    p = db.scalar(select(Presentation).where(Presentation.id == presentation_id,
                  Presentation.match_id == match.id,Presentation.presentation_version == 2))
    if p is None:
        fail('PRESENTATION_NOT_FOUND',404)
    return p


def _receipt(db, match, actor, operation_id, payload):
    prior = db.get(Operation,(match.id,str(operation_id)))
    if prior is not None and (prior.actor_id != actor.id or prior.payload != payload):
        fail('IDEMPOTENCY_CONFLICT')
    return prior


def _save_receipt(db, match, actor, request, payload, result, now):
    db.add(Operation(match_id=match.id,operation_id=str(request.operation_id),actor_id=actor.id,
                     participant_slot=request.participant_slot,payload=payload,result=result,created_at=now))
    db.flush()


def present_internal(db, actor, match_id, request: PresentCommand, *, shuffler=None):
    persistence.clean(db)
    try:
        request = PresentCommand.model_validate(request.model_dump())
        actor = persistence.authenticate(db,actor)
        match,people,state = persistence.locked(db,actor,match_id)
        payload = {'kind':'present',**request.model_dump(mode='json',exclude={'operation_id'})}
        previous = _receipt(db,match,actor,request.operation_id,payload)
        left = _present_authority(match,people,actor,request.participant_slot)
        if previous:
            p = _presentation(db,match,previous.result['operation']['presentation_id'])
            if (p.participant_slot,p.reader_slot,p.turn_number,p.request_operation_id) != (
                    request.participant_slot,left,request.turn_number,str(request.request_operation_id)):
                fail('INVALID_SAVED_RECEIPT')
            result = deepcopy(previous.result)
            db.commit()
            return result
        if (state.phase != Phase.QUESTION or int(state.active_player.id) != request.participant_slot
                or match.current_turn != request.turn_number):
            fail('QUESTION_NOT_PENDING')
        demand,arrival = _request(db,match,state,request.request_operation_id)
        existing = db.scalar(select(Presentation).where(Presentation.match_id == match.id,
                              Presentation.request_operation_id == str(request.request_operation_id)))
        now = server_now(db)
        events = []
        if existing:
            if db.get(Evaluation,(match.id,existing.id)) is not None:
                fail('PRESENTATION_ALREADY_EVALUATED')
            if not demand.result['operation']['version'] <= request.expected_version <= match.version:
                fail('STALE_VERSION')
            p = existing
            events.append({'kind':'PRESENTATION_REUSED','presentation_id':p.id})
        else:
            if request.expected_version != match.version:
                fail('STALE_VERSION')
            if 'content_preparation_version' not in match.configuration:
                fail('CONTENT_NOT_PREPARED')
            required = state.question
            deck = db.get(DeckState,(match.id,required.bank.value,required.level))
            if deck is None or deck.reserved_presentation_id is not None:
                fail('INVALID_DECK_RESERVATION')
            available,discard = list(deck.available_order),list(deck.discard_order)
            if not available:
                if not discard:
                    fail('INVALID_DECK_CIRCULATION')
                available = list(discard)
                (shuffler or content.shuffle_in_place)(available)
                if (any(type(i) is not int for i in available) or len(available) != len(discard)
                        or set(available) != set(discard)):
                    raise ValueError('Invalid server recycle permutation')
                discard = []
                deck.cycle += 1
                events.append({'kind':'DECK_RECYCLED','bank':deck.bank,'difficulty':deck.difficulty,'cycle':deck.cycle})
            copy_id = available.pop(0)
            p = Presentation(match_id=match.id,participant_slot=request.participant_slot,
                             turn_number=request.turn_number,cell=required.cell,copy_id=copy_id,
                             arrival_operation_id=arrival.operation_id,request_operation_id=demand.operation_id,
                             reader_slot=left,presentation_version=2,deck_cycle=deck.cycle,
                             opened_at=now,deadline_at=None)
            db.add(p); db.flush()
            deck.available_order,deck.discard_order,deck.reserved_presentation_id = available,discard,p.id
            match.version += 1
            events.append({'kind':'CARD_PRESENTED','presentation_id':p.id,'participant_slot':p.participant_slot,'reader_slot':left})
        db.flush()
        validate_flow(db,match,people,state)
        result = {'operation':{'operation_id':str(request.operation_id),'kind':'present',
                              'presentation_id':p.id,'version':match.version,'events':events},
                  'state':persistence.view(db,match,people,state)}
        _save_receipt(db,match,actor,request,payload,result,now)
        db.commit()
        return result
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500,{'code':'CARD_PERSISTENCE_FAILED'}) from None
    except Exception:
        db.rollback()
        raise


def reader_view_internal(db, actor, match_id, query: ReaderQuery):
    persistence.clean(db)
    try:
        query = ReaderQuery.model_validate(query.model_dump())
        actor = persistence.authenticate(db,actor)
        match,people,state = persistence.locked(db,actor,match_id)
        p = _presentation(db,match,query.presentation_id)
        _reader_authority(match,people,actor,p.participant_slot,query.reader_slot)
        if (db.get(Evaluation,(match.id,p.id)) is not None or state.phase != Phase.QUESTION
                or state.active_player.id != str(p.participant_slot) or match.current_turn != p.turn_number):
            fail('PRESENTATION_NOT_PENDING')
        _request(db,match,state,p.request_operation_id)
        question,bank,level = _stored(db,match.id,p)
        result = {'presentation_id':p.id,'participant_slot':p.participant_slot,'reader_slot':p.reader_slot,
                  'turn_number':p.turn_number,'bank':bank,'difficulty':level,'opened_at':utc(p.opened_at).isoformat(),
                  'question':{'text':question.text,'reference_answer':question.reference_answer,'note_reference':question.note_reference}}
        db.commit()
        return result
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500,{'code':'CARD_PERSISTENCE_FAILED'}) from None
    except Exception:
        db.rollback()
        raise


def evaluate_internal(db, actor, match_id, request: EvaluateCommand):
    persistence.clean(db)
    try:
        request = EvaluateCommand.model_validate(request.model_dump())
        actor = persistence.authenticate(db,actor)
        match,people,state = persistence.locked(db,actor,match_id)
        payload = {'kind':'evaluate',**request.model_dump(mode='json',exclude={'operation_id'})}
        prior = _receipt(db,match,actor,request.operation_id,payload)
        p = _presentation(db,match,request.presentation_id)
        _reader_authority(match,people,actor,request.participant_slot,request.reader_slot)
        if (p.participant_slot,p.reader_slot,p.turn_number) != (request.participant_slot,request.reader_slot,request.turn_number):
            fail('PRESENTATION_MISMATCH')
        evaluation = db.get(Evaluation,(match.id,p.id))
        if prior:
            if (evaluation is None or evaluation.actor_id != actor.id or evaluation.operation_id != str(request.operation_id)
                    or evaluation.evaluator_slot != request.reader_slot or evaluation.correct != request.correct):
                fail('INVALID_SAVED_RECEIPT')
            result = deepcopy(prior.result)
            db.commit()
            return result
        if evaluation is not None:
            fail('PRESENTATION_ALREADY_EVALUATED')
        if request.expected_version != match.version:
            fail('STALE_VERSION')
        if (state.phase != Phase.QUESTION or state.active_player.id != str(request.participant_slot)
                or match.current_turn != request.turn_number):
            fail('PRESENTATION_NOT_PENDING')
        _request(db,match,state,p.request_operation_id)
        required = state.question
        deck = db.get(DeckState,(match.id,required.bank.value,required.level))
        if deck is None or deck.reserved_presentation_id != p.id:
            fail('PRESENTATION_NOT_PENDING')
        now = server_now(db)
        transition = persistence.ENGINE.evaluate(state,request.correct)
        persistence.store_transition(db,match,transition,now)
        if request.correct:
            deck.discard_order = [*deck.discard_order,p.copy_id]
            card_event = 'CARD_DISCARDED'
        else:
            deck.available_order = [*deck.available_order,p.copy_id]
            card_event = 'CARD_RETURNED_TO_BOTTOM'
        deck.reserved_presentation_id = None
        match.version += 1
        db.flush()
        events = [{'kind':'EVALUATION_RECORDED','presentation_id':p.id,'participant_slot':p.participant_slot,
                   'reader_slot':p.reader_slot,'correct':request.correct},
                  {'kind':card_event,'presentation_id':p.id}, *[asdict(e) for e in transition.events]]
        result = {'operation':{'operation_id':str(request.operation_id),'kind':'evaluate','presentation_id':p.id,
                              'version':match.version,'events':events},
                  'evaluation':{'presentation_id':p.id,'participant_slot':p.participant_slot,
                                'reader_slot':p.reader_slot,'correct':request.correct,'evaluated_at':utc(now).isoformat()},
                  'state':persistence.view(db,match,people,transition.state)}
        _save_receipt(db,match,actor,request,payload,result,now)
        db.add(Evaluation(match_id=match.id,presentation_id=p.id,evaluator_slot=request.reader_slot,
                          actor_id=actor.id,operation_id=str(request.operation_id),correct=request.correct,evaluated_at=now))
        db.flush()
        persistence.validate_turn(db,match,transition.state)
        validate_flow(db,match,people,transition.state)
        db.commit()
        return result
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500,{'code':'CARD_PERSISTENCE_FAILED'}) from None
    except Exception:
        db.rollback()
        raise
