from uuid import uuid4
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from app.models import Subject, ContentBlock, Category, Topic, Question, GameSession, User
from app.models.pasapalabra import MatchQuestion
from app.schemas.pasapalabra import LocalStart, Selection, RoomCreate, RoomJoin, RoomAction
from app.schemas.game import UserAnswer
from app.services import game, pasapalabra as engine, pasapalabra_rooms as rooms

@pytest.fixture
def bank(db):
    subject=Subject(name='Asignatura real')
    db.add(subject); db.flush()
    block=ContentBlock(name='Bloque',subject_id=subject.id)
    db.add(block); db.flush()
    cat=Category(name='Categoria',block_id=block.id)
    topics=[Topic(name='A'),Topic(name='B')]
    users=[User(name=str(i),email=f'academic{i}@example.test',hashed_password='unused') for i in range(2)]
    db.add_all([cat,*topics,*users]);db.flush()
    for mode in ['TRIVIAL','PASAPALABRA']:
        for i in range(40):
            db.add(Question(topic_id=topics[i%2].id,category_id=cat.id,difficulty=2,question_type=mode,text=f'{mode} {i}',correct_answer='A',options=['A','B'] if mode=='TRIVIAL' else None,correct_option_index=0 if mode=='TRIVIAL' else None,letter='A' if mode=='PASAPALABRA' else None,exact_word='A' if mode=='PASAPALABRA' else None))
    db.commit()
    return dict(subject_id=subject.id,block_id=block.id,category_id=cat.id,difficulty=2),topics,users

def test_trivial_multi_topic_snapshot_correction_history(db,bank):
    selection,topics,users=bank
    # Two questions ensure both sources are selected deterministically.
    qs=list(db.scalars(select(Question).where(Question.question_type=='TRIVIAL').order_by(Question.id)))
    for q in qs[2:]:q.is_active=False
    db.commit()
    state=game.start_game_session(db,users[0],topic_id=None,**selection)
    assert state.topic_id is None and len(state.questions)==2
    stored=db.get(GameSession,state.session_id)
    assert {q['topic_id'] for q in stored.question_snapshot['questions']}=={t.id for t in topics}
    assert 'correct_option_index' not in state.model_dump()['questions'][0]
    qs[0].correct_option_index=1
    qs[0].category_id=None
    qs[0].topic_id=topics[1].id
    db.get(Subject,selection["subject_id"]).name="Nombre cambiado"
    db.commit()
    result=game.submit_game_session(db,users[0],state.session_id,[UserAnswer(question_id=q.id,selected_index=0) for q in state.questions])
    assert result.score==2
    assert stored.content_context['academic']['subject_name']=='Asignatura real'
    history=game.get_game_history_detail(db,users[0],state.session_id)
    assert history.content_context['academic']['subject_id']==selection['subject_id']
    assert game.get_game_progress(db,users[0])['best_marks'][0]['topic_id'] is None
    with pytest.raises(HTTPException):game.get_game_history_detail(db,users[1],state.session_id)

@pytest.mark.parametrize('count',[39,40])
def test_pasapalabra_limits_retry_and_scope(db,bank,count):
    selection,topics,users=bank
    if count==39:
        q=db.scalar(select(Question).where(Question.question_type=='PASAPALABRA'));q.is_active=False;db.commit()
    request=LocalStart(**selection,guest_name='Invitado',operation_id=uuid4())
    assert engine.prepare(db,request)['available']==count
    if count==39:
        with pytest.raises(HTTPException) as err:engine.start_local(db,users[0],request)
        assert err.value.detail['code']=='INSUFFICIENT_QUESTIONS';return
    state=engine.start_local(db,users[0],request)
    assert engine.start_local(db,users[0],request)['id']==state['id']
    assigned=list(db.scalars(select(MatchQuestion)))
    assert len({q.question_id for q in assigned})==40
    assert {q.snapshot['topic_id'] for q in assigned}=={t.id for t in topics}
    assert all(q.snapshot['classification']['category_id']==selection['category_id'] for q in assigned)
    assert set(state['academic'])=={'subject_id','subject_name','block_id','block_name','category_id','category_name'}

