from app.models import Category, ContentBlock, Question, Subject


def test_academic_relationships_are_optional_for_existing_question_flow(db, topic):
    subject = Subject(name="Illustrative subject")
    block = ContentBlock(name="Illustrative block", subject=subject)
    category = Category(name="Illustrative category", block=block)
    unplaced = Category(name="Unplaced category")
    question = Question(
        text="Existing game question", correct_answer="A", topic=topic,
        category=category, difficulty=2, options=["A", "B", "C", "D"],
        correct_option_index=0,
    )
    db.add_all([question, unplaced])
    db.commit()
    db.expire_all()

    stored = db.get(Question, question.id)
    assert stored.topic.id == topic.id
    assert stored.category.block.subject.name == "Illustrative subject"
    assert stored in stored.category.questions
    assert stored.category in stored.category.block.categories
    assert stored.category.block in stored.category.block.subject.blocks
    assert unplaced.block_id is None
    assert stored.difficulty == 2
