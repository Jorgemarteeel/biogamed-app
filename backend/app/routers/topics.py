from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Topic, User, UserRole
from app.schemas.topic import TopicCreate, TopicResponse
from app.services import topic as topic_service


router = APIRouter(prefix="/topics", tags=["Topics"])


@router.get("/", response_model=list[TopicResponse])
def list_topics(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[Topic]:
    return topic_service.get_topics(db=db, skip=skip, limit=limit)


@router.post(
    "/",
    response_model=TopicResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_topic(
    topic: TopicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Topic:
    if current_user.role not in {UserRole.ADMIN, UserRole.TEACHER}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para crear temáticas.",
        )

    return topic_service.create_topic(db=db, topic=topic)
