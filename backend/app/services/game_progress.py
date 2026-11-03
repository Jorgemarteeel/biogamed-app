"""Personal marks from saved classifications and answer snapshots."""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnswerLog, Category, GameSession, Topic, User
from app.utils.answers import is_accepted_answer


def _positive_id(value):
    return type(value) is int and value > 0


def _classification(session):
    ids = session.question_ids
    if (not isinstance(ids, list) or not 1 <= len(ids) <= 10
            or not all(_positive_id(value) for value in ids)
            or len(set(ids)) != len(ids)):
        return None
    context = session.content_context
    if (not isinstance(context, dict) or not isinstance(context.get("questions"), list)
            or not isinstance(context.get("selection"), dict)):
        return None
    selection = context["selection"]
    if not {"category_id", "category_name", "difficulty", "difficulty_unknown"} <= selection.keys():
        return None
    if (selection["category_id"] is not None and not _positive_id(selection["category_id"])):
        return None
    if selection["category_name"] is not None and not isinstance(selection["category_name"], str):
        return None
    if (selection["difficulty"] is not None and
            (type(selection["difficulty"]) is not int or selection["difficulty"] not in range(1, 5))):
        return None
    if (type(selection["difficulty_unknown"]) is not bool or
            (selection["difficulty_unknown"] and selection["difficulty"] is not None)):
        return None
    questions = context["questions"]
    if len(questions) != len(ids) or not all(isinstance(item, dict) for item in questions):
        return None
    context_ids = [item.get("question_id") for item in questions]
    if (not all(_positive_id(value) for value in context_ids)
            or len(set(context_ids)) != len(context_ids)
            or set(context_ids) != set(ids)):
        return None
    categories = [item.get("category_id") for item in questions]
    difficulties = [item.get("difficulty") for item in questions]
    if (not all(_positive_id(value) and value == categories[0] for value in categories)
            or not all(type(value) is int and value in range(1, 5)
                       and value == difficulties[0] for value in difficulties)):
        return None
    category_id = categories[0]
    difficulty = difficulties[0]
    if ((selection["category_id"] is not None and selection["category_id"] != category_id)
            or (selection["difficulty"] is not None and selection["difficulty"] != difficulty)
            or selection["difficulty_unknown"]):
        return None
    names = [item.get("category_name") for item in questions]
    if not all(name is None or isinstance(name, str) for name in names):
        return None
    if not all(name == names[0] for name in names):
        return None
    historical_name = names[0]
    return category_id, difficulty, historical_name


def _complete_answers(session, rows):
    if len(rows) != len(session.question_ids):
        return False
    if {row.question_id for row in rows} != set(session.question_ids):
        return False
    for row in rows:
        if row.question_type != session.game_mode or type(row.is_correct) is not bool:
            return False
        if session.game_mode == "TRIVIAL":
            if (type(row.selected_index) is not int or type(row.correct_option_index) is not int
                    or not isinstance(row.options, list) or not row.options
                    or not all(isinstance(value, str) for value in row.options)
                    or not 0 <= row.selected_index < len(row.options)
                    or not 0 <= row.correct_option_index < len(row.options)
                    or row.is_correct != (row.selected_index == row.correct_option_index)):
                return False
        elif session.game_mode == "PASAPALABRA":
            if (row.text_answer is None or not isinstance(row.exact_word, str)
                    or not row.exact_word.strip()
                    or (row.accepted_answers is not None and
                        (not isinstance(row.accepted_answers, list) or
                         not all(isinstance(value, str) for value in row.accepted_answers)))
                    or row.is_correct != is_accepted_answer(
                        row.text_answer, row.exact_word, row.accepted_answers,
                    )):
                return False
        else:
            return False
    return sum(row.is_correct for row in rows) == session.score


def get_personal_best_marks(db: Session, current_user: User):
    # Set queries for sessions, answer fields, and labels. No detail query per game.
    sessions = list(db.scalars(select(GameSession).where(
        GameSession.user_id == current_user.id, GameSession.is_completed.is_(True),
    )))
    if not sessions:
        return []
    logs = db.execute(select(
        AnswerLog.game_session_id, AnswerLog.question_id, AnswerLog.question_type,
        AnswerLog.options, AnswerLog.selected_index, AnswerLog.correct_option_index,
        AnswerLog.text_answer, AnswerLog.exact_word, AnswerLog.accepted_answers,
        AnswerLog.is_correct,
    ).join(GameSession, AnswerLog.game_session_id == GameSession.id).where(
        GameSession.user_id == current_user.id, GameSession.is_completed.is_(True),
    )).all()
    logs_by_session = defaultdict(list)
    for row in logs:
        logs_by_session[row.game_session_id].append(row)

    groups = defaultdict(list)
    for session in sessions:
        classification = _classification(session)
        if (classification is None or type(session.score) is not int
                or not 0 <= session.score <= len(session.question_ids)
                or not _complete_answers(session, logs_by_session[session.id])):
            continue
        category_id, difficulty, historical_name = classification
        key = (session.game_mode, session.topic_id, category_id,
               difficulty, len(session.question_ids))
        groups[key].append((session, historical_name))
    if not groups:
        return []

    topic_ids = {key[1] for key in groups}
    category_ids = {key[2] for key in groups}
    topics = dict(db.execute(select(Topic.id, Topic.name).where(Topic.id.in_(topic_ids))).all())
    categories = dict(db.execute(select(Category.id, Category.name).where(
        Category.id.in_(category_ids))).all())
    marks = []
    for (mode, topic_id, category_id, difficulty, total), candidates in sorted(groups.items()):
        ordered = sorted(candidates, key=lambda item: (item[0].created_at, item[0].id))
        best_score = max(session.score for session, _ in candidates)
        tied = [(session, name) for session, name in candidates if session.score == best_score]
        winner, historical_name = min(tied, key=lambda item: (item[0].created_at, item[0].id))
        category_name = historical_name or categories.get(category_id)
        historical_topic = (winner.content_context or {}).get("topic_name")
        topic_name = historical_topic if historical_topic is not None else topics.get(topic_id)
        marks.append({
            "game_mode": mode, "topic_id": topic_id,
            "topic_name": topic_name,
            "topic_name_source": ("historical" if historical_topic is not None else "current" if topic_name else None),
            "category_id": category_id, "category_name": category_name,
            "category_name_source": ("historical" if historical_name else "current" if category_name else None),
            "difficulty": difficulty, "total_questions": total,
            "best_score": best_score, "session_id": winner.id,
            "started_at": winner.created_at,
            "valid_results": len(candidates), "tied_best_results": len(tied),
            "results": [{"session_id": session.id, "started_at": session.created_at,
                         "score": session.score, "total_questions": total}
                        for session, _ in ordered],
        })
    return marks
