import unittest

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base, GameSession, Topic, User
from app.schemas.game import UserAnswer
from app.schemas.question import QuestionCreate, QuestionResponse
from app.services.game import start_game_session, submit_game_session
from app.services.question import create_question, get_questions_by_topic


class GameModesTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.user = User(name="Student", email="student@example.com", hashed_password="unused")
        self.topic = Topic(name="Medicine")
        self.db.add_all([self.user, self.topic])
        self.db.commit()
        self.trivial = create_question(self.db, QuestionCreate(
            text="Select the answer", topic_id=self.topic.id,
            options=["A", "B", "C", "D"], correct_option_index=2,
        ))
        self.word = create_question(self.db, QuestionCreate(
            text="Starts with A", topic_id=self.topic.id,
            question_type="PASAPALABRA", letter="A", exact_word="Aorta",
        ))

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_trivial_compatibility_and_second_submission(self):
        game = start_game_session(self.db, self.user, self.topic.id)
        self.assertEqual([q.id for q in game.questions], [self.trivial.id])
        public = game.questions[0].model_dump()
        self.assertNotIn("correct_option_index", public)
        self.assertNotIn("exact_word", public)
        answers = [UserAnswer(question_id=self.trivial.id, selected_index=2)]
        result = submit_game_session(self.db, self.user, game.session_id, answers)
        self.assertEqual((result.score, result.total_questions), (1, 1))
        self.assertEqual(result.corrections[0].correct_option_index, 2)
        session = self.db.get(GameSession, game.session_id)
        self.assertTrue(session.is_completed)
        self.assertEqual(session.score, 1)
        with self.assertRaises(HTTPException) as error:
            submit_game_session(self.db, self.user, game.session_id, answers)
        self.assertEqual(error.exception.status_code, 409)

    def test_pasapalabra_normalization_and_privacy(self):
        game = start_game_session(self.db, self.user, self.topic.id, "PASAPALABRA")
        self.assertEqual([q.id for q in game.questions], [self.word.id])
        public = game.questions[0].model_dump()
        self.assertEqual(public["letter"], "A")
        self.assertNotIn("exact_word", public)
        self.assertNotIn("correct_option_index", public)
        result = submit_game_session(self.db, self.user, game.session_id, [
            UserAnswer(question_id=self.word.id, text_answer="  aORTA  "),
        ])
        self.assertEqual(result.score, 1)
        self.assertEqual(result.corrections[0].exact_word, "Aorta")
        self.assertIsNone(result.corrections[0].correct_option_index)
        self.assertEqual(QuestionResponse.model_validate(self.word).question_type, "PASAPALABRA")
        self.assertEqual(len(get_questions_by_topic(self.db, self.topic.id)), 2)

    def test_pasapalabra_wrong_word(self):
        game = start_game_session(self.db, self.user, self.topic.id, "PASAPALABRA")
        result = submit_game_session(self.db, self.user, game.session_id, [
            UserAnswer(question_id=self.word.id, text_answer="Arteria"),
        ])
        self.assertEqual(result.score, 0)

    def test_mode_specific_required_answers(self):
        for mode, question in [("TRIVIAL", self.trivial), ("PASAPALABRA", self.word)]:
            game = start_game_session(self.db, self.user, self.topic.id, mode)
            with self.assertRaises(HTTPException) as error:
                submit_game_session(self.db, self.user, game.session_id, [
                    UserAnswer(question_id=question.id),
                ])
            self.assertEqual(error.exception.status_code, 422)
            self.assertFalse(self.db.get(GameSession, game.session_id).is_completed)

    def test_foreign_question_and_duplicate_answers_rejected(self):
        game = start_game_session(self.db, self.user, self.topic.id)
        for answers in [
            [UserAnswer(question_id=self.word.id, selected_index=2)],
            [UserAnswer(question_id=self.trivial.id, selected_index=2)] * 2,
        ]:
            with self.assertRaises(HTTPException) as error:
                submit_game_session(self.db, self.user, game.session_id, answers)
            self.assertEqual(error.exception.status_code, 422)

    def test_invalid_mode_and_question_payloads(self):
        with self.assertRaises(HTTPException) as error:
            start_game_session(self.db, self.user, self.topic.id, "UNKNOWN")
        self.assertEqual(error.exception.status_code, 422)
        for fields in [
            {},
            {"question_type": "PASAPALABRA", "letter": "A"},
            {"question_type": "PASAPALABRA", "letter": "B", "exact_word": "Aorta"},
        ]:
            with self.assertRaises(ValidationError):
                QuestionCreate(text="Question", topic_id=self.topic.id, **fields)


if __name__ == "__main__":
    unittest.main()
