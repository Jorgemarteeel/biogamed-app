from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from fastapi import HTTPException
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.models import User,UserRole
from app.models.role_change import RoleChange
from app.routers.users import change_role,RoleUpdate
from test_pasapalabra_postgres import postgres

def test_real_concurrent_admin_demotion_and_stale_target(postgres):
    with Session(postgres) as db:
        users=[User(name=n,email=n+'@example.com',hashed_password='unused',role=r) for n,r in [('A',UserRole.ADMIN),('B',UserRole.ADMIN),('T',UserRole.STUDENT)]];db.add_all(users);db.commit();a,b,t=[u.id for u in users]
    def race(jobs):
        barrier=Barrier(2)
        def run(job):
            actor,target,expected,new=job
            with Session(postgres) as db:
                db.get(User,actor);barrier.wait(timeout=10)
                try:change_role(db,actor,target,RoleUpdate(expected_role=expected,role=new));return 200
                except HTTPException as e:db.rollback();return e.status_code
        with ThreadPoolExecutor(2) as pool:return list(pool.map(run,jobs))
    assert sorted(race([(a,t,'student','teacher'),(b,t,'student','admin')]))==[200,409]
    # Restore a controlled population of exactly two administrators.
    with Session(postgres) as db:
        db.get(User,t).role=UserRole.STUDENT;db.commit()
    assert sorted(race([(a,b,'admin','student'),(b,a,'admin','student')]))==[200,403]
    with Session(postgres) as db:
        assert db.scalar(select(func.count()).select_from(User).where(User.role==UserRole.ADMIN))==1
        assert db.scalar(select(func.count()).select_from(RoleChange))==2
