import json
import re
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Question, Topic


BASE_DIR = Path(__file__).resolve().parent
RAW_DATA_DIR = BASE_DIR / "raw_data"


def _extract_javascript_array(source: str, variable_name: str) -> str:
    """Return the complete contents of a JavaScript array assignment."""
    assignment = re.search(
        rf"\b(?:const|let|var)\s+{re.escape(variable_name)}\s*=\s*\[",
        source,
    )
    if assignment is None:
        raise ValueError(f"No se encontró el array {variable_name}")

    start = assignment.end() - 1
    depth = 0
    quote = None
    escaped = False

    for index in range(start, len(source)):
        character = source[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue

        if character in {'"', "'", "`"}:
            quote = character
        elif character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
            if depth == 0:
                return source[start + 1 : index]

    raise ValueError(f"El array {variable_name} no está cerrado")


def _decode_javascript_string(value: str) -> str:
    """Decode a double-quoted JavaScript string used by the source files."""
    return json.loads(f'"{value}"')


def extract_html_questions(path: Path) -> list[dict[str, str]]:
    """Extract every {q: ..., a: ...} entry from an HTML QUESTIONS array."""
    source = path.read_text(encoding="utf-8-sig")
    array = _extract_javascript_array(source, "QUESTIONS")
    object_pattern = re.compile(
        r"\{\s*q\s*:\s*\"(?P<question>(?:\\.|[^\"\\])*)\"\s*,\s*"
        r"a\s*:\s*\"(?P<answer>(?:\\.|[^\"\\])*)\"\s*\}",
        re.DOTALL,
    )
    questions = [
        {
            "question": _decode_javascript_string(match.group("question")).strip(),
            "answer": _decode_javascript_string(match.group("answer")).strip(),
        }
        for match in object_pattern.finditer(array)
    ]
    if not questions:
        raise ValueError(f"No se extrajeron preguntas de {path}")
    return questions


def parse_pasapalabra_question(value: str) -> tuple[str, str]:
    """Extract the game letter and remove the Pasapalabra prefix."""
    match = re.match(
        r"^\s*(?:Empieza\s+por|Contiene)\s+la\s+letra\s+([A-ZÁÉÍÓÚÜÑ])\s*:\s*(.+)$",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        raise ValueError(f"Formato de pregunta Pasapalabra no reconocido: {value!r}")
    return match.group(1).upper(), match.group(2).strip()


def find_trivial_questions_dir() -> Path:
    """Find raw_data/Preguntas, also supporting the supplied nested layout."""
    direct_path = RAW_DATA_DIR / "Preguntas"
    if direct_path.is_dir():
        return direct_path

    candidates = sorted(path for path in RAW_DATA_DIR.rglob("Preguntas") if path.is_dir())
    if len(candidates) != 1:
        raise FileNotFoundError(
            "No se pudo identificar de forma unívoca la carpeta raw_data/Preguntas"
        )
    return candidates[0]


def parse_trivial_file(path: Path) -> list[dict[str, str]]:
    """Parse question blocks and their option marked with '(correcta)'."""
    content = path.read_text(encoding="utf-8-sig").strip()
    blocks = re.split(r"\r?\n\s*\r?\n", content)
    parsed = []

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        correct_lines = [line for line in lines if re.search(r"\(correcta\)\s*$", line, re.I)]
        if len(correct_lines) != 1:
            raise ValueError(
                f"Se esperaba una respuesta correcta por bloque en {path}: {block!r}"
            )

        answer_match = re.match(
            r"^[a-z]\)\s*(.*?)\s*\(correcta\)\s*$",
            correct_lines[0],
            flags=re.IGNORECASE,
        )
        if answer_match is None:
            raise ValueError(f"Respuesta correcta no reconocida en {path}: {correct_lines[0]!r}")

        # Preserve the alternatives in the question, but do not reveal which is correct.
        clean_text = re.sub(r"\s*\(correcta\)\s*$", "", block, flags=re.I | re.M).strip()
        parsed.append({"question": clean_text, "answer": answer_match.group(1).strip()})

    return parsed


def get_or_create_topic(session, name: str) -> Topic:
    topic = session.scalar(select(Topic).where(Topic.name == name))
    if topic is None:
        topic = Topic(name=name)
        session.add(topic)
        session.flush()
    return topic


def add_question_if_missing(
    session, topic: Topic, text: str, answer: str, game_letter: str | None
) -> bool:
    existing = session.scalar(
        select(Question).where(
            Question.topic_id == topic.id,
            Question.text == text,
            Question.game_letter == game_letter,
        )
    )
    if existing is not None:
        existing.correct_answer = answer
        return False

    session.add(
        Question(
            topic_id=topic.id,
            game_letter=game_letter,
            text=text,
            correct_answer=answer,
        )
    )
    return True


def seed_pasapalabra(session) -> int:
    inserted = 0
    sources = (
        ("Fisiología", RAW_DATA_DIR / "Fisio-Quiz-III.html"),
        ("Inmunología", RAW_DATA_DIR / "Inmuno-Quiz.html"),
    )
    for topic_name, path in sources:
        topic = get_or_create_topic(session, topic_name)
        for item in extract_html_questions(path):
            letter, clean_text = parse_pasapalabra_question(item["question"])
            inserted += add_question_if_missing(
                session, topic, clean_text, item["answer"], letter
            )
    return inserted


def seed_trivial(session) -> int:
    inserted = 0
    questions_dir = find_trivial_questions_dir()
    for topic_dir in sorted(path for path in questions_dir.iterdir() if path.is_dir()):
        topic = get_or_create_topic(session, topic_dir.name)
        for text_file in sorted(topic_dir.glob("*.txt")):
            for item in parse_trivial_file(text_file):
                inserted += add_question_if_missing(
                    session, topic, item["question"], item["answer"], None
                )
    return inserted


def seed_database() -> None:
    session = SessionLocal()
    try:
        inserted = seed_pasapalabra(session) + seed_trivial(session)
        session.commit()
        print(f"Base de datos poblada con éxito: {inserted} preguntas nuevas.")
    except Exception as error:
        session.rollback()
        print(f"Error al poblar la base de datos: {error}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
