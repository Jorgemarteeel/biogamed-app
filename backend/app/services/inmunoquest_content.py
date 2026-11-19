"""Automatic frozen open content. No HTTP, card drawing or human evaluation.

Private recovery helpers require an already authenticated/locked aggregate from
inmunoquest_persistence. Their values, especially answers, MUST NOT be serialized
to a client. Player state uses its existing explicit allowlist instead.
"""
from collections import defaultdict
from random import SystemRandom

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select, func

from app.domain.inmunoquest_rules import Bank
from app.models import Question, Subject, ContentBlock, Category
from app.models.trivial_content import TrivialContentCopy as Copy
from app.models.inmunoquest_content import InmunoQuestDeck as Deck
from app.schemas.question import QuestionCreate
from app.schemas.inmunoquest_content import StoredOpenQuestion

PREPARATION_VERSION = 'inmunoquest-decks-v1'
SHUFFLE_VERSION = 'systemrandom-fisher-yates-v1'
COPY_VERSION = 2
KEYS = tuple((b.value, level) for b in Bank for level in range(1, 5))
RNG = SystemRandom()


def fail(code):
    raise HTTPException(409, {'code': code})


def _selected_rows(db, subject_id):
    """One SQL statement/one MVCC snapshot, including academic labels.

    No row-by-row lazy relationships and no later source reread. Under PostgreSQL
    READ COMMITTED an edit committed after this statement changes the catalog,
    not the content frozen for this match. Inserts after it belong to later starts.
    """
    return db.execute(
        select(*Question.__table__.columns, Subject.name.label('subject_name'),
               Category.name.label('category_name'), Category.block_id.label('category_block_id'),
               ContentBlock.id.label('resolved_block_id'), ContentBlock.name.label('block_name'),
               ContentBlock.subject_id.label('block_subject_id'))
        .join(Subject, Subject.id == Question.subject_id)
        .outerjoin(Category, Category.id == Question.category_id)
        .outerjoin(ContentBlock, ContentBlock.id == func.coalesce(Question.block_id, Category.block_id))
        .where(Question.subject_id == subject_id, Question.question_type == 'INMUNOQUEST',
               Question.is_active.is_(True), Question.topic_id.is_(None),
               Question.bank.in_([b.value for b in Bank]), Question.difficulty.between(1, 4),
               func.length(func.trim(Question.text)) > 0,
               func.length(func.trim(Question.reference_answer)) > 0)
        .order_by(Question.id)
    ).mappings().all()


def _validated_copy(row, subject_id):
    # Reuse the actual manual/import content validation. Never put its exceptions
    # (which may include an answer) in HTTP errors, diagnostics or receipts.
    try:
        QuestionCreate.model_validate({key: row[key] for key in QuestionCreate.model_fields})
        stored = StoredOpenQuestion(id=row['id'], question_type='INMUNOQUEST', text=row['text'],
                                    reference_answer=row['reference_answer'], note_reference=row['note_reference'])
    except ValidationError:
        return None
    if row['category_id'] is not None:
        if row['category_name'] is None:
            return None
        if row['block_id'] is not None and row['category_block_id'] != row['block_id']:
            return None
    if (row['resolved_block_id'] is not None and row['block_subject_id'] != subject_id
            or (row['block_id'] is not None or row['category_block_id'] is not None) and row['resolved_block_id'] is None):
        return None
    academic = {
        'question_id': row['id'], 'subject_id': subject_id, 'subject_name': row['subject_name'],
        'block_id': row['resolved_block_id'], 'block_name': row['block_name'],
        'category_id': row['category_id'], 'category_name': row['category_name'],
    }
    return stored.model_dump(), academic


def shuffle_in_place(values):
    # Fixed procedural version; recovery uses the stored permutation, not a seed.
    for index in range(len(values) - 1, 0, -1):
        chosen = RNG.randrange(index + 1)
        values[index], values[chosen] = values[chosen], values[index]