def test_online_configuration_and_start(db,bank):
    selection,topics,users=bank
    room=rooms.create(db,users[0],RoomCreate(**selection,operation_id=uuid4()))
    assert room['configuration']['topic'] is None
    assert room['configuration']['academic']['category_id']==selection['category_id']
    room=rooms.join(db,users[1],RoomJoin(code=room['code'],operation_id=uuid4()))
    for u in users:room=rooms.action(db,u,room['id'],'ready',RoomAction(operation_id=uuid4(),expected_version=room['version']))
    room=rooms.action(db,users[0],room['id'],'start',RoomAction(operation_id=uuid4(),expected_version=room['version']))
    assert room['match_id'] and all(s.topic_id is None for s in db.scalars(select(GameSession)))

def test_hierarchy_contradictions_and_filters(db,bank):
    selection,topics,users=bank
    with pytest.raises(ValueError):Selection(**selection,topic_id=topics[0].id)
    with pytest.raises(ValueError):Selection(category_id=selection['category_id'])
    with pytest.raises(HTTPException):engine.prepare(db,Selection(**{**selection,'block_id':99999}))
    assert engine.prepare(db,Selection(**{**selection,'difficulty':3}))['available']==0
    assert engine.prepare(db,Selection(**{k:v for k,v in selection.items() if k!='difficulty'},difficulty_unknown=True))['available']==0

def test_http_auth_and_safe_contract(client,db,bank,auth_headers):
    selection,topics,users=bank
    assert client.post('/game/academic/start',json=selection).status_code==401
    assert client.post('/game/academic/start',json={**selection,'subject_id':99999},headers=auth_headers).status_code==404
    response=client.post('/game/academic/start',json=selection,headers=auth_headers)
    assert response.status_code==201,response.text
    assert len(response.json()['questions'])==10
    assert 'correct_option_index' not in response.text and 'exact_word' not in response.text
    assert client.post('/game/academic/preparations',json=selection,headers=auth_headers).json()['total_questions']==40

def test_other_categories_unclassified_and_unknown_difficulty(db,bank):
    selection,topics,users=bank
    other=Category(name='Otra',block_id=selection['block_id'])
    db.add(other);db.flush()
    for category,level in [(None,2),(other.id,2),(selection['category_id'],None)]:
        db.add(Question(topic_id=topics[0].id,category_id=category,difficulty=level,question_type='PASAPALABRA',text='Extra',letter='A',exact_word='A',correct_answer='A'))
    db.commit()
    assert engine.prepare(db,Selection(**selection))['available']==40
    base={k:v for k,v in selection.items() if k!='difficulty'}
    assert engine.prepare(db,Selection(**base))['available']==41
    assert engine.prepare(db,Selection(**base,difficulty_unknown=True))['available']==1
    subject=Subject(name='Otra asignatura');db.add(subject);db.commit()
    with pytest.raises(HTTPException):engine.prepare(db,Selection(**{**selection,'subject_id':subject.id}))


def test_room_context_is_saved_and_request_retry_payload_is_legacy_compatible(db,bank):
    selection,topics,users=bank
    request=RoomCreate(**selection,operation_id=uuid4())
    room=rooms.create(db,users[0],request)
    category=db.get(Category,selection['category_id']);category.name='Nombre posterior';db.commit()
    assert rooms.create(db,users[0],request)['configuration']['academic']['category_name']=='Categoria'
    room=rooms.join(db,users[1],RoomJoin(code=room['code'],operation_id=uuid4()))
    for u in users:room=rooms.action(db,u,room['id'],'ready',RoomAction(operation_id=uuid4(),expected_version=room['version']))
    room=rooms.action(db,users[0],room['id'],'start',RoomAction(operation_id=uuid4(),expected_version=room['version']))
    assert engine.read_state(db,users[1],room['match_id'])['academic']['category_name']=='Categoria'
    from app.services.content_selection import selection_dump
    old=LocalStart(topic_id=topics[0].id,guest_name='Invitado',operation_id=uuid4())
    assert set(selection_dump(old,exclude={'operation_id','guest_name'}))=={'topic_id','category_id','difficulty','difficulty_unknown'}


def test_corrupt_academic_snapshot_classification_rejected(db,bank):
    selection,topics,users=bank
    state=game.start_game_session(db,users[0],topic_id=None,**selection)
    stored=db.get(GameSession,state.session_id)
    context=dict(stored.content_context)
    context['academic']={'subject_id':None}
    stored.content_context=context;db.commit()
    with pytest.raises(HTTPException) as err:
        game.submit_game_session(db,users[0],state.session_id,[UserAnswer(question_id=q.id,selected_index=0) for q in state.questions])
    assert err.value.status_code==409
    assert not db.get(GameSession,state.session_id).is_completed
