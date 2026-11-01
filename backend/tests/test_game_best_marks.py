from datetime import datetime, timedelta, timezone
from copy import deepcopy

from app.models import AnswerLog, Category, GameSession, Question, Topic, User


def _session(db, user, topic, questions, category, level=2, score=0,
             mode="TRIVIAL", day=0, context=True, complete=True):
    ids = [question.id for question in questions]
    snapshot = {"selection": {"category_id": category.id, "category_name": category.name,
                              "difficulty": level, "difficulty_unknown": False},
                "questions": [{"question_id": question.id, "category_id": category.id,
                               "category_name": category.name, "difficulty": level}
                              for question in questions]} if context else None
    game = GameSession(user_id=user.id, topic_id=topic.id, game_mode=mode,
                       question_ids=ids, content_context=snapshot, score=score,
                       is_completed=complete,
                       created_at=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=day))
    db.add(game)
    db.flush()
    for index, question in enumerate(questions):
        correct = index < score
        db.add(AnswerLog(game_session_id=game.id, question_id=question.id,
                         question_text=question.text, question_type=mode,
                         options=["A", "B"] if mode == "TRIVIAL" else None,
                         selected_index=(0 if correct else 1) if mode == "TRIVIAL" else None,
                         correct_option_index=0 if mode == "TRIVIAL" else None,
                         text_answer=("A" if correct else "B") if mode == "PASAPALABRA" else None,
                         exact_word="A" if mode == "PASAPALABRA" else None,
                         accepted_answers=[] if mode == "PASAPALABRA" else None,
                         is_correct=correct))
    db.flush()
    return game


def test_best_marks_grouping_ties_zero_and_history_over_page(client, db, topic, test_user, auth_headers):
    other_topic = Topic(name="Other topic")
    first = Category(name="Historical category")
    second = Category(name="Second category")
    db.add_all([other_topic, first, second])
    db.flush()
    questions = [Question(text=f"Question {i}", topic_id=topic.id, question_type="TRIVIAL",
                          options=["A", "B"], correct_option_index=0, correct_answer="A")
                 for i in range(2)]
    db.add_all(questions)
    db.flush()
    early = _session(db, test_user, topic, questions, first, score=1, day=1)
    _session(db, test_user, topic, questions, first, score=1, day=1)
    _session(db, test_user, topic, questions, first, score=1, day=2)
    _session(db, test_user, topic, questions, first, score=0, day=3)
    for index in range(22):
        _session(db, test_user, topic, questions, first, score=0, day=10 + index)
    _session(db, test_user, topic, questions, first, level=3, score=0)
    current_name = _session(db, test_user, topic, questions, second, score=0)
    current_context = deepcopy(current_name.content_context)
    current_context["selection"]["category_name"] = None
    for item in current_context["questions"]:
        item["category_name"] = None
    current_name.content_context = current_context
    _session(db, test_user, other_topic, questions, first, score=0)
    _session(db, test_user, topic, questions[:1], first, score=0)
    _session(db, test_user, topic, questions, first, score=0, mode="PASAPALABRA")
    foreign = User(name="Foreign", email="marks-foreign@example.com", hashed_password="unused")
    db.add(foreign)
    db.flush()
    _session(db, foreign, topic, questions, first, score=2)
    db.commit()

    data = client.get("/game/progress", headers=auth_headers).json()
    assert data["started"] == data["completed"] == 31
    assert data["unfinished"] == 0
    assert len(data["best_marks"]) == 6
    mark = next(item for item in data["best_marks"] if item["game_mode"] == "TRIVIAL"
                and item["topic_id"] == topic.id and item["category_id"] == first.id
                and item["difficulty"] == 2 and item["total_questions"] == 2)
    assert (mark["best_score"], mark["session_id"], mark["valid_results"],
            mark["tied_best_results"]) == (1, early.id, 26, 3)
    assert mark["category_name"] == "Historical category"
    assert mark["category_name_source"] == "historical"
    assert mark["topic_name"] == topic.name
    assert all(item["best_score"] == 0 for item in data["best_marks"] if item is not mark)
    fallback = next(item for item in data["best_marks"] if item["category_id"] == second.id)
    assert (fallback["category_name"], fallback["category_name_source"]) == (second.name, "current")
    assert data["started"] == data["completed"] + data["unfinished"]


def test_best_marks_reject_invalid_snapshots_and_logs(client, db, topic, test_user, auth_headers):
    category = Category(name="Original")
    db.add(category)
    db.flush()
    questions = [Question(text=f"Q {i}", topic_id=topic.id, question_type="TRIVIAL",
                          options=["A", "B"], correct_option_index=0, correct_answer="A")
                 for i in range(2)]
    db.add_all(questions)
    db.flush()
    good = _session(db, test_user, topic, questions, category, score=0)
    _session(db, test_user, topic, questions, category, score=1, complete=False)
    _session(db, test_user, topic, questions, category, score=1, context=False)
    duplicate = _session(db, test_user, topic, questions, category, score=1)
    duplicate.question_ids = [questions[0].id, questions[0].id]
    mismatch = _session(db, test_user, topic, questions, category, score=1)
    mismatch_context = deepcopy(mismatch.content_context)
    mismatch_context["questions"][1]["question_id"] = 999
    mismatch.content_context = mismatch_context
    mixed = _session(db, test_user, topic, questions, category, score=1)
    mixed_context = deepcopy(mixed.content_context)
    mixed_context["questions"][1]["difficulty"] = 3
    mixed.content_context = mixed_context
    unknown = _session(db, test_user, topic, questions, category, score=1)
    unknown_context = deepcopy(unknown.content_context)
    unknown_context["questions"][1]["category_id"] = None
    unknown.content_context = unknown_context
    bad_score = _session(db, test_user, topic, questions, category, score=1)
    bad_score.score = 2
    missing_log = _session(db, test_user, topic, questions, category, score=1)
    db.delete(missing_log.answer_logs[0])
    bad_correction = _session(db, test_user, topic, questions, category, score=1)
    bad_correction.answer_logs[0].is_correct = False
    db.commit()

    # Current bank edits cannot rewrite the saved classification or mark.
    category.name = "Renamed category"
    for question in questions:
        question.category_id = None
        question.difficulty = 4
    db.commit()
    data = client.get("/game/progress", headers=auth_headers).json()
    assert data["started"] == 10
    assert data["completed"] == 9
    assert data["unfinished"] == 1
    assert len(data["best_marks"]) == 1
    mark = data["best_marks"][0]
    assert (mark["session_id"], mark["best_score"], mark["valid_results"],
            mark["tied_best_results"]) == (good.id, 0, 1, 1)
    assert mark["category_name"] == "Original"
    assert mark["category_name_source"] == "historical"
