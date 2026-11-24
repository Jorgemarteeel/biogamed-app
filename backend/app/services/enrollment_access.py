from sqlalchemy import update

from app.models import Enrollment


def enable_for_play(db, target: Enrollment):
    """Under the enrollment write lock, replace the enabled year without deleting enrollments."""
    if target.play_enabled:
        return
    db.execute(update(Enrollment).where(
        Enrollment.student_id == target.student_id, Enrollment.subject_id == target.subject_id,
        Enrollment.play_enabled.is_(True),
    ).values(play_enabled=False))
    target.play_enabled = True
