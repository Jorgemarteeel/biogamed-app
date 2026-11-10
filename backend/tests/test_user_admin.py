from uuid import uuid4
from sqlalchemy import select
from app.main import app
from app.dependencies import get_current_user
from app.models import User,UserRole
from app.models.role_change import RoleChange
from app.utils.security import create_access_token

def make(db,name,role):
    u=User(name=name,email=name+'@example.com',hashed_password='unused',role=role);db.add(u);db.commit();return u

def test_permissions_registration_and_privacy(client,db):
    admin=make(db,'Admin',UserRole.ADMIN);student=make(db,'Student',UserRole.STUDENT);teacher=make(db,'Teacher',UserRole.TEACHER)
    assert client.get('/admin/users').status_code==401
    for actor in [student,teacher]:
        app.dependency_overrides[get_current_user]=lambda:actor
        assert client.get('/admin/users').status_code==403
        assert client.patch(f'/admin/users/{student.id}/role',json={'expected_role':'student','role':'admin'}).status_code==403
    app.dependency_overrides[get_current_user]=lambda:admin
    r=client.get('/admin/users?search=STUDENT&role=student&limit=1').json();assert r['total']==1
    assert set(r['items'][0])=={'id','name','email','role'}
    first=client.get('/admin/users?limit=2').json();last=client.get('/admin/users?limit=2&skip=2').json()
    assert first['total']==3 and len({u['id'] for u in first['items']+last['items']})==3
    assert client.get('/admin/users?search=%25').json()['total']==0
    assert client.get('/admin/users?role=other').status_code==422
    assert client.patch(f'/admin/users/{student.id}/role',json={'expected_role':'student','role':'root'}).status_code==422
    teacher.email='legacy@example.test';db.commit()
    changed=client.patch(f'/admin/users/{teacher.id}/role',json={'expected_role':'teacher','role':'student'})
    assert changed.status_code==200 and changed.json()['email']=='legacy@example.test'
    app.dependency_overrides.pop(get_current_user,None)
    payload={'name':'Public','email':'public@example.com','password':'test-only-password'}
    assert client.post('/auth/register',json={**payload,'role':'admin'}).status_code==422
    assert client.post('/auth/register',json=payload).json()['role']=='student'

def test_role_trace_conflict_and_old_token(client,db):
    a=make(db,'A',UserRole.ADMIN);b=make(db,'B',UserRole.ADMIN);target=make(db,'T',UserRole.STUDENT)
    token=create_access_token({'email':b.email,'sub':str(b.id),'role':'admin'})
    headers={'Authorization':'Bearer '+token}
    assert client.get('/admin/users',headers=headers).status_code==200
    app.dependency_overrides[get_current_user]=lambda:a
    assert client.patch(f'/admin/users/{a.id}/role',json={'expected_role':'admin','role':'student'}).status_code==403
    assert client.patch(f'/admin/users/{target.id}/role',json={'expected_role':'student','role':'teacher'}).status_code==200
    assert client.patch(f'/admin/users/{target.id}/role',json={'expected_role':'student','role':'admin'}).status_code==409
    event=db.scalar(select(RoleChange));assert (event.actor_id,event.target_id,event.previous_role,event.new_role)==(a.id,target.id,'student','teacher') and event.changed_at
    assert client.patch(f'/admin/users/{b.id}/role',json={'expected_role':'admin','role':'student'}).status_code==200
    app.dependency_overrides.pop(get_current_user,None)
    assert client.get('/admin/users',headers=headers).status_code==403
    assert client.get('/monitoring/activity',headers=headers).status_code==403
    assert client.patch(f'/admin/users/{target.id}/role',headers=headers,json={'expected_role':'teacher','role':'admin'}).status_code==403
