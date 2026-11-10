"""Explicit isolated-demo bootstrap; never a public registration path."""
import os
from sqlalchemy.engine import make_url
from sqlalchemy import select,text
from app.database import engine,SessionLocal
from app.models import User,UserRole
from app.utils.security import get_password_hash

def main():
    url=make_url(str(engine.url))
    if url.database!='biogamed_demo' or url.host!='db' or os.getenv('BIOGAMED_DEMO_PROVISION')!='1':raise RuntimeError('Refusing provisioning outside explicitly enabled isolated demo')
    password=os.environ['BIOGAMED_DEMO_ADMIN_PASSWORD']
    if len(password)<16:raise RuntimeError('Demo password too short')
    with SessionLocal() as db:
        assert db.scalar(text('select current_database()'))=='biogamed_demo'
        user=db.scalar(select(User).where(User.email=='admin-demo@example.com'))
        if user:
            if user.role!=UserRole.ADMIN:raise RuntimeError('Existing account must not be promoted by bootstrap')
            print('Existing demo administrator retained; no password change');return
        db.add(User(name='Administrador Demo',email='admin-demo@example.com',hashed_password=get_password_hash(password),role=UserRole.ADMIN));db.commit()
        print('Isolated demo administrator created')
if __name__=='__main__':main()
