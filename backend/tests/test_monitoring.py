from datetime import datetime, timezone, date
from uuid import uuid4
import pytest
from app.models import User, UserRole, GameSession
from app.models.pasapalabra import PasapalabraMatch, MatchParticipant
from app.dependencies import get_current_user
from app.main import app
from app.routers.monitoring import bounds

def test_dates():
    lo,hi=bounds(date(2026,7,1),date(2026,7,1))
    assert lo.hour==23 and hi.hour==23 and (hi-lo).days==1
    spring=bounds(date(2026,3,29),date(2026,3,29));assert (spring[1]-spring[0]).total_seconds()==23*3600
    with pytest.raises(Exception):bounds(date(2026,7,2),date(2026,7,1))

def test_permissions_counts_privacy_and_pagination(client,db):
    teacher=User(name="Staff",email="staff@test.invalid",hashed_password="unused",role=UserRole.TEACHER)
    student=User(name="Student",email="student@test.invalid",hashed_password="unused",role=UserRole.STUDENT)
    db.add_all([teacher,student]);db.commit()
    assert client.get('/monitoring/activity').status_code==401
    app.dependency_overrides[get_current_user]=lambda:student
    assert client.get('/monitoring/activity').status_code==403
    app.dependency_overrides[get_current_user]=lambda:teacher
    now=datetime(2026,7,1,12,tzinfo=timezone.utc)
    m=PasapalabraMatch(owner_id=teacher.id,start_operation_id=str(uuid4()),start_payload={},play_mode="ONLINE",rules_version="pasapalabra-online-v1",status="FINISHED",outcome="ABANDONMENT",created_at=now)
    db.add(m);db.flush()
    for position,user in enumerate([teacher,student],1):
        s=GameSession(user_id=user.id,topic_id=None,game_mode="PASAPALABRA",question_ids=list(range(20)),shared_match_id=m.id,format_key=m.rules_version,pending_count=20,created_at=now)
        db.add(s);db.flush();db.add(MatchParticipant(match_id=m.id,position=position,user_id=user.id,name=user.name,session_id=s.id))
    db.add(GameSession(user_id=teacher.id,topic_id=None,game_mode="TRIVIAL",question_ids=[1],is_completed=False,created_at=now));db.commit()
    r=client.get('/monitoring/activity?start=2026-07-01&end=2026-07-01&limit=1').json()
    assert (r['started'],r['abandoned'],r['unknown'],r['unique_registered'])==(2,1,1,2)
    assert len(r['items'])==1 and r['total']==2
    assert sum(g['sessions'] for g in r['groups'])==3  # two online participants + individual
    assert sum(x['registered'] for x in client.get('/monitoring/activity?limit=100').json()['items'])==3
    assert r['groups'][0]['sessions']==2 and r['groups'][0]['pending']==40
    assert 'email' not in str(r) and 'password' not in str(r) and 'snapshot' not in str(r)
    assert client.get('/monitoring/activity?game=TRIVIAL').json()['started']==1
    assert client.get('/monitoring/activity?start=2027-01-01').json()['started']==0
    for query in ['game=INVALID','limit=101','skip=-1','start=2026-07-02&end=2026-07-01']:
        assert client.get('/monitoring/activity?'+query).status_code==422
    app.dependency_overrides.pop(get_current_user,None)

def test_local_guest_excluded_and_normal_results(client,db,topic):
    from app.models import Question,AnswerLog
    admin=User(name="Admin",email="admin@test.invalid",hashed_password="unused",role=UserRole.ADMIN);db.add(admin);db.flush()
    now=datetime(2026,1,1,tzinfo=timezone.utc)
    q=Question(topic_id=topic.id,text="Private clue",correct_answer="secret",question_type="TRIVIAL");db.add(q);db.flush()
    m=PasapalabraMatch(owner_id=admin.id,start_operation_id=str(uuid4()),start_payload={},play_mode="LOCAL",rules_version="pasapalabra-local-v1",status="FINISHED",outcome="NORMAL",created_at=now);db.add(m);db.flush()
    s=GameSession(user_id=admin.id,topic_id=topic.id,game_mode="PASAPALABRA",question_ids=[q.id],shared_match_id=m.id,format_key=m.rules_version,is_completed=True,pending_count=0,created_at=now);db.add(s);db.flush()
    db.add_all([MatchParticipant(match_id=m.id,position=1,user_id=admin.id,name="Admin",session_id=s.id),MatchParticipant(match_id=m.id,position=2,name="Private guest")])
    db.add(AnswerLog(game_session_id=s.id,question_id=q.id,question_text="Private clue",question_type="PASAPALABRA",is_correct=True));db.commit()
    app.dependency_overrides[get_current_user]=lambda:admin
    r=client.get('/monitoring/activity').json()
    assert r['normal']==1 and r['unique_registered']==1 and r['items'][0]['guests']==1
    assert r['groups'][0]['correct']==1 and r['groups'][0]['sessions']==1
    assert 'Private' not in str(r) and 'secret' not in str(r)
    assert client.get('/monitoring/activity?skip=20').json()['items']==[]
    m.status='RUNNING';m.outcome=None;db.commit()
    opened=client.get('/monitoring/activity').json()
    assert opened['open']==1 and opened['normal']==0
    assert db.get(PasapalabraMatch,m.id).status=='RUNNING'
    app.dependency_overrides.pop(get_current_user,None)

def test_date_boundaries_and_incomplete_completed_session(client,db,topic):
    u=User(name="Staff",email="boundary@test.invalid",hashed_password="unused",role=UserRole.TEACHER);db.add(u);db.flush()
    for moment in [datetime(2026,6,30,22,59,tzinfo=timezone.utc),datetime(2026,6,30,23,tzinfo=timezone.utc),datetime(2026,7,1,22,59,tzinfo=timezone.utc),datetime(2026,7,1,23,tzinfo=timezone.utc)]:
        db.add(GameSession(user_id=u.id,topic_id=topic.id,game_mode="TRIVIAL",question_ids=[1],is_completed=True,created_at=moment))
    db.commit();app.dependency_overrides[get_current_user]=lambda:u
    r=client.get('/monitoring/activity?start=2026-07-01&end=2026-07-01').json()
    assert r['started']==2 and r['normal']==2 and r['unique_registered']==1
    assert r['groups'][0]['unknown_sessions']==2
    assert r['groups'][0]['correct']==0 and r['groups'][0]['wrong']==0
    app.dependency_overrides.pop(get_current_user,None)
