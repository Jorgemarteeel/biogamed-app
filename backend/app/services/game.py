from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import GameSession, Question, Topic, User
from app.schemas.game import (
    AnswerCorrection, GameResultResponse, GameSessionStartResponse,
    QuestionForGame, UserAnswer,
)


def start_game_session(
    db: Session, current_user: User, topic_id: int
) -> GameSessionStartResponse:
    if db.get(Topic, topic_id) is None:
        raise HTTPException(404, "La temática no existe.")
    questions = list(db.scalars(
        select(Question).where(
            Question.topic_id == topic_id,
            Question.options.is_not(None),
            Question.correct_option_index.is_not(None),
        ).order_by(func.random()).limit(10)
    ))
    if not questions:
        raise HTTPException(409, "La temática no tiene preguntas de opción múltiple.")
    public_questions = [QuestionForGame.model_validate(q) for q in questions]
    session = GameSession(
        user_id=current_user.id, topic_id=topic_id,
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
        submitted_ids = [answer.question_id for answer in answers]
        if (len(set(submitted_ids)) != len(submitted_ids)
                or set(submitted_ids) != set(session.question_ids)):
            raise HTTPException(422, "Envía una respuesta por cada pregunta de la sesión, sin duplicados.")
        questions = {q.id: q for q in db.scalars(
            select(Question).where(Question.id.in_(session.question_ids))
        )}
        corrections = []
        for answer in answers:
            question = questions.get(answer.question_id)
            if (question is None or question.topic_id != session.topic_id
                    or not question.options or question.correct_option_index is None
                    or not 0 <= question.correct_option_index < len(question.options)):
                raise HTTPException(409, "Una pregunta de la sesión ya no está disponible.")
            if not 0 <= answer.selected_index < len(question.options):
                raise HTTPException(422, "El índice seleccionado no corresponde a una opción.")
            corrections.append(AnswerCorrection(
                question_id=question.id, selected_index=answer.selected_index,
                correct_option_index=question.correct_option_index,
                is_correct=answer.selected_index == question.correct_option_index,
            ))
        score = sum(c.is_correct for c in corrections)
        # The conditional update also prevents double submissions without row locks.
        updated = db.execute(update(GameSession).where(
            GameSession.id == session_id, GameSession.is_completed.is_(False),
        ).values(score=score, is_completed=True))
        if updated.rowcount != 1:
            raise HTTPException(409, "La sesión ya está completada.")
        result = GameResultResponse(
            score=score, total_questions=len(session.question_ids), corrections=corrections
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result
