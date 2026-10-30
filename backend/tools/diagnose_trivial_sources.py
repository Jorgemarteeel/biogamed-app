"""Read-only audit of original Trivial TXT files against existing questions.

Run from backend/: python -B tools/diagnose_trivial_sources.py --output PATH
The output path should be outside the repository. No assignment is performed.
"""

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import engine  # noqa: E402
from app.models import Question, Topic  # noqa: E402
from seed import BASE_DIR, find_trivial_questions_dir, parse_trivial_file  # noqa: E402


def normalize(value: str) -> str:
    """Ignore only formatting whitespace (including CRLF and indentation)."""
    return " ".join(value.split())


def read_sources(directory: Path | None = None) -> list[dict]:
    directory = directory or find_trivial_questions_dir()
    records = []
    for folder in sorted(path for path in directory.iterdir() if path.is_dir()):
        for path in sorted(folder.glob("*.txt")):
            match = re.fullmatch(re.escape(folder.name) + r"([1-4])", path.stem)
            if match is None:
                raise ValueError(f"Nivel no identificable en {path}")
            for position, item in enumerate(parse_trivial_file(path), start=1):
                records.append({"file": path.relative_to(BASE_DIR).as_posix(),
                                "position": position,
                                "category": folder.name, "difficulty": int(match.group(1)),
                                **item})
    return records


def question_data(question: Question) -> dict:
    return {name: getattr(question, name) for name in (
        "id", "topic_id", "question_type", "text", "options",
        "correct_option_index", "correct_answer", "category_id", "difficulty")}


def compare_content(source: dict, question: dict) -> list[str]:
    differences = []
    legacy = normalize(question["text"]) == normalize(source["legacy_text"])
    if not legacy and normalize(question["text"]) != normalize(source["question"]):
        differences.append("enunciado")
    if question["options"] is None and not legacy:
        differences.append("opciones ausentes")
    elif question["options"] is not None and (
        not isinstance(question["options"], list)
        or [normalize(str(option)) for option in question["options"]]
           != [normalize(option) for option in source["options"]]
    ):
        differences.append("opciones u orden")
    if question["correct_option_index"] is not None and (
        question["correct_option_index"] != source["correct_option_index"]
    ):
        differences.append("índice de solución")
    if normalize(question["correct_answer"]) != normalize(source["answer"]):
        differences.append("texto de solución")
    return differences


def diagnose(sources: list[dict], topics: list[dict], questions: list[dict],
             categories: list[dict] | None = None) -> dict:
    categories = categories or []
    category_by_id = {item["id"]: item for item in categories}
    topic_ids_by_name = defaultdict(list)
    for topic in topics:
        topic_ids_by_name[topic["name"]].append(topic["id"])
    source_occurrences = defaultdict(list)
    for index, source in enumerate(sources):
        source_occurrences[normalize(source["question"])].append(index)
    conflicting_sources = set()
    for indices in source_occurrences.values():
        classifications = {(sources[i]["category"], sources[i]["difficulty"])
                           for i in indices}
        if len(classifications) > 1:
            conflicting_sources.update(indices)

    proposed, incidents = [], []
    represented = set()
    for index, source in enumerate(sources):
        topic_ids = topic_ids_by_name[source["category"]]
        record = {key: source[key] for key in ("file", "position", "category", "difficulty")}
        record["topic_ids"] = topic_ids
        same_topic = [q for q in questions if q["topic_id"] in topic_ids
                      and q["question_type"] == "TRIVIAL"]
        text_candidates = [q for q in same_topic if normalize(q["text"]) in
                           {normalize(source["question"]), normalize(source["legacy_text"])}]
        full = [(q, compare_content(source, q)) for q in text_candidates]
        exact = [q for q, differences in full if not differences]
        if not text_candidates:
            # Exact alternatives and solution can identify a changed enunciado
            # as a review candidate without treating it as an assignment.
            full = [(q, ["enunciado"]) for q in same_topic
                    if isinstance(q["options"], list)
                    and [normalize(str(option)) for option in q["options"]]
                        == [normalize(option) for option in source["options"]]
                    and q["correct_option_index"] == source["correct_option_index"]
                    and normalize(q["correct_answer"]) == normalize(source["answer"])]
        for q in exact:
            represented.add(q["id"])
        if index in conflicting_sources:
            peers = source_occurrences[normalize(source["question"])]
            incidents.append({**record, "type": "origen_contradictorio",
                              "candidate_ids": [q["id"] for q in exact],
                              "other_sources": [f"{sources[i]['file']}#{sources[i]['position']}"
                                                for i in peers if i != index]})
        elif not topic_ids:
            incidents.append({**record, "type": "tematica_ausente", "candidate_ids": []})
        elif len(topic_ids) > 1:
            incidents.append({**record, "type": "tematica_ambigua",
                              "candidate_ids": [q["id"] for q in exact]})
        elif len(text_candidates) > 1:
            incidents.append({**record, "type": "multiples_candidatos",
                              "candidate_ids": [q["id"] for q in text_candidates],
                              "differences": {q["id"]: diff for q, diff in full}})
        elif not exact and full:
            incidents.append({**record, "type": "contenido_discrepante",
                              "candidate_ids": [q["id"] for q, _ in full],
                              "differences": {q["id"]: diff for q, diff in full}})
        elif not exact:
            other_topics = [q["id"] for q in questions if q["question_type"] == "TRIVIAL"
                            and normalize(q["text"]) in
                            {normalize(source["question"]), normalize(source["legacy_text"])}]
            incidents.append({**record, "type": "sin_correspondencia",
                              "candidate_ids": other_topics})
        else:
            q = exact[0]
            conflicts = []
            if q["difficulty"] is not None and q["difficulty"] != source["difficulty"]:
                conflicts.append("difficulty")
            if q["category_id"] is not None:
                existing = category_by_id.get(q["category_id"])
                if existing is None or existing["name"] != source["category"]:
                    conflicts.append("category_id")
                elif existing.get("block_id") is not None:
                    conflicts.append("category_id con bloque académico")
            if conflicts:
                incidents.append({**record, "type": "asignacion_existente",
                                  "candidate_ids": [q["id"]], "conflicts": conflicts,
                                  "existing_category_id": q["category_id"],
                                  "existing_difficulty": q["difficulty"]})
            else:
                proposed.append({**record, "question_id": q["id"],
                                 "topic_id": q["topic_id"]})
    unmatched = [q for q in questions if q["id"] not in represented]
    return {"proposed": proposed, "incidents": incidents,
            "unmatched": unmatched, "source_count": len(sources),
            "represented_count": len(represented)}


