import pytest

from app.models import Question, UserRole


@pytest.fixture
def bank(db, topic):
    questions = [
        Question(topic_id=topic.id, text="Select B", correct_answer="B",
                 options=["A", "B", "C", "D"], correct_option_index=1),
        Question(topic_id=topic.id, text="Starts with A", correct_answer="Aorta",
                 question_type="PASAPALABRA", letter="A", exact_word="Aorta"),
    ]
    db.add_all(questions)
    db.commit()
    return questions


def test_bank_requires_valid_credentials(client, topic, bank):
    for headers in ({}, {"Authorization": "Bearer invalid-token"}):
        response = client.get(f"/questions/topic/{topic.id}", headers=headers)
        assert response.status_code == 401
        assert "Aorta" not in response.text


def test_student_cannot_read_bank(client, topic, bank, auth_headers):
    response = client.get(f"/questions/topic/{topic.id}", headers=auth_headers)
    assert response.status_code == 403
    assert "Aorta" not in response.text


@pytest.mark.parametrize("role", [UserRole.TEACHER, UserRole.ADMIN])
def test_staff_can_read_solutions_and_permission_uses_current_role(
    client, db, topic, bank, test_user, auth_headers, role,
):
    # The token was issued while the user was a student.
    test_user.role = role
    db.commit()
    response = client.get(f"/questions/topic/{topic.id}", headers=auth_headers)
    assert response.status_code == 200
    by_id = {question["id"]: question for question in response.json()}
    assert by_id[bank[0].id]["correct_option_index"] == 1
    assert by_id[bank[1].id]["exact_word"] == "Aorta"
    test_user.role = UserRole.STUDENT
    db.commit()
    assert client.get(f"/questions/topic/{topic.id}", headers=auth_headers).status_code == 403
