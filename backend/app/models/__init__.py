"""Register all models and expose the public model imports."""

from app.models.base import Base
from app.models.user import User, UserRole
from app.models.topic import Topic
from app.models.question import Question
from app.models.game_session import GameSession
from app.models.legacy import AnswerLog, AnswerStatus, GameMode, LegacyGameSession

__all__ = [
    "Base", "User", "UserRole", "Topic", "Question", "GameSession",
    "AnswerLog", "AnswerStatus", "GameMode", "LegacyGameSession",
]
