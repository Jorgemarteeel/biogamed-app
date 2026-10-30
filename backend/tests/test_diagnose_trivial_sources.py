from tools.diagnose_trivial_sources import diagnose


def source(category="Macrófago", level=1, **changes):
    item = {"file": f"{category}{level}.txt", "position": 1,
            "category": category, "difficulty": level,
            "question": "¿Qué célula?", "legacy_text": "¿Qué célula?\na) A\nb) B\nc) C\nd) D",
            "options": ["A", "B", "C", "D"], "answer": "B",
            "correct_option_index": 1}
    return {**item, **changes}


def question(id=10, **changes):
    item = {"id": id, "topic_id": 5, "question_type": "TRIVIAL",
            "text": "¿Qué célula?", "options": ["A", "B", "C", "D"],
            "correct_option_index": 1, "correct_answer": "B",
            "category_id": None, "difficulty": None}
    return {**item, **changes}


TOPICS = [{"id": 5, "name": "Macrófago"}]


def test_unique_match_and_legacy_format():
    normal = diagnose([source(question="¿Qué  célula?\n")], TOPICS, [question()])
    assert [(p["question_id"], p["topic_id"]) for p in normal["proposed"]] == [(10, 5)]
    legacy = diagnose([source()], TOPICS, [question(text=source()["legacy_text"],
                                                   options=None, correct_option_index=None)])
    assert legacy["proposed"][0]["question_id"] == 10


def test_duplicate_database_rows_require_review():
    result = diagnose([source()], TOPICS, [question(), question(id=11)])
    assert not result["proposed"]
    assert result["incidents"][0]["type"] == "multiples_candidatos"
    assert result["incidents"][0]["candidate_ids"] == [10, 11]


def test_changed_content_and_existing_assignment_require_review():
    changed = diagnose([source()], TOPICS, [question(options=["A", "C", "B", "D"])])
    assert changed["incidents"][0]["type"] == "contenido_discrepante"
    assert changed["incidents"][0]["candidate_ids"] == [10]
    changed_text = diagnose([source()], TOPICS, [question(text="Otro enunciado")])
    assert changed_text["incidents"][0]["type"] == "contenido_discrepante"
    assert changed_text["incidents"][0]["candidate_ids"] == [10]
    assigned = diagnose([source()], TOPICS, [question(difficulty=4, category_id=7)],
                        [{"id": 7, "name": "Otra"}])
    assert assigned["incidents"][0]["type"] == "asignacion_existente"
    assert set(assigned["incidents"][0]["conflicts"]) == {"difficulty", "category_id"}
    compatible = diagnose([source()], TOPICS,
                          [question(difficulty=1, category_id=8)],
                          [{"id": 8, "name": "Macrófago", "block_id": None}])
    assert compatible["proposed"][0]["question_id"] == 10


def test_conflicting_source_levels_require_review():
    result = diagnose([source(level=1), source(level=2)], TOPICS, [question()])
    assert not result["proposed"]
    assert [item["type"] for item in result["incidents"]] == [
        "origen_contradictorio", "origen_contradictorio"]
