from unittest.mock import patch
from uuid import uuid4
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from test_pasapalabra_postgres import postgres


def test_academic_migration_preserves_legacy_and_guards_history(postgres):
    cfg=Config("alembic.ini")
    with patch("app.database.engine",postgres):
        command.downgrade(cfg,"a21b30c41d52")
        user_id=uuid4()
        with postgres.begin() as c:
            c.execute(text("INSERT INTO users(id,name,email,hashed_password,role) VALUES(:id,'Legacy','legacy@example.test','unused','STUDENT')"),{'id':user_id})
            c.execute(text("INSERT INTO topics(id,name) VALUES(1,'Original')"))
            c.execute(text("INSERT INTO game_engine_sessions(id,user_id,topic_id,score,is_completed,created_at,question_ids,game_mode) VALUES(1,:id,1,0,false,now(),'[]','TRIVIAL')"),{'id':user_id})
            before=c.execute(text('select to_jsonb(g) from game_engine_sessions g')).scalar_one()
        command.upgrade(cfg,'head')
        with postgres.connect() as c:
            assert c.execute(text('select to_jsonb(g) from game_engine_sessions g')).scalar_one()==before
            assert c.execute(text('select question_snapshot from game_engine_sessions')).scalar_one() is None
        assert next(c for c in inspect(postgres).get_columns('game_engine_sessions') if c['name']=='topic_id')['nullable']
        command.check(cfg)
        with postgres.begin() as c:
            c.execute(text('update game_engine_sessions set topic_id=null'))
        with pytest.raises(RuntimeError,match='Academic history'):
            command.downgrade(cfg,'a21b30c41d52')
        with postgres.connect() as c:
            assert c.execute(text('select version_num from alembic_version')).scalar_one()=='b31c40d52e63'


def test_academic_engines_on_migrated_postgresql(postgres):
    from sqlalchemy.orm import Session
    from sqlalchemy import select
    from test_academic_selection import bank
    from app.services import game, pasapalabra as engine
    from app.schemas.pasapalabra import LocalStart
    from app.models import GameSession
    from app.models.pasapalabra import MatchQuestion
    with Session(postgres) as db:
        selection,topics,users=bank.__wrapped__(db)
        trivial=game.start_game_session(db,users[0],topic_id=None,**selection)
        assert trivial.topic_id is None and len(trivial.questions)==10
        state=engine.start_local(db,users[0],LocalStart(**selection,guest_name='Invitado',operation_id=uuid4()))
        assert state['academic']['category_id']==selection['category_id']
        questions=list(db.scalars(select(MatchQuestion)))
        assert len({q.question_id for q in questions})==40
        assert {q.snapshot['topic_id'] for q in questions}=={t.id for t in topics}
        assert all(s.topic_id is None for s in db.scalars(select(GameSession)))
