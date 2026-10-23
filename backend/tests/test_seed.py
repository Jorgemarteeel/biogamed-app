import pytest
from sqlalchemy import func, select

import seed
from app.models import Question, Topic
from app.schemas.game import UserAnswer
from app.schemas.question import QuestionCreate
from app.services.game import start_game_session, submit_game_session


def test_import_repairs_legacy_rows_and_is_repeatable(db, test_user):
    trivial_dir = seed.find_trivial_questions_dir()
    source = sorted(trivial_dir.rglob("*.txt"))[0]
    item = seed.parse_trivial_file(source)[0]
    trivial_topic = seed.get_or_create_topic(db, source.parent.name)
    word_topic = seed.get_or_create_topic(db, "Inmunología")
    word = seed.extract_html_questions(seed.RAW_DATA_DIR / "Inmuno-Quiz.html")[0]
    letter, text = seed.parse_pasapalabra_question(word["question"])
    old_trivial = Question(topic_id=trivial_topic.id, text=item["legacy_text"],
                           correct_answer=item["answer"])
    old_word = Question(topic_id=word_topic.id, text=text,
                        correct_answer=word["answer"], game_letter=letter)
    db.add_all([old_trivial, old_word])
    db.commit()
    old_ids = (old_trivial.id, old_word.id)

    # Match production's autoflush=False, including repeated source questions.
    db.autoflush = False
    inserted = seed.seed_pasapalabra(db) + seed.seed_trivial(db)
    db.commit()
    count = db.scalar(select(func.count()).select_from(Question))
    assert count == inserted + 2
    assert (old_trivial.id, old_word.id) == old_ids
    assert old_trivial.options == item["options"]
    assert old_trivial.text == item["question"]
    assert old_word.question_type == "PASAPALABRA"
    assert old_word.letter == letter
    assert old_word.exact_word == word["answer"]
    assert old_word.text == word["question"]
    assert seed.seed_pasapalabra(db) + seed.seed_trivial(db) == 0
    db.commit()
    assert db.scalar(select(func.count()).select_from(Question)) == count

    for question in db.scalars(select(Question)):
        if question.question_type == "TRIVIAL":
            assert len(question.options) == 4
            assert question.options[question.correct_option_index] == question.correct_answer
        else:
            assert question.letter and question.exact_word
            assert question.text.startswith(("Empieza", "Contiene"))

    # Every imported topic/mode must actually start and score a game.
    pairs = db.execute(select(Question.topic_id, Question.question_type).distinct()).all()
    for topic_id, mode in pairs:
        game = start_game_session(db, test_user, topic_id, mode)
        answers = []
        for public in game.questions:
            stored = db.get(Question, public.id)
            answers.append(UserAnswer(
                question_id=stored.id,
                selected_index=stored.correct_option_index if mode == "TRIVIAL" else None,
                text_answer=stored.exact_word if mode == "PASAPALABRA" else None,
            ))
        result = submit_game_session(db, test_user, game.session_id, answers)
        assert result.score == result.total_questions


def test_contains_letter_question_is_supported():
    question = QuestionCreate(
        topic_id=1, text="Contiene la letra A: Inmunoglobulina de las mucosas.",
        question_type="PASAPALABRA", letter="A", exact_word="IgA",
    )
    assert question.exact_word == "IgA"


def test_seed_rolls_back_on_failure(db, monkeypatch):
    # Keep the fixture session open so its rolled-back contents can be checked.
    monkeypatch.setattr(seed, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    def fail(session):
        raise ValueError("invalid source")
    monkeypatch.setattr(seed, "seed_trivial", fail)
    with pytest.raises(ValueError, match="invalid source"):
        seed.seed_database()
    assert db.scalar(select(func.count()).select_from(Question)) == 0
    assert db.scalar(select(func.count()).select_from(Topic)) == 0
