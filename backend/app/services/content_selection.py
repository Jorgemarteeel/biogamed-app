"""Resolve academic identities; legacy topics remain an independent selector."""
from fastapi import HTTPException
from app.models import Topic
from app.services.subject import get_category

def selection_dump(request, **kwargs):
    value = request.model_dump(**kwargs)
    for key in ("subject_id", "block_id"):
        if value.get(key) is None:
            value.pop(key, None)
    return value

def resolve(db, topic_id, category_id=None, subject_id=None, block_id=None):
    academic = subject_id is not None or block_id is not None
    if academic:
        if topic_id is not None or None in (subject_id, block_id, category_id):
            raise HTTPException(422, "Selección académica contradictoria o incompleta")
        category = get_category(db, subject_id, block_id, category_id)
        return {"subject_id": subject_id, "subject_name": category.block.subject.name,
                "block_id": block_id, "block_name": category.block.name,
                "category_id": category.id, "category_name": category.name}
    if topic_id is None:
        raise HTTPException(422, "Falta la temática o jerarquía académica")
    if db.get(Topic, topic_id) is None:
        raise HTTPException(404, "La temática no existe.")
    return None