def prepare(db, match, now, *, shuffler=None):
    """Part of creation's transaction. No commit, no independent retry/start."""
    groups = defaultdict(list)
    for row in _selected_rows(db, match.subject_id):
        validated = _validated_copy(row, match.subject_id)
        if validated is not None:
            groups[(row['bank'], row['difficulty'])].append((row, validated))
    missing = [{'bank': bank, 'difficulty': level} for bank, level in KEYS if not groups[(bank, level)]]
    if missing:
        raise HTTPException(409, {'code': 'EMPTY_INMUNOQUEST_DECKS', 'minimum_per_deck': 1,
                                  'missing_decks': missing})
    for bank, level in KEYS:
        copies = []
        for row, (stored, academic) in groups[(bank, level)]:
            copy = Copy(match_id=match.id, question_id=row['id'], bank=bank, difficulty=level,
                        snapshot_version=COPY_VERSION, snapshot=stored, classification=academic,
                        binding_snapshot={'kind': 'subject', 'id': match.subject_id, 'name': row['subject_name']},
                        copied_at=now)
            db.add(copy)
            copies.append(copy)
        db.flush()
        original = [copy.id for copy in copies]
        order = list(original)
        (shuffler or shuffle_in_place)(order)
        if (any(type(value) is not int for value in order) or len(order) != len(original)
                or set(order) != set(original)):
            raise ValueError('Invalid server shuffle permutation')
        db.add(Deck(match_id=match.id, bank=bank, difficulty=level, initial_order=order,
                    shuffle_version=SHUFFLE_VERSION, created_at=now))
    match.configuration = {**match.configuration, 'content_preparation_version': PREPARATION_VERSION}
    db.flush()
    validate_preparation(db, match)


def validate_preparation(db, match):
    """Check only saved metadata/order. Never query the original questions."""
    marker = match.configuration.get('content_preparation_version')
    decks = list(db.execute(select(Deck.bank, Deck.difficulty, Deck.shuffle_version, Deck.initial_order)
                            .where(Deck.match_id == match.id)))
    copies = list(db.execute(select(Copy.id, Copy.question_id, Copy.bank, Copy.difficulty, Copy.snapshot_version)
                             .where(Copy.match_id == match.id)))
    if 'content_preparation_version' not in match.configuration:
        if decks or any(copy.snapshot_version == COPY_VERSION for copy in copies):
            fail('INVALID_SAVED_CONTENT')
        return None  # Pre-delivery internal states remain interpretable, not backfilled.
    if marker != PREPARATION_VERSION:
        fail('UNSUPPORTED_CONTENT_VERSION')
    if match.subject_id is None or len(decks) != len(KEYS) or {(d.bank, d.difficulty) for d in decks} != set(KEYS):
        fail('INVALID_SAVED_CONTENT')
    expected = defaultdict(set)
    for copy in copies:
        if copy.snapshot_version != COPY_VERSION:
            fail('UNSUPPORTED_CONTENT_VERSION')
        if (copy.bank, copy.difficulty) not in KEYS:
            fail('INVALID_SAVED_CONTENT')
        expected[(copy.bank, copy.difficulty)].add(copy.id)
    for deck in decks:
        if deck.shuffle_version != SHUFFLE_VERSION:
            fail('UNSUPPORTED_SHUFFLE_VERSION')
        order = deck.initial_order
        if (type(order) is not list or not order or any(type(value) is not int for value in order)
                or len(order) != len(set(order)) or set(order) != expected[(deck.bank, deck.difficulty)]):
            fail('INVALID_SAVED_CONTENT')
    return decks


def recover_private_decks(db, match):
    """Trusted server use ONLY, after locking/auth. Not a player projection."""
    decks = validate_preparation(db, match)
    if decks is None:
        fail('CONTENT_NOT_PREPARED')
    rows = db.execute(select(Copy.id, Copy.question_id, Copy.bank, Copy.difficulty, Copy.snapshot,
                             Copy.classification, Copy.binding_snapshot).where(Copy.match_id == match.id)).all()
    private = {}
    for row in rows:
        invalid = False
        try:
            stored = StoredOpenQuestion.model_validate(row.snapshot)
        except ValidationError:
            invalid = True
        if invalid:
            fail('INVALID_PRIVATE_CONTENT')
        if (not isinstance(row.classification, dict) or not isinstance(row.binding_snapshot, dict)
                or stored.id != row.question_id or row.classification.get('question_id') != row.question_id
                or row.classification.get('subject_id') != match.subject_id
                or row.binding_snapshot.get('kind') != 'subject' or row.binding_snapshot.get('id') != match.subject_id):
            fail('INVALID_PRIVATE_CONTENT')
        private[row.id] = {'copy_id': row.id, 'question': stored, 'bank': row.bank, 'difficulty': row.difficulty,
                           'academic': row.classification, 'binding': row.binding_snapshot}
    return tuple({'bank': deck.bank, 'difficulty': deck.difficulty, 'shuffle_version': deck.shuffle_version,
                  'copy_ids': tuple(deck.initial_order), 'cards': tuple(private[i] for i in deck.initial_order)}
                 for deck in sorted(decks, key=lambda d: KEYS.index((d.bank, d.difficulty))))
