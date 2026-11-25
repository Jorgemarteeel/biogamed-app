"""Real PostgreSQL starts and enrollment serialization, on disposable schemas only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models import User, Subject, AcademicEdition, Enrollment, Topic, Question, GameSession
from app.models.pasapalabra import PasapalabraMatch, MatchQuestion
from app.schemas.pasapalabra import LocalStart
from app.services import pasapalabra as service
from app.services.user_onboarding import lock_users
from app.utils.security import get_password_hash
from test_user_onboarding import dni
from test_pasapalabra_postgres import postgres

PASSWORD="synthetic-postgres-password"
def bank(engine):
 with Session(engine) as db:
  s=Subject(name="Disposable subject",code="RACE");db.add(s);db.flush()
  years=[AcademicEdition(subject_id=s.id,academic_year=y) for y in ("2026-2027","2027-2028")];db.add_all(years);db.flush()
  t=Topic(name="Disposable theme",edition_id=years[0].id);db.add(t);db.flush()
  hashed=get_password_hash(PASSWORD)
  users=[User(name=f"Synthetic {i}",email=f"race-{i}@example.com",dni=dni(92000000+i),hashed_password=hashed) for i in range(2)]
  db.add_all(users);db.flush()
  db.add_all([Enrollment(student_id=u.id,subject_id=s.id,edition_id=years[0].id,play_enabled=True) for u in users])
  db.add_all([Question(text=f"Synthetic {n}",question_type="PASAPALABRA",topic_id=t.id,edition_id=years[0].id,subject_id=s.id,difficulty=1,letter="A",exact_word="Arteria",correct_answer="Arteria") for n in range(40)])
  db.commit()
  return users[0].id,users[1].id,years[0].id,years[1].id,LocalStart(operation_id=uuid4(),subject_id=s.id,topic_id=t.id,difficulty=1,guest_dni=users[1].dni,guest_password=PASSWORD)

def test_enrollment_start_retry_is_one_match_two_sessions_one_draw(postgres,monkeypatch):
 owner,guest,old,new,request=bank(postgres)
 barrier=Barrier(2);draws=[];sample=service.RNG.sample
 def draw(*args,**kwargs):draws.append(1);return sample(*args,**kwargs)
 monkeypatch.setattr(service.RNG,"sample",draw)
 def start(_):
  with Session(postgres) as db:
   actor=db.get(User,owner);barrier.wait(timeout=10)
   return service.start_local(db,actor,request)
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(start,[0,1]))
 assert results[0]["id"]==results[1]["id"] and len(draws)==1
 with Session(postgres) as db:
  assert db.scalar(select(func.count()).select_from(PasapalabraMatch))==1
  assert db.scalar(select(func.count()).select_from(GameSession))==2
  assert db.scalar(select(func.count()).select_from(MatchQuestion))==40

def test_start_waits_for_enrollment_change_and_rejects_old_theme(postgres):
 owner,guest,old,new,request=bank(postgres);entered=Event()
 with Session(postgres) as manager, ThreadPoolExecutor(max_workers=1) as pool:
  lock_users(manager)
  enrollment=manager.get(Enrollment,(owner,old));enrollment.play_enabled=False;manager.flush()
  manager.add(Enrollment(student_id=owner,subject_id=request.subject_id,edition_id=new,play_enabled=True))
  def start():
   with Session(postgres) as db:
    actor=db.get(User,owner);entered.set()
    try:return service.start_local(db,actor,request)
    except HTTPException as error:return error.status_code
  pending=pool.submit(start);assert entered.wait(timeout=10);manager.commit()
  assert pending.result(timeout=20)==409
 with Session(postgres) as db:assert db.scalar(select(func.count()).select_from(PasapalabraMatch))==0
