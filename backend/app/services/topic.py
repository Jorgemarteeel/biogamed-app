from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Topic
from app.schemas.topic import TopicCreate
from app.services.game_questions import playable_question_filter


def get_topics(db: Session, skip: int = 0, limit: int = 100, mode: str | None = None) -> list[Topic]:
    statement = select(Topic)
    if mode is not None:
        statement = statement.where(Topic.questions.any(playable_question_filter(mode)))
    statement = statement.order_by(Topic.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def create_topic(db: Session, topic: TopicCreate) -> Topic:
    db_topic = Topic(**topic.model_dump())
    db.add(db_topic)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(db_topic)
    return db_topic
