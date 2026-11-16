"""Frozen question content and presentations only; no selection policy or answers."""
from datetime import timedelta
from sqlalchemy import select
from pydantic import ValidationError
from app.models import Question
from app.models.trivial_content import TrivialContentCopy as ContentCopy, TrivialPresentation as Presentation
from app.models.trivial_board import TrivialBoardOperation as Operation, TrivialBoardTurn as Turn
from app.schemas.game_snapshot import StoredQuestion
from app.schemas.trivial_persistence import PresentationCommand
from app.services.game_questions import playable_question_filter
from app.services.game import _classification
from app.services.trivial_board import destination
from app.services.pasapalabra import server_now, utc
from app.services import trivial_persistence as persistence

NORMAL_SECONDS = 60


def freeze_content(db, match, bindings, now):
    """Part of create_internal's transaction. No commit and no later replacement."""
    for binding in bindings:
        context = destination(db,binding.kind,binding.id)
        column = Question.category_id if binding.kind=='category' else Question.topic_id
        candidates = list(db.scalars(select(Question).where(playable_question_filter('TRIVIAL'),column==binding.id)
                                    .order_by(Question.id).execution_options(populate_existing=True).with_for_update(of=Question,read=True)))
        for q in candidates:
            try:
                stored=StoredQuestion.model_validate(q)
                if not stored.text.strip() or not stored.options or not 0 <= stored.correct_option_index < len(stored.options):
                    raise ValueError('Invalid Trivial content')
            except (ValidationError,ValueError,TypeError):
                persistence.fail('INVALID_ELIGIBLE_QUESTION',422)
            classification={**_classification(q),'topic_name':q.topic.name}
            db.add(ContentCopy(match_id=match.id,question_id=q.id,bank=binding.bank,difficulty=q.difficulty,
                               snapshot_version=1,snapshot=stored.model_dump(),classification=classification,
                               binding_snapshot=context,copied_at=now))
    db.flush()


def public_presentation(db, match, turn, viewer_id):
    record=db.scalar(select(Presentation).where(Presentation.match_id==match.id,
                    Presentation.turn_number==turn.number,Presentation.participant_slot==turn.participant_slot)
                    .order_by(Presentation.id.desc()).limit(1))
    if record is None:
        return None
    copy=db.get(ContentCopy,record.copy_id)
    if copy.snapshot_version!=1:
        persistence.fail('UNSUPPORTED_CONTENT_VERSION')
    now=server_now(db)
    participant=next(p for p in persistence.roster(db,match) if p.slot==record.participant_slot)
    visible=match.play_mode=='LOCAL' or participant.user_id==viewer_id
    stored=StoredQuestion.model_validate(copy.snapshot) if visible else None
    # Explicit allowlist, never serialize an ORM copy or a StoredQuestion.
    return {'id':record.id,'participant_slot':record.participant_slot,'turn_number':record.turn_number,
            'cell':record.cell,'bank':copy.bank,'level':copy.difficulty,
            'opened_at':utc(record.opened_at),'deadline_at':utc(record.deadline_at),'server_now':now,
            'expired':now>=utc(record.deadline_at),
            'question':{'text':stored.text,'options':list(stored.options)} if stored else None}


def present_internal(db,actor,match_id,request:PresentationCommand):
    """Selection is a trusted internal argument, NOT a user-facing command contract."""
    persistence.clean(db)
    try:
        request=PresentationCommand.model_validate(request.model_dump())
        actor=persistence.authenticate(db,actor)
        match,people=persistence.locked(db,actor,match_id)
        payload={'kind':'present',**request.model_dump(mode='json',exclude={'operation_id'})}
        previous=db.get(Operation,(match.id,str(request.operation_id)))
        if previous:
            if previous.actor_id!=actor.id or previous.payload!=payload:
                persistence.fail('IDEMPOTENCY_CONFLICT')
            participant=persistence.authorized_participant(match,people,actor,request.participant_slot)
            original_turn=db.get(Turn,(match.id,request.turn_number))
            if previous.participant_slot!=participant.slot or original_turn is None or original_turn.participant_slot!=participant.slot:
                persistence.fail('INVALID_SAVED_RECEIPT')
            result={'operation':previous.result,'state':persistence.view(db,match,people,actor.id)}
            db.commit()
            return result
        if request.expected_version!=match.version:
            persistence.fail('STALE_VERSION')
        participant=persistence.authorized_participant(match,people,actor,request.participant_slot)
        turn=db.get(Turn,(match.id,match.current_turn))
        if request.turn_number!=turn.number:
            persistence.fail('STALE_TURN')
        if turn.participant_slot!=participant.slot:
            persistence.fail('OUT_OF_TURN')
        if participant.phase!='QUESTION_REQUIRED' or turn.status!='OPEN':
            persistence.fail('ARRIVAL_UNRESOLVED')
        definition=persistence.saved_definition(match,people)
        required=persistence.movement_state(match,participant,definition).question
        if (request.cell,request.bank,request.level)!=(required.cell,required.bank,required.level):
            persistence.fail('QUESTION_REQUIREMENT_MISMATCH')
        # This occurrence must reference the last committed movement arrival, not
        # an arbitrary historical cell or a retry of an old educational occurrence.
        arrival=db.scalar(select(Operation).where(Operation.match_id==match.id,
                          Operation.payload['kind'].as_string()=='move')
                          .order_by(Operation.result['version'].as_integer().desc()).limit(1))
        if (arrival is None or arrival.operation_id!=str(request.arrival_operation_id)
                or arrival.participant_slot!=participant.slot or arrival.result['turn_number']!=turn.number
                or not any(e['kind']=='QUESTION_REQUIRED' and e['destination']==request.cell for e in arrival.result['events'])):
            persistence.fail('ARRIVAL_MISMATCH')
        existing=db.scalar(select(Presentation.id).where(Presentation.match_id==match.id,
                                                       Presentation.arrival_operation_id==arrival.operation_id))
        if existing is not None:
            persistence.fail('PRESENTATION_EXISTS')
        copy=db.scalar(select(ContentCopy).where(ContentCopy.id==request.copy_id,ContentCopy.match_id==match.id))
        if copy is None:
            persistence.fail('COPY_NOT_IN_MATCH',422)
        if copy.snapshot_version!=1:
            persistence.fail('UNSUPPORTED_CONTENT_VERSION')
        if copy.bank!=required.bank or copy.difficulty!=required.level:
            persistence.fail('COPY_REQUIREMENT_MISMATCH')
        binding_keys={(b['bank'],b['kind'],b['id']) for b in match.configuration.get('content_bindings',[])}
        if (copy.bank,copy.binding_snapshot['kind'],copy.binding_snapshot['id']) not in binding_keys:
            persistence.fail('COPY_NOT_IN_CONFIGURATION')
        now=server_now(db)
        record=Presentation(match_id=match.id,participant_slot=participant.slot,turn_number=turn.number,
                            cell=required.cell,copy_id=copy.id,arrival_operation_id=arrival.operation_id,
                            opened_at=now,deadline_at=now+timedelta(seconds=NORMAL_SECONDS))
        db.add(record); db.flush()
        match.version+=1
        receipt={'operation_id':str(request.operation_id),'kind':'present','version':match.version,
                 'presentation_id':record.id,'participant_slot':participant.slot,'turn_number':turn.number}
        db.add(Operation(match_id=match.id,operation_id=str(request.operation_id),actor_id=actor.id,
                         participant_slot=participant.slot,payload=payload,result=receipt,created_at=now))
        db.flush()
        result={'operation':receipt,'state':persistence.view(db,match,people,actor.id)}
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
