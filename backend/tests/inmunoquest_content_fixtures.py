"""Synthetic twenty-deck content, unrelated to the real teaching documents."""
from app.models import Question
from app.domain.inmunoquest_rules import Bank


def seed_open_questions(db, subject_id, *, counts=None):
    questions = []
    counts = counts or {}
    for bank in Bank:
        for level in range(1, 5):
            for index in range(counts.get((bank.value, level), 1)):
                q = Question(question_type='INMUNOQUEST', subject_id=subject_id,
                             text=f'Synthetic open {bank.value}/{level}/{index}',
                             reference_answer=f'Private synthetic reference {bank.value}/{level}/{index}',
                             bank=bank.value, difficulty=level, note_reference='T1' if index == 0 else None)
                db.add(q)
                questions.append(q)
    db.flush()
    return questions
