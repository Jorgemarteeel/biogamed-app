from datetime import datetime,timezone
from uuid import uuid4
import pytest
from sqlalchemy.exc import IntegrityError
from app.main import app
from app.dependencies import get_current_user
from app.models import User,UserRole,Question,GameSession,AnswerLog
from app.models.pasapalabra import PasapalabraMatch,MatchParticipant,MatchQuestion
NOW=datetime(2026,7,1,12,tzinfo=timezone.utc)

def user(db,name,role=UserRole.STUDENT):
    u=User(name=name,email=name+'@test.invalid',hashed_password='unused',role=role);db.add(u);db.flush();return u

def question(db,topic):
    q=Question(topic_id=topic.id,text='Current bank text',correct_answer='secret',question_type='TRIVIAL',is_active=False);db.add(q);db.flush();return q

def answer(db,u,q,correct=False,text='Historical text',options=None,shared=None,mode='TRIVIAL',fmt=None):
    s=GameSession(user_id=u.id,topic_id=q.topic_id,game_mode=mode,question_ids=[q.id],created_at=NOW,shared_match_id=shared,format_key=fmt);db.add(s);db.flush()
    a=AnswerLog(game_session_id=s.id,question_id=q.id,question_text=text,question_type=mode,is_correct=correct,options=options or ['A','B'],selected_index=0 if correct else 1,correct_option_index=0,text_answer=('private solution' if correct else 'saved') if mode=='PASAPALABRA' else None,exact_word='private solution' if mode=='PASAPALABRA' else None);db.add(a);db.flush();return s,a

def test_versions_counts_permissions_dates_and_pagination(client,db,topic):
    staff=user(db,'staff',UserRole.TEACHER);a=user(db,'a');b=user(db,'b');q=question(db,topic);q2=question(db,topic)
    assert client.get('/monitoring/difficulties.csv').status_code==401
    assert client.get('/monitoring/difficulties').status_code==401
    app.dependency_overrides[get_current_user]=lambda:a
    assert client.get('/monitoring/difficulties.csv').status_code==403
    assert client.get('/monitoring/difficulties').status_code==403
    for u,correct in [(a,False),(a,True),(b,False)]:answer(db,u,q,correct)
    answer(db,a,q,True,text='Edited historical version')
    _,solution_edit=answer(db,a,q,True);solution_edit.correct_option_index=1;solution_edit.selected_index=1
    answer(db,b,q2,True)  # same wording, different question ID
    s,old=answer(db,a,q);old.options=None;old.correct_option_index=None
    q.text='Edited current bank';db.commit()
    app.dependency_overrides[get_current_user]=lambda:staff
    r=client.get('/monitoring/difficulties?minimum=1').json()
    assert (r['evaluated'],r['excluded_records'],r['total'])==(6,1,4)
    first=r['items'][0];assert (first['evaluated'],first['accounts'],first['correct'],first['wrong'])==(3,2,1,2)
    assert first['error_percent']==pytest.approx(200/3)
    assert first['text']=='Historical text' and 'secret' not in str(r) and 'private solution' not in str(r) and '@test' not in str(r)
    assert client.get('/monitoring/difficulties').json()['total']==0
    assert client.get('/monitoring/difficulties?minimum=3').json()['total']==1
    second=client.get('/monitoring/difficulties?minimum=1&limit=1&skip=1').json()['items']
    assert len(second)==1 and second[0]['version_reference']!=first['version_reference']
    assert any(row['wrong']==0 for row in r['items'])
    assert client.get('/monitoring/difficulties?minimum=1&start=2026-07-02').json()['evaluated']==0
    assert client.get('/monitoring/difficulties?minimum=1&start=2026-07-01&end=2026-07-01').json()['evaluated']==6
    assert client.get('/monitoring/difficulties?game=PASAPALABRA').json()['evaluated']==0
    for query in ['minimum=0','minimum=1.5','minimum=100001','skip=-1','limit=101','game=OTHER','start=2026-07-02&end=2026-07-01']:
        assert client.get('/monitoring/difficulties?'+query).status_code==422
    # Existing uniqueness prevents retry/duplicate educational observations.
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(AnswerLog(game_session_id=s.id,question_id=q.id,question_text='duplicate',question_type='TRIVIAL',is_correct=False));db.flush()
    assert client.get('/monitoring/difficulties?minimum=1').json()['evaluated']==6

