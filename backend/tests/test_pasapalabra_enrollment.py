"""Enrollment-bound catalog, two registered local players and shared online engine."""
import json
from uuid import uuid4
from unittest.mock import patch
import pytest
from sqlalchemy import select, func
from app.models import User, UserRole, Subject, AcademicEdition, Enrollment, Topic, Question, GameSession
from app.models.pasapalabra import PasapalabraMatch, MatchQuestion
from app.services import pasapalabra as engine
from app.utils.security import get_password_hash
from test_user_onboarding import dni

PASSWORD="synthetic-pass-ñ-2026"
@pytest.fixture
def academic_bank(db,client,monkeypatch):
    from app.utils import auth_limits
    monkeypatch.setattr(auth_limits,"limits",auth_limits.AuthLimits())
    monkeypatch.setattr(engine.RNG,"choice",lambda values:1)
    subject=Subject(name="Synthetic course",code="SYNTH")
    db.add(subject);db.flush()
    editions=[AcademicEdition(subject_id=subject.id,academic_year=y) for y in ("2026-2027","2027-2028")]
    db.add_all(editions);db.flush()
    topics=[Topic(name="Same theme",edition_id=e.id,icon_data="data:image/png;base64,year"+str(i)) for i,e in enumerate(editions)]
    db.add_all(topics);db.flush()
    hashed=get_password_hash(PASSWORD)
    users=[User(name=f"Synthetic student {i}",email=f"pp-{i}@example.com",dni=dni(91000000+i),hashed_password=hashed,role=UserRole.STUDENT) for i in range(3)]
    db.add_all(users);db.flush()
    db.add_all([Enrollment(student_id=u.id,subject_id=subject.id,edition_id=editions[0 if i<2 else 1].id,play_enabled=True) for i,u in enumerate(users)])
    for i,(t,e) in enumerate(zip(topics,editions)):
        db.add_all([Question(text=f"Year {i} clue {n}",question_type="PASAPALABRA",letter="A",exact_word="Arteria",correct_answer="Arteria",difficulty=1,topic_id=t.id,edition_id=e.id,subject_id=subject.id) for n in range(40)])
        db.add(Question(text="Retired",question_type="PASAPALABRA",letter="A",exact_word="Arteria",correct_answer="Arteria",difficulty=1,topic_id=t.id,edition_id=e.id,is_active=False))
        db.add(Question(text="Open board only",question_type="INMUNOQUEST",reference_answer="Private",difficulty=1,topic_id=t.id,edition_id=e.id))
    db.commit()
    headers=[]
    for u in users:
        r=client.post("/auth/login",data={"username":u.dni,"password":PASSWORD});assert r.status_code==200
        headers.append({"Authorization":"Bearer "+r.json()["access_token"]})
    return subject,editions,topics,users,headers

def selection(bank,which=0):
    s,ed,topics,users,headers=bank
    return dict(subject_id=s.id,topic_id=topics[which].id,difficulty=1)

def test_catalog_is_resolved_from_enrollment_and_has_no_answers(client,db,academic_bank):
    s,ed,t,u,h=academic_bank
    assert client.get("/pasapalabra/subjects").status_code==401
    assert client.get("/pasapalabra/subjects",headers=h[0]).json()==[dict(id=s.id,name=s.name,academic_year="2026-2027")]
    for i,who in enumerate((0,2)):
        result=client.get(f"/pasapalabra/subjects/{s.id}/topics",headers=h[who]).json()
        assert result["topics"][0]["id"]==t[i].id and result["topics"][0]["icon"]==t[i].icon_data
        assert result["topics"][0]["levels"]==[dict(level=n,available=40 if n==1 else 0) for n in range(1,5)]
        assert "Arteria" not in json.dumps(result) and "Private" not in json.dumps(result)
    assert client.post("/pasapalabra/preparations",headers=h[0],json=selection(academic_bank,1)).status_code==409
    assert client.post("/pasapalabra/preparations",headers=h[0],json={**selection(academic_bank),"difficulty":2}).json()["can_start"] is False
    assert client.post("/pasapalabra/preparations",headers=h[0],json={**selection(academic_bank),"edition_id":ed[1].id}).status_code==422

