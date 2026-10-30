from collections import Counter

import pytest
from sqlalchemy import select

from app.models import Category, Question, Topic
from tools.assign_trivial_metadata import (
    AssignmentConflict, apply_assignments, plan_assignments,
)


def bank(db):
    sources = []
    questions = []
    for name in ("Linfocito", "Macrófago", "Erlenmeyer", "Jeringuilla"):
        topic = Topic(name=name)
        db.add(topic)
        db.flush()
        for level in range(1, 5):
            for position in range(1, 11):
                text = f"Pregunta {name} {level} {position}"
                questions.append(Question(topic_id=topic.id, text=text,
                                          question_type="TRIVIAL", options=["A", "B", "C", "D"],
                                          correct_option_index=1, correct_answer="B"))
                sources.append({"file": f"{name}{level}.txt", "position": position,
                                "category": name, "difficulty": level,
                                "question": text,
                                "legacy_text": f"{text}\na) A\nb) B\nc) C\nd) D",
                                "options": ["A", "B", "C", "D"],
                                "correct_option_index": 1, "answer": "B"})
    db.add_all(questions)
    other_topic = Topic(name="Other")
    db.add(other_topic)
    db.flush()
    outside = [Question(topic_id=other_topic.id, text="No está en TXT",
                        correct_answer="A", question_type="TRIVIAL"),
               Question(topic_id=other_topic.id, text="Palabra", correct_answer="B",
                        question_type="PASAPALABRA")]
    db.add_all(outside)
    db.commit()
    return sources, questions, outside


def test_dry_run_assignment_and_repeat_preserve_other_content(db):
    sources, questions, outside = bank(db)
    before = [(q.id, q.topic_id, q.text, q.options, q.correct_answer) for q in questions]
    proposed, categories = plan_assignments(db, sources)
    assert len(proposed) == 160 and categories == {}
    assert not list(db.scalars(select(Category)))
    assert apply_assignments(db, sources) == (4, 160)
    db.commit()
    assert apply_assignments(db, sources) == (0, 0)
    db.commit()
    assert len(list(db.scalars(select(Category)))) == 4
    assert [(q.id, q.topic_id, q.text, q.options, q.correct_answer) for q in questions] == before
    assert all(q.category_id is None and q.difficulty is None for q in outside)
    counts = Counter((q.category.name, q.difficulty) for q in questions)
    assert set(counts.values()) == {10} and len(counts) == 16
    assert all(q.category.block_id is None for q in questions)


def test_conflict_cancels_all_assignments(db):
    sources, questions, _ = bank(db)
    questions[-1].difficulty = 3 if sources[-1]["difficulty"] != 3 else 2
    db.commit()
    with pytest.raises(AssignmentConflict, match="Diagnóstico no apto"):
        apply_assignments(db, sources)
    assert not list(db.scalars(select(Category)))
    assert all(q.category_id is None for q in questions)


def test_ambiguous_category_cancels_all_assignments(db):
    sources, questions, _ = bank(db)
    db.add_all([Category(name="Linfocito"), Category(name="Linfocito")])
    db.commit()
    with pytest.raises(AssignmentConflict, match="Categoría de origen ambigua"):
        apply_assignments(db, sources)
    assert all(q.category_id is None and q.difficulty is None for q in questions)