def test_shared_accounts_guest_pass_and_formats(client,db,topic):
    a=user(db,'admin',UserRole.ADMIN);b=user(db,'online');q=question(db,topic)
    for mode in ['ONLINE','LOCAL']:
        m=PasapalabraMatch(owner_id=a.id,start_operation_id=str(uuid4()),start_payload={},play_mode=mode,rules_version='pasapalabra-'+mode.lower()+'-v1',status='RUNNING',created_at=NOW);db.add(m);db.flush()
        for position,u in enumerate([a,b],1):
            s,log=answer(db,u,q,position==1,mode='PASAPALABRA',shared=m.id,fmt=m.rules_version)
            s.created_at=datetime(2026,7,2,12,tzinfo=timezone.utc)
            db.add(MatchParticipant(match_id=m.id,position=position,user_id=u.id if mode=='ONLINE' or position==1 else None,name='Private name',session_id=s.id))
        # A stored pass has no evaluated answer. It must not enter denominators.
        db.flush();p=db.query(MatchParticipant).filter_by(match_id=m.id,position=1).one()
        q2=question(db,topic);db.add(MatchQuestion(match_id=m.id,participant_id=p.id,number=2,question_id=q2.id,snapshot={'text':'passed'},state='PASSED'))
    db.commit();app.dependency_overrides[get_current_user]=lambda:a
    r=client.get('/monitoring/difficulties?minimum=1').json()
    assert client.get('/monitoring/difficulties?minimum=1&start=2026-07-01&end=2026-07-01').json()['evaluated']==3
    assert r['evaluated']==3 and r['total']==2 and r['excluded_records']==0
    online=next(x for x in r['items'] if 'en línea' in x['format_label'])
    assert (online['accounts'],online['correct'],online['wrong'],online['evaluated'])==(2,1,1,2)
    local=next(x for x in r['items'] if 'local' in x['format_label']);assert local['evaluated']==1 and local['accounts']==1
    assert 'Private name' not in str(r) and 'private solution' not in str(r)


def test_csv_all_groups_filters_versions_and_limit(client,db,topic,monkeypatch):
    import csv,io
    from decimal import Decimal
    from app.routers import monitoring
    staff=user(db,'exporter',UserRole.ADMIN);other=user(db,'second');q=question(db,topic)
    clue='=SUM(1;2)\n"áé"'
    answer(db,staff,q,True,text=clue);answer(db,other,q,False,text=clue)
    answer(db,staff,q,True,text='Otra versión histórica')
    for i in range(24):answer(db,staff,question(db,topic),False,text='Fila á\nsegunda;"línea"')
    db.commit();app.dependency_overrides[get_current_user]=lambda:staff
    report=client.get('/monitoring/difficulties?minimum=1&limit=100').json()
    response=client.get('/monitoring/difficulties.csv?minimum=1')
    assert response.status_code==200 and response.content.startswith(b'\xef\xbb\xbf')
    rows=list(csv.reader(io.StringIO(response.content.decode('utf-8-sig')),delimiter=';'))
    assert len(rows)==27 and len(rows[0])==8 and rows[0][-1]=='Error (%)'
    assert len(client.get('/monitoring/difficulties?minimum=1').json()['items'])==20
    assert [row[0] for row in rows[1:]]==[row['version_reference'] for row in report['items']]
    assert sum(row[0].startswith(f'Q{q.id}/') for row in rows[1:])==2
    assert any(row[1]=="'"+clue and row[3:5]==['2','2'] for row in rows[1:])
    assert any(row[1]=='Fila á\nsegunda;"línea"' for row in rows[1:])
    for row,expected in zip(rows[1:],report['items']):
        assert Decimal(row[-1].replace(',','.'))==Decimal(str(expected['error_percent']))
    assert response.headers['cache-control']=='no-store' and response.headers['x-content-type-options']=='nosniff'
    assert 'biogamed-dificultades.csv' in response.headers['content-disposition']
    assert client.get('/monitoring/difficulties.csv?minimum=2').headers['x-export-count']=='1'
    assert client.get('/monitoring/difficulties.csv?minimum=1&game=PASAPALABRA').headers['x-export-count']=='0'
    assert client.get('/monitoring/difficulties.csv?minimum=1&start=2026-07-01&end=2026-07-01').headers['x-export-count']=='26'
    empty=client.get('/monitoring/difficulties.csv?minimum=1&start=2026-07-02')
    assert len(list(csv.reader(io.StringIO(empty.content.decode('utf-8-sig')),delimiter=';')))==1
    for params in ['minimum=0','minimum=1.5','game=OTHER','start=2026-07-02&end=2026-07-01']:
        assert client.get('/monitoring/difficulties.csv?'+params).status_code==422
    monkeypatch.setattr(monitoring,'DIFFICULTIES_EXPORT_LIMIT',26)
    assert client.get('/monitoring/difficulties.csv?minimum=1').status_code==200
    monkeypatch.setattr(monitoring,'DIFFICULTIES_EXPORT_LIMIT',25)
    assert client.get('/monitoring/difficulties.csv?minimum=1').status_code==422
    payload=response.content.decode('utf-8-sig');assert '@test.invalid' not in payload and 'private solution' not in payload
