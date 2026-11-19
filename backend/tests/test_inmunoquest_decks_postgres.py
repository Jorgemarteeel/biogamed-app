"""Automatic deck preparation: exclusively guarded, disposable PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock
from unittest.mock import patch
from uuid import uuid4
import json
import traceback

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select, func, text, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User, Question, Subject, ContentBlock, Category, Topic, GameSession, AnswerLog
from app.models.trivial_board import TrivialBoardMatch as Match, TrivialBoardParticipant as Participant, TrivialBoardOperation as Operation
from app.models.trivial_content import TrivialContentCopy as Copy, TrivialPresentation as Presentation
from app.models.inmunoquest_content import InmunoQuestDeck as Deck
from app.services import inmunoquest_persistence as service, inmunoquest_content as content
from app.schemas.inmunoquest_persistence import InternalSetup
from app.schemas.trivial_persistence import ParticipantSpec
from test_inmunoquest_persistence_postgres import pg, accounts, create, reload, code
from inmunoquest_content_fixtures import seed_open_questions


def private(engine, user_id, match_id):
    with Session(engine) as db:
        actor = service.authenticate(db, db.get(User, user_id))
        match, _, _ = service.locked(db, actor, match_id)
        return content.recover_private_decks(db, match)


def counts(engine):
    with Session(engine) as db:
        return {table.__tablename__: db.scalar(select(func.count()).select_from(table))
                for table in (Match, Participant, Copy, Deck, Operation, Presentation, GameSession, AnswerLog)}


def zero_aggregates(engine):
    assert not any(counts(engine).values())


def setup_request(ids, subject, *, operation=None, online=False):
    return InternalSetup(operation_id=operation or uuid4(), subject_id=subject,
                         play_mode='ONLINE' if online else 'LOCAL',
                         participants=[ParticipantSpec(user_id=ids[0]),
                                       ParticipantSpec(user_id=ids[1]) if online else ParticipantSpec(guest_name='Synthetic guest')])


def test_twenty_shared_decks_variable_counts_real_hierarchy_and_format_isolation(pg):
    ids, subject = accounts(pg)
    with Session(pg) as db:
        other = Subject(name='Synthetic other subject')
        topic = Topic(name='LYMPHOCYTE')  # A name is never a bank binding.
        db.add_all([other, topic]); db.flush()
        block = ContentBlock(subject_id=subject, name='Synthetic block')
        db.add(block); db.flush()
        category = Category(name='Synthetic category', block_id=block.id)
        orphan = Category(name='Synthetic category without block')
        db.add_all([category, orphan]); db.flush()
        base = list(db.scalars(select(Question).where(Question.subject_id == subject).order_by(Question.id)))
        base[0].block_id, base[0].category_id = block.id, category.id
        base[1].block_id = block.id
        # A real category link can provide available block context without
        # rewriting the source's direct NULL block association.
        base[2].category_id = category.id
        base[3].category_id = orphan.id
        extras = seed_open_questions(db, subject, counts={key: (3 if key == ('FLASK', 2) else 0) for key in content.KEYS})
        excluded = seed_open_questions(db, other.id)
        excluded += seed_open_questions(db, None)
        # A category link alone must not turn a NULL direct subject into an
        # eligible question or silently classify it during preparation.
        excluded[-1].category_id = category.id
        retired = Question(question_type='INMUNOQUEST', subject_id=subject, bank='DNA', difficulty=1,
                           text='Retired synthetic', reference_answer='Retired private', is_active=False)
        trivial = Question(question_type='TRIVIAL', subject_id=subject, topic_id=topic.id, text='Synthetic options',
                           correct_answer='A', options=['A','B','C','D'], correct_option_index=0)
        pasa = Question(question_type='PASAPALABRA', subject_id=subject, topic_id=topic.id, text='Synthetic word',
                        correct_answer='Aorta', exact_word='Aorta', letter='A')
        db.add_all([retired, trivial, pasa]); db.commit()
        expected = {q.id for q in [*base, *extras]}
        excluded_ids = {q.id for q in [*excluded, retired, trivial, pasa]}
        category_name, block_name = category.name, block.name
    state, _ = create(pg, ids, subject, size=6)
    decks = private(pg, ids[0], state['id'])
    assert len(decks) == 20 and {(d['bank'], d['difficulty']) for d in decks} == set(content.KEYS)
    cards = [card for deck in decks for card in deck['cards']]
    assert len(cards) == 23 and {c['question'].id for c in cards} == expected
    assert not excluded_ids & {c['question'].id for c in cards}
    assert [len(d['cards']) for d in decks if (d['bank'], d['difficulty']) == ('FLASK', 2)] == [4]
    by_id = {c['question'].id: c for c in cards}
    for qid in [base[0].id, base[2].id]:
        assert by_id[qid]['academic']['category_name'] == category_name
        assert by_id[qid]['academic']['block_name'] == block_name
    assert by_id[base[3].id]['academic']['category_name'] == 'Synthetic category without block'
    assert by_id[base[3].id]['academic']['block_id'] is None
    with Session(pg) as db:
        assert db.get(Question, base[2].id).block_id is None
        assert db.scalar(select(func.count()).select_from(Deck)) == 20  # Not twenty per participant.
        assert db.scalar(select(func.count()).select_from(GameSession)) == 0
        assert db.scalar(select(func.count()).select_from(Presentation)) == 0
    assert 'Private synthetic reference' not in json.dumps(state)
    assert 'reference_answer' not in json.dumps(state)
    assert all('options' not in c['question'].model_dump() for c in cards)


@pytest.mark.parametrize('invalid', ['retired', 'blank', 'invalid_reference', 'wrong_subject', 'contradictory_hierarchy'])
def test_exact_empty_decks_and_invalid_sources_reject_atomically(pg, invalid):
    ids, subject = accounts(pg)
    with Session(pg) as db:
        q = db.scalar(select(Question).where(Question.subject_id == subject, Question.bank == 'LYMPHOCYTE', Question.difficulty == 1))
        another = Subject(name='Synthetic foreign subject'); db.add(another); db.flush()
        if invalid == 'retired': q.is_active = False
        elif invalid == 'blank': q.text = '   '
        elif invalid == 'invalid_reference': q.reference_answer = '\t'
        elif invalid == 'wrong_subject': q.subject_id = another.id
        else:
            block = ContentBlock(subject_id=another.id, name='Foreign synthetic block'); db.add(block); db.flush()
            q.block_id = block.id
        # A second genuinely empty deck must also be named, never substituted.
        db.scalar(select(Question).where(Question.subject_id == subject, Question.bank == 'DNA', Question.difficulty == 4)).is_active = False
        db.commit()
    with pytest.raises(HTTPException) as error:
        create(pg, ids, subject)
    assert error.value.detail == {'code':'EMPTY_INMUNOQUEST_DECKS', 'minimum_per_deck':1,
                                  'missing_decks':[{'bank':'LYMPHOCYTE','difficulty':1},{'bank':'DNA','difficulty':4}]}
    zero_aggregates(pg)


def test_all_twenty_missing_and_subject_required_no_partial_start(pg):
    ids, subject = accounts(pg)
    with Session(pg) as db:
        for q in db.scalars(select(Question).where(Question.subject_id == subject)): q.is_active = False
        db.commit()
    with pytest.raises(HTTPException) as error:
        create(pg, ids, subject)
    assert error.value.detail['missing_decks'] == [{'bank':bank,'difficulty':level} for bank,level in content.KEYS]
    with pytest.raises(HTTPException) as error:
        create(pg, ids, None)
    assert code(error) == 'SUBJECT_REQUIRED'
    zero_aggregates(pg)


def test_frozen_open_copies_survive_source_edit_retirement_and_reclassification(pg):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject)
    before = private(pg, ids[0], state['id'])
    card = before[0]['cards'][0]
    with Session(pg) as db:
        foreign = Subject(name='Synthetic moved subject'); db.add(foreign); db.flush()
        q = db.get(Question, card['question'].id)
        q.text, q.reference_answer, q.note_reference = 'New text', 'New private answer', 'T16'
        q.is_active, q.subject_id, q.bank, q.difficulty = False, foreign.id, 'DNA', 4
        db.get(Subject, subject).name = 'Synthetic renamed source subject'
        db.commit()
    assert private(pg, ids[0], state['id']) == before
    reload(pg, ids, state)
    with Session(pg) as db:
        assert db.get(Copy, card['copy_id']).snapshot['text'] != 'New text'


def test_identical_text_in_different_banks_is_not_merged(pg):
    ids, subject = accounts(pg)
    with Session(pg) as db:
        qs = list(db.scalars(select(Question).where(Question.subject_id == subject, Question.difficulty == 1).order_by(Question.id)))
        for q in qs[:2]: q.text, q.reference_answer = 'Same synthetic wording', 'Same private reference'
        source_ids = {q.id for q in qs[:2]}; db.commit()
    state, _ = create(pg, ids, subject)
    cards = [c for d in private(pg, ids[0], state['id']) for c in d['cards'] if c['question'].id in source_ids]
    assert len(cards) == 2 and len({c['bank'] for c in cards}) == 2 and len({c['copy_id'] for c in cards}) == 2


def test_saved_shuffle_recovery_retry_and_no_live_catalog_reads(pg):
    ids, subject = accounts(pg)
    with Session(pg) as db:
        seed_open_questions(db, subject, counts={key:2 for key in content.KEYS}); db.commit()
    shuffles = []

    def reverse(values):
        shuffles.append(tuple(values)); values.reverse()

    request = setup_request(ids, subject)
    with Session(pg) as db:
        state = service.create_internal(db, db.get(User, ids[0]), request, shuffler=reverse)
    before = private(pg, ids[0], state['id'])
    assert len(shuffles) == 20
    assert [d['copy_ids'] for d in before] == [tuple(reversed(values)) for values in shuffles]
    assert all(d['shuffle_version'] == content.SHUFFLE_VERSION for d in before)
    with Session(pg) as db:
        for q in db.scalars(select(Question).where(Question.subject_id == subject)): q.is_active = False
        db.commit()
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany): statements.append(statement.lower())

    event.listen(pg, 'before_cursor_execute', capture)
    try:
        with patch.object(content, '_selected_rows', side_effect=AssertionError('No live catalog on retry')):
            with Session(pg) as db:
                assert service.create_internal(db, db.get(User, ids[0]), request,
                                               shuffler=lambda values: pytest.fail('No retry shuffle')) == state
            reload(pg, ids, state)
            assert private(pg, ids[0], state['id']) == before
    finally:
        event.remove(pg, 'before_cursor_execute', capture)
    assert not any('from questions' in statement or 'join questions' in statement for statement in statements)
    assert counts(pg)['trivial_board_content_copies'] == 60 and counts(pg)['inmunoquest_decks'] == 20


@pytest.mark.parametrize('failure', ['shuffle', 'receipt', 'commit', 'bad_permutation'])
def test_full_creation_rolls_back_copies_decks_participants_and_receipt(pg, failure):
    ids, subject = accounts(pg)
    calls = []

    def shuffle(values):
        calls.append(1)
        if failure == 'shuffle' and len(calls) == 11: raise RuntimeError('Synthetic shuffle fault')
        if failure == 'bad_permutation': values.append(values[0])

    with Session(pg) as db:
        actor = db.get(User, ids[0])
        context = (patch.object(service.Operation, '__init__', side_effect=RuntimeError('Synthetic receipt fault')) if failure == 'receipt'
                   else patch.object(db, 'commit', side_effect=RuntimeError('Synthetic commit fault')) if failure == 'commit'
                   else patch.object(content, 'shuffle_in_place', shuffle))
        with context, pytest.raises(ValueError if failure == 'bad_permutation' else RuntimeError):
            service.create_internal(db, actor, setup_request(ids, subject), shuffler=shuffle)
    zero_aggregates(pg)


def test_database_failures_and_invalid_content_do_not_leak_reference_answers(pg, caplog):
    ids, subject = accounts(pg)
    secret = 'Private synthetic sentinel never in diagnostics'
    with Session(pg) as db:
        actor = db.get(User, ids[0])
        with patch.object(service, 'public_state', side_effect=IntegrityError('synthetic insert', {'answer':secret}, Exception('synthetic'))):
            with pytest.raises(HTTPException) as error:
                service.create_internal(db, actor, setup_request(ids, subject))
        assert error.value.status_code == 500 and code(error) == 'MATCH_PERSISTENCE_FAILED'
        assert secret not in ''.join(traceback.format_exception(error.value)) and secret not in caplog.text
    zero_aggregates(pg)


def test_questions_and_deck_orders_are_immutable_in_postgresql(pg):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject)
    saved = private(pg, ids[0], state['id'])
    for target in ('copy', 'deck'):
        with Session(pg) as db, pytest.raises(IntegrityError):
            if target == 'copy':
                db.get(Copy, saved[0]['cards'][0]['copy_id']).snapshot = {'text':'Changed'}
            else:
                db.get(Deck, (state['id'], saved[0]['bank'], saved[0]['difficulty'])).initial_order = []
            db.commit()
    assert private(pg, ids[0], state['id']) == saved


@pytest.mark.parametrize('same_actor', [True, False])
def test_real_concurrent_creation_freezes_and_shuffles_only_once(pg, same_actor):
    ids, subject = accounts(pg)
    barrier, count_lock = Barrier(2), Lock()
    calls = []
    operation = uuid4()

    def worker(index):
        actor_id = ids[0] if same_actor or index == 0 else ids[1]
        roster = ids if actor_id == ids[0] else [ids[1], ids[0], *ids[2:]]
        request = setup_request(roster, subject, operation=operation, online=True)
        with Session(pg) as db:
            db.execute(text("SET LOCAL lock_timeout = '6s'"))
            actor = db.get(User, actor_id)
            barrier.wait(timeout=5)

            def shuffle(values):
                with count_lock: calls.append(1)
                values.reverse()

            try: return service.create_internal(db, actor, request, shuffler=shuffle)
            except HTTPException as error: return error.detail['code']

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, index) for index in (0, 1)]
        results = [future.result(timeout=20) for future in futures]
    if same_actor: assert results[0] == results[1]
    else: assert 'IDEMPOTENCY_CONFLICT' in results and sum(isinstance(r, dict) for r in results) == 1
    assert len(calls) == 20
    assert counts(pg)['trivial_board_matches'] == 1 and counts(pg)['trivial_board_content_copies'] == 20


def test_single_catalog_snapshot_is_consistent_during_edits(pg):
    ids, subject = accounts(pg)
    captured, edited = Event(), Event()
    original_select = content._selected_rows
    with Session(pg) as db:
        source_ids = list(db.scalars(select(Question.id).where(Question.subject_id == subject).order_by(Question.id).limit(2)))
        old_texts = {q.id:q.text for q in db.scalars(select(Question).where(Question.id.in_(source_ids)))}

    def selected(db, subject_id):
        rows = original_select(db, subject_id)
        captured.set()
        assert edited.wait(timeout=8)
        return rows

    def creator():
        with Session(pg) as db:
            return service.create_internal(db, db.get(User, ids[0]), setup_request(ids, subject))

    with patch.object(content, '_selected_rows', selected), ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(creator)
        assert captured.wait(timeout=8)
        try:
            with Session(pg) as db:
                for q in db.scalars(select(Question).where(Question.id.in_(source_ids))):
                    q.text, q.reference_answer, q.is_active = 'Committed newer text', 'Committed newer private answer', False
                db.commit()
        finally: edited.set()
        state = future.result(timeout=15)
    saved = [c for d in private(pg, ids[0], state['id']) for c in d['cards'] if c['question'].id in source_ids]
    assert {c['question'].id:c['question'].text for c in saved} == old_texts
    assert len(saved) == 2


def test_permissions_actor_content_conflicts_and_forbidden_client_selections(pg):
    ids, subject = accounts(pg)
    request = setup_request(ids, subject)
    with Session(pg) as db:
        state = service.create_internal(db, db.get(User, ids[0]), request)
        for altered, actor_id, expected in (
            (request, ids[1], 'HOST_MUST_BE_FIRST'),
            (request.model_copy(update={'subject_id':None}), ids[0], 'IDEMPOTENCY_CONFLICT'),
            (setup_request([ids[1], ids[0]], subject, operation=request.operation_id), ids[1], 'IDEMPOTENCY_CONFLICT'),
        ):
            with pytest.raises(HTTPException) as error:
                service.create_internal(db, db.get(User, actor_id), altered, shuffler=lambda values:pytest.fail('Rejected requests cannot shuffle'))
            assert code(error) == expected
        with pytest.raises(HTTPException) as error:
            service.read_state(db, db.get(User, ids[6]), state['id'])
        assert code(error) == 'MATCH_NOT_FOUND'
    for extra in ({'question_ids':[1]}, {'initial_order':[1]}, {'difficulty':1}, {'category_id':1}):
        with pytest.raises(ValidationError): InternalSetup.model_validate(request.model_dump() | extra)


def seed_pre_decks_manual(db, actor, *, subject_id=None, operation=None):
    """Exact synthetic pre-delivery aggregate shape, with no prepared content."""
    request = setup_request([actor.id], subject_id, operation=operation)
    state = service.ENGINE.prepare(('1', '2'))
    subject = db.get(Subject, subject_id) if subject_id else None
    match = Match(owner_id=actor.id, setup_operation_id=str(request.operation_id),
                  setup_payload={'kind':'setup', **request.model_dump(mode='json', exclude={'operation_id'})},
                  play_mode='LOCAL', subject_id=subject_id, version=1, current_turn=1,
                  board_version=service.BOARD_VERSION, rules_version=service.RULES_VERSION, state_schema_version=2,
                  board_snapshot=service.board_manifest(), manual_state=service.encode(state),
                  configuration={'schema_version':2,'scope':'MANUAL_MOVEMENT_ONLY','participants_closed':True,
                                 'subject':{'id':subject.id,'name':subject.name} if subject else None}, created_at=service.server_now(db))
    db.add(match); db.flush()
    people = [Participant(match_id=match.id,slot=1,user_id=actor.id,name=actor.name,position=None,phase=None,skip_next_own_turn=None),
              Participant(match_id=match.id,slot=2,name='Synthetic old guest',position=None,phase=None,skip_next_own_turn=None)]
    db.add_all(people); db.flush()
    view = service.public_state(match, people, state)
    db.add(Operation(match_id=match.id,operation_id=str(request.operation_id),actor_id=actor.id,participant_slot=1,
                     payload=match.setup_payload,result={'state':view},created_at=match.created_at))
    db.commit()
    return view, request


def test_additive_migration_preserves_html_copies_and_old_manual_states_without_backfill(pg):
    from test_trivial_content_postgres import prepare, arrival, present, request_for
    from app.services import trivial_persistence as old_service, trivial_content as old_content
    users, html, _, _, _, _ = prepare(pg, bank='SYRINGE')
    moved, move_request = arrival(pg, users, html, roll=5)
    presentation_request = request_for(pg, moved['state'], move_request)
    presented = present(pg, users[0], moved['state'], presentation_request)
    with Session(pg) as db:
        manual, setup = seed_pre_decks_manual(db, db.get(User, users[0]))
    # Build a v1-only fixture with the current ORM, then remove additive empty
    # structures before recording the old schema. No version-2 presentation or
    # prepared deck is discarded; f3/e2 guards remain active.
    with patch('app.database.engine', pg): command.downgrade(Config('alembic.ini'), 'd19c285da6eb')
    tables=('users','topics','subjects','content_blocks','categories','questions','trivial_board_matches',
            'trivial_board_participants','trivial_board_turns','trivial_board_operations',
            'trivial_board_content_copies','trivial_board_presentations')
    def rows():
        with pg.connect() as connection:
            return {name:connection.scalar(text(f"SELECT coalesce(jsonb_agg(v ORDER BY v::text),'[]'::jsonb) FROM (SELECT to_jsonb(t) v FROM {name} t) data")) for name in tables}
    before = rows()
    with patch('app.database.engine', pg): command.upgrade(Config('alembic.ini'), 'head')
    after = rows()
    for p in after['trivial_board_presentations']:
        assert p.pop('presentation_version') == 1
        for field in ('reader_slot','request_operation_id','deck_cycle'):
            assert p.pop(field) is None
    assert after == before
    with Session(pg) as db, patch.object(old_content, 'server_now', return_value=presented['state']['presentation']['server_now']):
        actor = db.get(User, users[0])
        assert old_service.read_state(db, actor, html['id']) == presented['state']
        assert service.read_state(db, actor, manual['id']) == manual
        assert service.create_internal(db, actor, setup, shuffler=lambda values:pytest.fail('No historical backfill')) == manual
        assert db.scalar(select(func.count()).select_from(Deck)) == 0
        assert db.scalar(select(func.count()).select_from(Copy).where(Copy.snapshot_version == 2)) == 0
        match, _, _ = service.locked(db, actor, manual['id'])
        with pytest.raises(HTTPException) as error: content.recover_private_decks(db, match)
        assert code(error) == 'CONTENT_NOT_PREPARED'


def test_downgrade_guard_and_saved_procedure_versions(pg):
    ids, subject = accounts(pg)
    state, _ = create(pg, ids, subject)
    saved = private(pg, ids[0], state['id'])
    with patch('app.database.engine', pg), pytest.raises(RuntimeError, match='Cannot discard prepared'):
        command.downgrade(Config('alembic.ini'), 'd19c285da6eb')
    assert private(pg, ids[0], state['id']) == saved
    with Session(pg) as db:
        match = db.get(Match, state['id'])
        match.configuration = {**match.configuration, 'content_preparation_version':'future'}
        db.commit()
        with pytest.raises(HTTPException) as error: service.read_state(db, db.get(User, ids[0]), state['id'])
        assert code(error) == 'UNSUPPORTED_CONTENT_VERSION'


def test_unknown_saved_shuffle_procedure_is_not_silently_reinterpreted(pg):
    ids, subject = accounts(pg)
    with patch.object(content, 'SHUFFLE_VERSION', 'synthetic-future-procedure'):
        state, _ = create(pg, ids, subject)
    with Session(pg) as db, pytest.raises(HTTPException) as error:
        service.read_state(db, db.get(User, ids[0]), state['id'])
    assert code(error) == 'UNSUPPORTED_SHUFFLE_VERSION'


def test_historical_owner_scoped_duplicate_keys_remain_recoverable(pg):
    ids, subject = accounts(pg)
    operation = uuid4()
    with Session(pg) as db:
        first, first_request = seed_pre_decks_manual(db, db.get(User, ids[0]), operation=operation)
        second, second_request = seed_pre_decks_manual(db, db.get(User, ids[1]), operation=operation)
        for actor_id, request, expected in ((ids[0], first_request, first), (ids[1], second_request, second)):
            assert service.create_internal(db, db.get(User, actor_id), request,
                                           shuffler=lambda values:pytest.fail('Old receipts must not freeze content')) == expected
        new_request = setup_request([ids[2], ids[0]], subject, operation=operation)
        with pytest.raises(HTTPException) as error:
            service.create_internal(db, db.get(User, ids[2]), new_request)
        assert code(error) == 'IDEMPOTENCY_CONFLICT'
        assert db.scalar(select(func.count()).select_from(Deck)) == 0


def test_spanish_multiline_content_and_optional_reference_are_frozen_verbatim(pg):
    ids, subject = accounts(pg)
    text_value = '  ¿Qué función tiene esta célula?\nSegunda línea, con ñ y «comillas».  '
    answer_value = 'Respuesta de referencia: señalización.\nIncluye varios elementos y tildes.'
    with Session(pg) as db:
        q = db.scalar(select(Question).where(Question.subject_id == subject).order_by(Question.id))
        q.text, q.reference_answer, q.note_reference = text_value, answer_value, None
        db.commit()
    state, _ = create(pg, ids, subject)
    stored = private(pg, ids[0], state['id'])[0]['cards'][0]['question']
    assert stored.text == text_value and stored.reference_answer == answer_value and stored.note_reference is None


def test_creation_refreshes_a_cached_subject_before_freezing_its_name(pg):
    ids, subject = accounts(pg)
    with Session(pg) as db:
        cached = db.get(Subject, subject)
        assert cached.name == 'Synthetic explicit subject'
        with Session(pg) as editor:
            editor.get(Subject, subject).name = 'Synthetic latest committed name'
            editor.commit()
        state = service.create_internal(db, db.get(User, ids[0]), setup_request(ids, subject))
    assert state['subject']['name'] == 'Synthetic latest committed name'
    assert all(card['academic']['subject_name'] == state['subject']['name']
               for deck in private(pg, ids[0], state['id']) for card in deck['cards'])
