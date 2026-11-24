import base64
import csv
import io
from uuid import uuid4
from sqlalchemy import select, func
from app.models import AcademicEdition, Question, Topic
from app.services import edition_content as service
from test_user_onboarding import managers


def content_csv(rows, fixed=False):
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(([] if fixed else ["tematica"]) + service.COLUMNS)
    writer.writerows(rows)
    return out.getvalue().encode("utf-8-sig")


def request(client, auth, path, raw, **fields):
    return client.post(path, headers=auth, files={"file": ("test.csv", raw, "text/csv")}, data=fields)


def test_scoped_content_mixed_csv_atomicity_and_privacy(client, db, managers):
    roles, _ = managers
    auth = roles["teacher"]
    ed = db.scalar(select(AcademicEdition))
    next_ed = AcademicEdition(subject_id=ed.subject_id, academic_year="2027-2028")
    old = Question(text="Original", question_type="INMUNOQUEST", reference_answer="Original solution", bank="SPLEEN", difficulty=2)
    db.add_all([next_ed, old])
    db.commit()
    paths = [f"/edition-content/{e.id}" for e in (ed, next_ed)]
    for path in paths:
        assert client.get(path).status_code == 401
        assert client.get(path, headers=roles["student"]).status_code == 403
    topics = [client.post(path+"/topics", headers=auth, json={"name":"Tejidos"}).json() for path in paths]
    assert topics[0]["id"] != topics[1]["id"]
    assert client.post(paths[0]+"/topics", headers=auth, json={"name":"tejidos"}).status_code == 409
    raw = content_csv([
        ["Tejidos","INMUNOQUEST",2,"¿Qué es un tejido?","Conjunto de células","T1","","",""],
        ["Tejidos","PASAPALABRA",1,"Con la A: vaso que sale del corazón","","","A","Arteria",""],
    ])
    p = request(client, auth, paths[0]+"/validate", raw).json()
    assert p["valid"] == 2 and not p["errors"]
    assert {g["game"] for g in p["groups"]} == {"INMUNOQUEST","PASAPALABRA"}
    fields = {"proof":p["proof"], "operation_id":str(uuid4())}
    result = request(client, auth, paths[0]+"/confirm", raw, **fields)
    assert result.status_code == 200
    assert result.json()["count"] == 2
    assert request(client, auth, paths[0]+"/confirm", raw, **fields).json() == result.json()
    assert request(client, auth, paths[1]+"/confirm", raw, **fields).status_code == 422
    assert len(client.get(paths[0]+"/questions", params={"topic_id":topics[0]["id"]}, headers=auth).json()["items"]) == 2
    assert client.get(paths[1]+"/questions", params={"topic_id":topics[0]["id"]}, headers=auth).status_code == 404
    assert client.get(paths[1]+"/questions", params={"topic_id":topics[1]["id"]}, headers=auth).json()["total"] == 0
    assert request(client, auth, paths[0]+"/validate", raw).json()["errors"]
    invalid = content_csv([["Missing","INMUNOQUEST",1,"Q","A","","","",""],
                           ["Tejidos","INMUNOQUEST",9,"Q","A","","","",""]])
    errors = request(client, auth, paths[0]+"/validate", invalid).json()
    assert not errors["proof"] and {e["row"] for e in errors["errors"]} == {2,3}
    assert db.scalar(select(func.count()).select_from(Question)) == 3
    fixed = content_csv([["INMUNOQUEST",3,"Otra pregunta","Otra respuesta","","","",""]], fixed=True)
    p = request(client, auth, paths[0]+"/validate", fixed, topic_id=topics[0]["id"]).json()
    assert p["proof"]
    assert request(client, auth, paths[0]+"/confirm", fixed, topic_id=topics[0]["id"], proof=p["proof"],operation_id=str(uuid4())).json()["count"] == 1
    assert client.put(paths[0]+"/board",headers=auth,json={"SPLEEN":topics[0]["id"]}).json()["slots"][2]["decks"][1]["count"] == 1
    assert client.put(paths[0]+"/board",headers=auth,json={"SPLEEN":topics[1]["id"]}).status_code == 404
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWQAAAABJRU5ErkJggg==")
    assert request(client, auth, paths[0]+f'/topics/{topics[0]["id"]}/icon',png).status_code == 200
    assert request(client, auth, paths[0]+f'/topics/{topics[0]["id"]}/icon',b"<svg/>").status_code == 422
    assert client.get(paths[1],headers=auth).json()["topics"][0]["icon"] is None
    db.refresh(old)
    assert old.edition_id is None and old.text == "Original" and old.bank == "SPLEEN"
    assert client.get("/edition-content/legacy/pending",headers=auth).json()["total"] == 1

