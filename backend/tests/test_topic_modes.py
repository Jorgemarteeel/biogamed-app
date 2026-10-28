from app.models import Question, Topic


def test_topics_filter_by_playable_mode_before_pagination(client, db):
    empty, trivial, word, both, incomplete = [Topic(name=name) for name in
        ["Empty", "Trivial", "Words", "Both", "Incomplete"]]
    db.add_all([empty, trivial, word, both, incomplete])
    db.flush()
    for topic in [trivial, both]:
        for _ in range(2):
            db.add(Question(topic_id=topic.id, text="Choose", correct_answer="B",
                            options=["A", "B", "C", "D"], correct_option_index=1))
    for topic in [word, both]:
        db.add(Question(topic_id=topic.id, text="Starts with A", correct_answer="Aorta",
                        question_type="PASAPALABRA", letter="A", exact_word="Aorta"))
    db.add_all([
        Question(topic_id=incomplete.id, text="Legacy", correct_answer="A"),
        Question(topic_id=incomplete.id, text="Legacy word", correct_answer="Aorta",
                 question_type="PASAPALABRA", game_letter="A"),
    ])
    db.commit()
    def ids(query):
        response = client.get("/topics/" + query)
        assert response.status_code == 200
        return [item["id"] for item in response.json()]
    assert ids("") == [empty.id, trivial.id, word.id, both.id, incomplete.id]
    assert ids("?mode=TRIVIAL") == [trivial.id, both.id]
    assert ids("?mode=PASAPALABRA") == [word.id, both.id]
    assert ids("?mode=TRIVIAL&skip=1&limit=1") == [both.id]
    assert client.get("/topics/?mode=UNKNOWN").status_code == 422


def test_no_playable_topics_returns_empty_list(client, topic):
    assert client.get("/topics/?mode=TRIVIAL").json() == []
    assert client.get("/topics/?mode=PASAPALABRA").json() == []
