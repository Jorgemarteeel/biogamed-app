"""Guards + opt-in integration against a NEW restored demo clone, never normal DB."""
import copy
import json
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from tools.copy_demo_content import TABLES, activity, digest, guard, run


def source_stub():
    return {"identity":{"system_identifier":"origin","database":"biogamed"},
            "tables":{name:[] for name in TABLES}}


@pytest.mark.parametrize("identity,expected_database,expected_system", [
    ({"database":"biogamed","system_identifier":"origin"},"biogamed","origin"),
    ({"database":"biogamed_demo","system_identifier":"origin"},"biogamed_demo","origin"),
    ({"database":"other","system_identifier":"demo"},"other","demo"),
    ({"database":"biogamed_demo","system_identifier":"demo"},"demo_clone","demo"),
    ({"database":"biogamed_demo","system_identifier":"demo"},"biogamed_demo","wrong"),
])
def test_rejects_normal_cluster_wrong_database_and_wrong_identity(identity, expected_database, expected_system):
    with pytest.raises(ValueError):
        guard(identity,source_stub(),expected_database,expected_system)


def test_accepts_exact_separate_cluster_only_content_payload():
    identity={"database":"biogamed_demo","system_identifier":"demo"}
    guard(identity,source_stub(),"biogamed_demo","demo")
    bad=source_stub()
    bad["tables"]["users"]=[]
    with pytest.raises(ValueError,match="five content"):
        guard(identity,bad,"biogamed_demo","demo")
    bad=source_stub()
    bad["tables"]["questions"]=[{"id":1},{"id":1}]
    with pytest.raises(ValueError,match="Duplicate"):
        guard(identity,bad,"biogamed_demo","demo")


def test_content_digest_is_stable_and_keeps_answers_alternatives_and_retirement():
    value={"id":1,"options":["a","b"],"accepted_answers":["uno","dos"],"is_active":False}
    assert digest(value)==digest(dict(reversed(list(value.items()))))
    for field,replacement in [("options",["b","a"]),("accepted_answers",["uno"]),("is_active",True)]:
        assert digest({**value,field:replacement})!=digest(value)


@pytest.mark.skipif(not os.getenv("DEMO_CONTENT_TEST_DATABASE"),reason="requires a new verified demo restore clone")
def test_real_postgres_copy_rollback_idempotency_conflicts_and_personal_data_preserved():
    database=os.environ["DEMO_CONTENT_TEST_DATABASE"]
    assert database.startswith("demo_content_test_")
    engine=create_engine(os.environ["DATABASE_URL"])
    engine=create_engine(engine.url.set(database=database))
    source=json.loads(Path(os.environ["DEMO_CONTENT_SOURCE"]).read_text())
    plan=json.loads(Path(os.environ["DEMO_CONTENT_PLAN"]).read_text())
    def fingerprints(c):
        return {t:c.execute(text("select md5(coalesce(string_agg(md5(to_jsonb(x)::text),'' order by id),'')) from "+t+" x")).scalar() for t in TABLES}
    with engine.connect() as c:
        expected=c.execute(text("select system_identifier::text from pg_control_system()")).scalar()
        baseline=fingerprints(c)
        personal=activity(c)
    with engine.connect() as c:
        tx=c.begin()
        dry=run(c,source,plan,database,expected)
        assert all(h["source"]==h["target_normalized"] for h in dry["verified_content"].values())
        tx.rollback()
        assert fingerprints(c)==baseline
    with engine.begin() as c:
        first=run(c,source,plan,database,expected)
        assert first["inserted"]["questions"]==len(source["tables"]["questions"])
        assert activity(c)==personal
    with engine.begin() as c:
        second=run(c,source,plan,database,expected)
        assert not any(second["inserted"].values())
        assert first["maps"]==second["maps"]
        stable=fingerprints(c)
        assert activity(c)==personal
        for original in source["tables"]["questions"]:
            if not original["is_active"]:
                target=second["maps"]["questions"][str(original["id"])]["target_id"]
                assert c.execute(text("select is_active from questions where id=:id"),{"id":target}).scalar() is False
    bad=copy.deepcopy(plan)
    bad["organization"]["blocks"][-1]["categories"][0]["source_question_ids"].append(1)
    with pytest.raises(ValueError,match="retired"):
        with engine.begin() as c:
            run(c,source,bad,database,expected)
    with engine.connect() as c:
        assert fingerprints(c)==stable
        assert activity(c)==personal
        tx=c.get_transaction()
        tx.rollback()
        tx=c.begin()
        target=second["maps"]["questions"][str(source["tables"]["questions"][0]["id"])]["target_id"]
        c.execute(text("update questions set text='changed by rollback-only test' where id=:id"),{"id":target})
        with pytest.raises(ValueError,match="Owned content changed"):
            run(c,source,plan,database,expected)
        tx.rollback()
        assert fingerprints(c)==stable
    engine.dispose()