def render(result: dict) -> str:
    lines = ["# Diagnóstico de correspondencias Trivial", "",
             "Lectura exclusivamente. Categoría = nombre de carpeta de origen; "
             "nivel = sufijo 1–4 del TXT. No equivale a clasificación académica validada.", "",
             f"Fuentes: {result['source_count']}; propuestas: {len(result['proposed'])}; "
             f"incidencias: {len(result['incidents'])}; preguntas representadas: "
             f"{result['represented_count']}.", "", "## Recuentos por categoría y nivel", "",
             "| Categoría de origen | Nivel | Propuestas | Incidencias |",
             "|---|---:|---:|---:|"]
    proposals = Counter((p["category"], p["difficulty"]) for p in result["proposed"])
    incidents = Counter((p["category"], p["difficulty"]) for p in result["incidents"])
    for category, level in sorted(proposals.keys() | incidents.keys()):
        lines.append(f"| {category} | {level} | {proposals[category, level]} | "
                     f"{incidents[category, level]} |")
    lines += ["", "## Correspondencias propuestas", "",
              "| Archivo | Posición | question_id | topic_id | Categoría de origen | Nivel |",
              "|---|---:|---:|---:|---|---:|"]
    for item in result["proposed"]:
        lines.append(f"| {item['file']} | {item['position']} | {item['question_id']} | "
                     f"{item['topic_id']} | {item['category']} | {item['difficulty']} |")
    lines += ["", "## Incidencias y candidatos", "",
              "| Archivo | Posición | Temáticas ID | Tipo | Candidatos question_id | Detalle |",
              "|---|---:|---|---|---|---|"]
    for item in result["incidents"]:
        detail = "; ".join(f"{k}={v}" for k, v in item.items() if k in (
            "differences", "other_sources", "conflicts", "existing_category_id",
            "existing_difficulty"))
        lines.append(f"| {item['file']} | {item['position']} | {item['topic_ids']} | "
                     f"{item['type']} | {item['candidate_ids']} | {detail} |")
    lines += ["", "## Preguntas no representadas en los TXT", "",
              "Pasapalabra se enumera aquí, pero queda fuera de la clasificación.", "",
              "| question_id | topic_id | Modalidad | Enunciado |",
              "|---:|---:|---|---|"]
    for item in result["unmatched"]:
        lines.append(f"| {item['id']} | {item['topic_id']} | {item['question_type']} | "
                     f"{normalize(item['text']).replace('|', '&#124;')} |")
    lines += ["", "## Normalización", "",
              "Solo se colapsan espacios, tabulaciones y saltos de línea. "
              "Se reconoce el enunciado heredado que incluye las cuatro opciones "
              "y no tiene columnas de opciones. Se conserva el orden de opciones "
              "y se compara la solución textual; no se usa semejanza aproximada.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    sources = read_sources()
    with engine.connect() as connection:
        connection.exec_driver_sql("SET TRANSACTION READ ONLY")
        with Session(bind=connection) as session:
            topics = [{"id": t.id, "name": t.name} for t in session.scalars(select(Topic))]
            questions = [question_data(q) for q in session.scalars(select(Question))]
            from app.models import Category
            categories = [{"id": c.id, "name": c.name, "block_id": c.block_id}
                          for c in session.scalars(select(Category))]
            result = diagnose(sources, topics, questions, categories)
    args.output.write_text(render(result), encoding="utf-8")
    print(f"Informe: {args.output}")
    print(f"Fuentes={result['source_count']} propuestas={len(result['proposed'])} "
          f"incidencias={len(result['incidents'])} "
          f"no_representadas={len(result['unmatched'])}")


if __name__ == "__main__":
    main()
