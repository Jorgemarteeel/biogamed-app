from datetime import timedelta
import pytest
from sqlalchemy import select
from app.models import User,UserRole,GameSession
from app.utils.security import get_password_hash,verify_password,pwd_context,create_access_token

NEW='ñ'*72+' Contraseña nueva con sufijo único 🔬'

def request(password=NEW,current='test-password-123'):
    return dict(current_password=current,new_password=password,confirmation=password)

@pytest.mark.parametrize('role',[UserRole.STUDENT,UserRole.TEACHER,UserRole.ADMIN])
def test_own_name_permissions_and_history(client,db,test_user,auth_headers,role):
    test_user.role=role
    history=GameSession(user_id=test_user.id,topic_id=None,question_ids=[],score=0,is_completed=False,content_context={'saved':'Original'})
    db.add(history);db.commit()
    assert client.patch('/auth/me',json={'name':'A'}).status_code==401
    result=client.patch('/auth/me',json={'name':'  Nombre ñ revisado  '},headers=auth_headers)
    assert result.status_code==200 and result.json()['name']=='Nombre ñ revisado'
    assert set(result.json())=={'id','name','email','role'}
    for body in [{'name':' '},{'name':'x'*256},{'name':'A','role':'admin'},{'name':'A','email':'x@example.com'},{'name':'A','id':str(test_user.id)}]:
        assert client.patch('/auth/me',json=body,headers=auth_headers).status_code==422
    db.refresh(history);assert history.content_context=={'saved':'Original'}


def test_long_passwords_and_legacy_compatibility():
    legacy=pwd_context.hash('x'*72+'A')
    assert verify_password('x'*72+'B',legacy)  # Preserve unavoidable old bcrypt semantics.
    for value in ['x'*72+'A','ñ'*36+'A','🔬'*255]:
        hashed=get_password_hash(value);assert hashed.startswith('$argon2id$')
        assert verify_password(value,hashed) and not verify_password(value[:-1]+'B',hashed)
    with pytest.raises(ValueError):get_password_hash('x'*256)
    assert not verify_password('x'*256,legacy)


def test_password_validation_and_revocation(client,db,test_user,auth_headers):
    legacy=create_access_token({'email':test_user.email})
    tokens=[auth_headers,{'Authorization':'Bearer '+legacy}]
    assert client.post('/auth/me/password',json=request()).status_code==401
    for body,status in [(request(current='wrong'),400),(request()|{'confirmation':'different-password'},422),(request('short'),422),(request()|{'role':'admin'},422)]:
        assert client.post('/auth/me/password',json=body,headers=auth_headers).status_code==status
        assert client.get('/auth/me',headers=auth_headers).status_code==200
    assert client.post('/auth/me/password',json=request(),headers=auth_headers).status_code==200
    for h in tokens:
        for path in ['/auth/me','/game/history','/subjects','/admin/users','/pasapalabra/matches/1','/pasapalabra/rooms/00000000-0000-4000-8000-000000000001']:
            assert client.get(path,headers=h).status_code==401
    assert client.post('/auth/login',data={'username':test_user.email,'password':'test-password-123'}).status_code==401
    login=client.post('/auth/login',data={'username':test_user.email,'password':NEW})
    assert login.status_code==200
    current={'Authorization':'Bearer '+login.json()['access_token']}
    assert client.get('/auth/me',headers=current).status_code==200
    assert client.post('/auth/me/password',json=request('Otra nueva contraseña larga 🔬',NEW),headers=current).status_code==200
    assert client.get('/auth/me',headers=current).status_code==401
    assert client.get('/auth/me',headers=tokens[1]).status_code==401


def test_registration_unicode_limits_and_no_privileges(client,db):
    for value in ['ñ'*36+'A','🔬'*255]:
        email=f'u{len(value)}@example.com'
        response=client.post('/auth/register',json={'name':'  Nombre  ','email':email,'password':value})
        assert response.status_code==201 and response.json()['role']=='student' and response.json()['name']=='Nombre'
        assert client.post('/auth/login',data={'username':email,'password':value}).status_code==200
        assert client.post('/auth/login',data={'username':email,'password':value[:-1]+'B'}).status_code==401
    assert client.post('/auth/register',json={'name':'A','email':'bad@example.com','password':'x'*256}).status_code==422
    assert client.post('/auth/register',json={'name':'A','email':'bad@example.com','password':'12345678','role':'admin'}).status_code==422


def test_legacy_login_and_atomic_rollback(client,db,test_user,auth_headers,monkeypatch):
    original=pwd_context.hash('test-password-123');test_user.hashed_password=original;db.commit()
    assert client.post('/auth/login',data={'username':test_user.email,'password':'test-password-123'}).status_code==200
    db.refresh(test_user);assert test_user.hashed_password==original
    def fail():raise RuntimeError('controlled database failure')
    with monkeypatch.context() as m:
        m.setattr(db,'commit',fail)
        with pytest.raises(RuntimeError):client.post('/auth/me/password',json=request(),headers=auth_headers)
    db.refresh(test_user);assert test_user.auth_version==0 and test_user.hashed_password==original
    assert client.get('/auth/me',headers=auth_headers).status_code==200