def test_local_identity_results_retry_and_history_survive_year_change(client,db,academic_bank):
    s,ed,t,u,h=academic_bank
    body={**selection(academic_bank),"operation_id":str(uuid4()),"guest_dni":u[1].dni,"guest_password":PASSWORD}
    assert client.post("/pasapalabra/local/start",headers=h[0],json={**body,"guest_password":"wrong"}).status_code==400
    assert client.get("/auth/me",headers=h[0]).status_code==200
    assert client.post("/pasapalabra/local/start",headers=h[0],json={**body,"guest_dni":u[0].dni}).status_code==409
    assert client.post("/pasapalabra/local/start",headers=h[0],json={**body,"guest_dni":u[2].dni}).status_code==409
    assert client.post("/pasapalabra/local/start",headers=h[0],json={**body,"topic_id":t[1].id}).status_code==409
    response=client.post("/pasapalabra/local/start",headers=h[0],json=body)
    assert response.status_code==201,response.text
    state=response.json();mid=state["id"]
    assert all(p["registered"] for p in state["participants"])
    assert state["academic"]["edition_id"]==ed[0].id and state["topic_icon"]==t[0].icon_data
    assert client.post("/pasapalabra/local/start",headers=h[0],json=body).json()["id"]==mid
    assert db.scalar(select(func.count()).select_from(GameSession))==2
    stored=db.get(PasapalabraMatch,mid)
    assert PASSWORD not in json.dumps(stored.start_payload) and u[1].dni not in json.dumps(stored.start_payload)
    assert client.get(f"/pasapalabra/matches/{mid}",headers=h[1]).json()["personal_session_id"]!=state["personal_session_id"]
    assert client.post(f"/pasapalabra/matches/{mid}/pass",headers=h[1],json=dict(operation_id=str(uuid4()),expected_version=state["version"],participant=1,number=1)).status_code==403
    # Each participant answers, while the authenticated host remains the transport actor.
    for participant in (1,2):
        for correct in (True,False):
            state=client.post(f"/pasapalabra/matches/{mid}/answer",headers=h[0],json=dict(operation_id=str(uuid4()),expected_version=state["version"],participant=participant,number=state["active_question"]["number"],text_answer="Arteria" if correct else "incorrect")).json()["state"]
    sessions=list(db.scalars(select(GameSession).order_by(GameSession.id)))
    assert {g.user_id for g in sessions}=={u[0].id,u[1].id} and all(g.score==1 and g.wrong_count==1 for g in sessions)
    snapshot=json.dumps(sessions[0].content_context,sort_keys=True)
    old_enrollment=db.get(Enrollment,(u[0].id,ed[0].id));old_enrollment.play_enabled=False;db.flush()
    db.add(Enrollment(student_id=u[0].id,subject_id=s.id,edition_id=ed[1].id,play_enabled=True));db.commit()
    db.refresh(sessions[0]);assert json.dumps(sessions[0].content_context,sort_keys=True)==snapshot
    assert client.get(f"/pasapalabra/matches/{mid}",headers=h[0]).json()["academic"]["edition_id"]==ed[0].id
    assert client.post("/pasapalabra/local/start",headers=h[0],json=body).json()["id"]==mid
    assert client.post("/pasapalabra/local/start",headers=h[0],json={**body,"operation_id":str(uuid4())}).status_code==409
    newer=client.post("/pasapalabra/local/start",headers=h[0],json={**selection(academic_bank,1),"operation_id":str(uuid4()),"guest_dni":u[2].dni,"guest_password":PASSWORD})
    assert newer.status_code==201 and newer.json()["academic"]["edition_id"]==ed[1].id
    assert newer.json()["topic_icon"]==t[1].icon_data

def test_online_membership_and_start_recheck_current_enrollment(client,db,academic_bank):
    s,ed,t,u,h=academic_bank
    room=client.post("/pasapalabra/rooms",headers=h[0],json={**selection(academic_bank),"operation_id":str(uuid4())}).json()
    join=dict(code=room["code"],operation_id=str(uuid4()))
    assert client.post("/pasapalabra/rooms/join",headers=h[2],json=join).status_code==409
    room=client.post("/pasapalabra/rooms/join",headers=h[1],json={**join,"operation_id":str(uuid4())}).json()
    for who in (0,1):
        room=client.post(f"/pasapalabra/rooms/{room['id']}/ready",headers=h[who],json=dict(operation_id=str(uuid4()),expected_version=room["version"])).json()
    en=db.get(Enrollment,(u[1].id,ed[0].id));en.play_enabled=False;db.flush()
    db.add(Enrollment(student_id=u[1].id,subject_id=s.id,edition_id=ed[1].id,play_enabled=True));db.commit()
    assert client.post(f"/pasapalabra/rooms/{room['id']}/start",headers=h[0],json=dict(operation_id=str(uuid4()),expected_version=room["version"])).status_code==409
    db.get(Enrollment,(u[1].id,ed[1].id)).play_enabled=False;db.flush();en.play_enabled=True;db.commit()
    room=client.post(f"/pasapalabra/rooms/{room['id']}/start",headers=h[0],json=dict(operation_id=str(uuid4()),expected_version=room["version"])).json()
    assert room["status"]=="STARTED"
    states=[client.get(f"/pasapalabra/matches/{room['match_id']}",headers=h[i]).json() for i in (0,1)]
    assert [r["self_position"] for r in states]==[1,2]
    assert states[1]["active_question"] is None
    assert all(r["academic"]["edition_id"]==ed[0].id for r in states)

def test_companion_credentials_are_not_echoed_and_limited_before_hash(client,db,academic_bank,monkeypatch):
    from app.utils import auth_limits
    from app.services import pasapalabra_academic
    s,ed,t,u,h=academic_bank
    body={**selection(academic_bank),"operation_id":str(uuid4()),"guest_dni":u[1].dni,"guest_password":PASSWORD}
    invalid=client.post("/pasapalabra/local/start",headers=h[0],json={**body,"guest_password":"s"*256})
    assert invalid.status_code==422 and "s"*256 not in invalid.text and u[1].dni not in invalid.text
    auth_limits.limits.rules["login"]=(1,600);auth_limits.limits.entries.clear()
    first=client.post("/pasapalabra/local/start",headers=h[0],json={**body,"guest_password":"wrong"})
    assert first.status_code==400
    with patch.object(pasapalabra_academic,"verify_password") as verify:
        limited=client.post("/pasapalabra/local/start",headers=h[0],json=body)
        assert limited.status_code==429 and int(limited.headers["Retry-After"])>0
        verify.assert_not_called()