def test_receipt_recovers_lost_response_without_writes_and_requires_owner(client, db, managers):
    roles, _ = managers
    auth = roles["teacher"]
    ed = db.scalar(select(AcademicEdition))
    base = f"/edition-content/{ed.id}"
    topic = client.post(base+"/topics", headers=auth, json={"name":"Recuperación"}).json()
    raw = content_csv([["INMUNOQUEST",1,"Recuperar una confirmación","Referencia","","","",""]], fixed=True)
    op = str(uuid4())
    receipt = f"{base}/receipts/{op}?topic_id={topic['id']}"
    assert client.get(receipt, headers=auth).json()["status"] == "unknown"
    p = request(client, auth, base+"/validate",raw,topic_id=topic["id"]).json()
    fields = dict(topic_id=topic["id"],proof=p["proof"],operation_id=op)
    # The server commits while the caller discards the HTTP response.
    request(client, auth, base+"/confirm",raw,**fields)
    for _ in range(2):
        r = client.get(receipt, headers=auth)
        assert r.status_code == 200 and r.json()["count"] == 1 and r.json()["status"] == "confirmed"
    assert request(client, auth, base+"/confirm",raw,**fields).json()["count"] == 1
    assert db.scalar(select(func.count()).select_from(Question).where(Question.edition_id==ed.id)) == 1
    assert client.get(receipt).status_code == 401
    assert client.get(receipt, headers=roles["student"]).status_code == 403
    assert client.get(receipt, headers=roles["admin"]).json()["status"] == "unknown"

def test_unassigned_filter_is_global_includes_retired_and_paginates(client, db, managers):
    roles, _ = managers
    ed = db.scalar(select(AcademicEdition))
    topic = Topic(name="Previous topic")
    scoped = Topic(name="Edition topic", edition_id=ed.id)
    db.add_all([topic, scoped])
    db.flush()
    unassigned = [Question(text=f"Previous {n}", question_type="TRIVIAL" if n % 2 else "PASAPALABRA",
                           topic_id=topic.id, correct_answer="Stored", is_active=n % 3 != 0) for n in range(24)]
    unassigned.append(Question(text="Previous open question", question_type="INMUNOQUEST",
                               reference_answer="Private reference", bank="DNA", difficulty=1, is_active=False))
    assigned = Question(text="Scoped", question_type="INMUNOQUEST", reference_answer="Scoped reference",
                        difficulty=1, topic_id=scoped.id, edition_id=ed.id, subject_id=ed.subject_id)
    db.add_all([*unassigned, assigned])
    db.commit()
    expected = sorted(q.id for q in unassigned)
    url = "/edition-content/legacy/pending"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=roles["student"]).status_code == 403
    first = client.get(url, headers=roles["teacher"]).json()
    second = client.get(url, params={"skip":20}, headers=roles["teacher"]).json()
    assert first["total"] == second["total"] == 25
    assert [r["id"] for r in first["items"] + second["items"]] == expected
    assert len(first["items"]) == 20 and len(second["items"]) == 5
    assert all("reference_answer" not in r and "correct_answer" not in r for r in first["items"] + second["items"])
    assert client.get(url, headers=roles["admin"]).json()["total"] == 25
