"""Assign verified Trivial source category and level in one transaction.

Run from backend/: python -B tools/assign_trivial_metadata.py [--apply]
Default is a read-only simulation. --apply writes only category_id and difficulty.
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import engine
from app.models import Category, Question, Topic
from tools.diagnose_trivial_sources import diagnose, question_data, read_sources


SOURCE_CATEGORIES = {"Linfocito", "Macrófago", "Erlenmeyer", "Jeringuilla"}


class AssignmentConflict(ValueError):
    pass


def plan_assignments(session: Session, sources: list[dict]) -> tuple[list[dict], dict[str, Category]]:
    existing = list(session.scalars(select(Category)))
    by_name = {}
    for name in SOURCE_CATEGORIES:
        candidates = [category for category in existing if category.name == name]
        if len(candidates) > 1 or (candidates and candidates[0].block_id is not None):
            raise AssignmentConflict(f"Categoría de origen ambigua: {name}; "
                                     f"IDs: {[category.id for category in candidates]}")
        if candidates:
            by_name[name] = candidates[0]

    topics = [{"id": t.id, "name": t.name} for t in session.scalars(select(Topic))]
    questions = [question_data(q) for q in session.scalars(select(Question))]
    categories = [{"id": c.id, "name": c.name, "block_id": c.block_id}
                  for c in existing]
    result = diagnose(sources, topics, questions, categories)
    proposed = result["proposed"]
    if (len(sources) != 160 or len(proposed) != 160 or result["incidents"]
            or len({item["question_id"] for item in proposed}) != 160
            or {item["category"] for item in proposed} != SOURCE_CATEGORIES):
        sample = [(item["type"], item["file"], item["position"],
                   item["candidate_ids"]) for item in result["incidents"][:10]]
        raise AssignmentConflict(
            f"Diagnóstico no apto: fuentes={len(sources)}, propuestas={len(proposed)}, "
            f"incidencias={len(result['incidents'])}, muestra={sample}")
    counts = Counter((item["category"], item["difficulty"]) for item in proposed)
    if any(counts[name, level] != 10 for name in SOURCE_CATEGORIES for level in range(1, 5)):
        raise AssignmentConflict(f"Distribución inesperada: {dict(counts)}")
    return proposed, by_name


def apply_assignments(session: Session, sources: list[dict]) -> tuple[int, int]:
    """Caller owns the transaction; validate everything before making changes."""
    proposed, by_name = plan_assignments(session, sources)
    created = 0
    for name in sorted(SOURCE_CATEGORIES):
        if name not in by_name:
            category = Category(name=name, block_id=None)
            session.add(category)
            by_name[name] = category
            created += 1
    session.flush()
    changed = 0
    for item in proposed:
        question = session.get(Question, item["question_id"])
        category_id = by_name[item["category"]].id
        if question.category_id != category_id or question.difficulty != item["difficulty"]:
            question.category_id = category_id
            question.difficulty = item["difficulty"]
            changed += 1
    session.flush()
    return created, changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit the verified assignments")
    args = parser.parse_args()
    sources = read_sources()
    if args.apply:
        # SERIALIZABLE makes concurrent changes fail rather than silently stale the audit.
        with engine.connect().execution_options(isolation_level="SERIALIZABLE") as connection:
            with connection.begin():
                with Session(bind=connection) as session:
                    created, changed = apply_assignments(session, sources)
        print(f"Aplicado: 160 correspondencias; categorías creadas={created}; "
              f"preguntas actualizadas={changed}")
    else:
        with engine.connect() as connection:
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            with Session(bind=connection) as session:
                proposed, by_name = plan_assignments(session, sources)
        print(f"Simulación de solo lectura: {len(proposed)} correspondencias, "
              f"0 incidencias; categorías a crear={len(SOURCE_CATEGORIES) - len(by_name)}")


if __name__ == "__main__":
    main()
