from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import AnswerLog, GameSession, Question, Topic, User
from app.schemas.game import (
    AnswerCorrection, GameResultResponse, GameSessionStartResponse,
    QuestionForGame, UserAnswer,
)


def start_game_session(
    db: Session, current_user: User, topic_id: int, game_mode: str = "TRIVIAL"
) -> GameSessionStartResponse:
    if game_mode not in {"TRIVIAL", "PASAPALABRA"}:
        raise HTTPException(422, "El modo debe ser TRIVIAL o PASAPALABRA.")
    if db.get(Topic, topic_id) is None:
        raise HTTPException(404, "La temática no existe.")
    statement = select(Question).where(
        Question.topic_id == topic_id, Question.question_type == game_mode,
    )
    if game_mode == "TRIVIAL":
        statement = statement.where(
            Question.options.is_not(None),
            Question.correct_option_index.is_not(None),
        )
    else:
        statement = statement.where(
            Question.letter.is_not(None), Question.exact_word.is_not(None),
        )
    questions = list(db.scalars(statement.order_by(func.random()).limit(10)))
    if not questions:
        raise HTTPException(409, "La temática no tiene preguntas disponibles para este modo.")
    public_questions = [QuestionForGame.model_validate(q) for q in questions]
    session = GameSession(
        user_id=current_user.id, topic_id=topic_id, game_mode=game_mode,
        question_ids=[q.id for q in questions], is_completed=False, score=0,
    )
    try:
        db.add(session)
        db.flush()
        result = GameSessionStartResponse(
            session_id=session.id, topic_id=topic_id, questions=public_questions
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


def submit_game_session(
    db: Session, current_user: User, session_id: int, answers: list[UserAnswer]
) -> GameResultResponse:
    try:
        session = db.scalar(
            select(GameSession).where(GameSession.id == session_id).with_for_update()
        )
        if session is None:
            raise HTTPException(404, "La sesión no existe.")
        if session.user_id != current_user.id:
            raise HTTPException(403, "La sesión pertenece a otro usuario.")
        if session.is_completed:
            raise HTTPException(409, "La sesión ya está completada.")
        if session.game_mode not in {"TRIVIAL", "PASAPALABRA"}:
            raise HTTPException(409, "El modo de la sesión no es válido.")
        submitted_ids = [answer.question_id for answer in answers]
        if (len(set(submitted_ids)) != len(submitted_ids)
                or set(submitted_ids) != set(session.question_ids)):
            raise HTTPException(422, "Envía una respuesta por cada pregunta de la sesión, sin duplicados.")
        questions = {q.id: q for q in db.scalars(
            select(Question).where(Question.id.in_(session.question_ids))
        )}
        corrections = []
        logs = []
        for answer in answers:
            question = questions.get(answer.question_id)
            if (question is None or question.topic_id != session.topic_id
                    or question.question_type != session.game_mode):
                raise HTTPException(409, "Una pregunta de la sesión ya no está disponible.")
            if session.game_mode == "TRIVIAL":
                if (not question.options or question.correct_option_index is None
                        or not 0 <= question.correct_option_index < len(question.options)):
                    raise HTTPException(409, "Una pregunta de la sesión ya no está disponible.")
                if (answer.selected_index is None
                        or not 0 <= answer.selected_index < len(question.options)):
                    raise HTTPException(422, "TRIVIAL requiere un selected_index válido.")
                correction = AnswerCorrection(
                    question_id=question.id, selected_index=answer.selected_index,
                    correct_option_index=question.correct_option_index,
                    is_correct=answer.selected_index == question.correct_option_index,
                )
            else:
                if not question.exact_word or not question.exact_word.strip():
                    raise HTTPException(409, "Una pregunta de la sesión ya no está disponible.")
                if answer.text_answer is None:
                    raise HTTPException(422, "PASAPALABRA requiere text_answer.")
                correction = AnswerCorrection(
                    question_id=question.id, text_answer=answer.text_answer,
                    exact_word=question.exact_word,
                    is_correct=(answer.text_answer.strip().lower()
                                == question.exact_word.strip().lower()),
                )
            corrections.append(correction)
            logs.append(AnswerLog(
                game_session_id=session.id, question_id=question.id,
                question_text=question.text, question_type=session.game_mode,
                options=list(question.options) if session.game_mode == "TRIVIAL" else None,
                letter=question.letter if session.game_mode == "PASAPALABRA" else None,
                selected_index=correction.selected_index, text_answer=correction.text_answer,
                correct_option_index=correction.correct_option_index,
                exact_word=correction.exact_word, is_correct=correction.is_correct,
                response_time_ms=answer.response_time_ms,
            ))
        score = sum(c.is_correct for c in corrections)
        # The conditional update also prevents double submissions without row locks.
        updated = db.execute(update(GameSession).where(
            GameSession.id == session_id, GameSession.is_completed.is_(False),
        ).values(score=score, is_completed=True))
        if updated.rowcount != 1:
            raise HTTPException(409, "La sesión ya está completada.")
        db.add_all(logs)
        result = GameResultResponse(
            score=score, total_questions=len(session.question_ids), corrections=corrections
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


def get_game_history(db: Session, current_user: User, skip: int, limit: int):
    return list(db.scalars(select(GameSession).where(
        GameSession.user_id == current_user.id,
    ).order_by(GameSession.created_at.desc(), GameSession.id.desc()).offset(skip).limit(limit)))


def get_game_history_detail(db: Session, current_user: User, session_id: int):
    session = db.scalar(select(GameSession).where(
        GameSession.id == session_id, GameSession.user_id == current_user.id,
    ))
    if session is None:
        raise HTTPException(404, "La sesión no existe.")
    return session
