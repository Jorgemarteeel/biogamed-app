from copy import deepcopy
from collections import Counter
import pytest
from pydantic import ValidationError
from sqlalchemy import event,select,func
from app.models import UserRole,Question,Category,Subject,ContentBlock,Topic,GameSession,AnswerLog
from app.schemas.trivial_board import Board
from app.services.trivial_board import board


def test_original_definition_and_correction():
    b=board();assert len(b.cells)==140 and [c.id for c in b.cells]==list(range(1,141))
    assert Counter(c.level for c in b.cells)=={1:57,2:41,3:25,4:17}
    assert b.cells[13].source_label=='Jeriguinlla' and b.cells[13].label=='Jeringuilla' and b.cells[13].bank=='SYRINGE'
    assert sum(c.bank=='SPLEEN' for c in b.cells)==17
    assert b.effects['BRAIN'].status=='PENDING' and b.effects['BRAIN'].seconds is None
    assert b.effects['VIRUS'].move_delta==-3 and b.effects['DNA'].resolve_landing is True


@pytest.mark.parametrize('damage',['duplicate','order','level','kind','missing','bank','coordinates','brain','unknown_version','wrong_bank','wrong_effect'])
def test_invalid_board_rejected(damage):
    d=deepcopy(board().model_dump())
    if damage=='duplicate':d['cells'][1]['id']=1
    if damage=='order':d['cells'][2]['order']=4
    if damage=='level':d['cells'][57]['level']=1
    if damage=='kind':d['cells'][2]['kind']='DICE'
    if damage=='missing':d['cells']=d['cells'][:-1]
    if damage=='bank':d['cells'][7]['bank']='SPLEEN'
    if damage=='coordinates':d['cells'][1]['vertices'][0]['x']=-1
    if damage=='brain':d['effects']['BRAIN']['seconds']=240
    if damage=='wrong_bank':d['cells'][1]['bank']='FLASK'
    if damage=='wrong_effect':d['cells'][7]['kind']='DNA'
    if damage=='unknown_version':d['version']='unreviewed'
    with pytest.raises(ValidationError):Board.model_validate(d)


@pytest.fixture
def staff(test_user,db):
    test_user.role=UserRole.TEACHER;db.commit();return test_user


def test_permissions(client,auth_headers,test_user,db):
    assert client.get('/trivial-board').status_code==401
    for path in ['/trivial-board','/trivial-board/destinations?kind=topic']:
        assert client.get(path,headers=auth_headers).status_code==403
    assert client.post('/trivial-board/coverage',headers=auth_headers,json={}).status_code==403
    for role in [UserRole.TEACHER,UserRole.ADMIN]:
        test_user.role=role;db.commit();data=client.get('/trivial-board',headers=auth_headers)
        assert data.status_code==200 and data.json()['coverage']['can_start'] is False
        assert data.headers['cache-control']=='no-store'
    assert client.post('/trivial-board/start',headers=auth_headers,json={}).status_code in (404,405)


def add_question(db,topic,category,level=1,active=True,mode='TRIVIAL',fields=True):
    q=Question(topic_id=topic.id,category_id=category.id,text='PRIVATE QUESTION SHOULD NEVER LEAVE COVERAGE',correct_answer='PRIVATE SOLUTION',question_type=mode,is_active=active,difficulty=level,options=['uno','dos'] if fields else None,correct_option_index=0 if fields else None)
    db.add(q);return q


def test_explicit_filters_multi_topics_no_writes_and_privacy(client,auth_headers,staff,db,topic):
    other=Topic(name=topic.name);subject=Subject(name='Synthetic subject');db.add_all([other,subject]);db.flush()
    block=ContentBlock(name='Synthetic block',subject_id=subject.id);db.add(block);db.flush()
    category=Category(name='Unrelated category label',block_id=block.id);empty=Category(name='Linfocito');db.add_all([category,empty]);db.flush()
    add_question(db,topic,category,1);add_question(db,other,category,1);add_question(db,topic,category,2)
    add_question(db,topic,category,None);add_question(db,topic,category,1,active=False)
    add_question(db,topic,category,1,mode='PASAPALABRA');add_question(db,topic,category,1,fields=False)
    db.commit()
    calls=[]
    def capture(conn,cursor,statement,parameters,context,executemany):calls.append(statement.lstrip().split()[0].upper())
    event.listen(db.bind,'before_cursor_execute',capture)
    try:
        initial=client.get('/trivial-board',headers=auth_headers).json()['coverage']
        assert all(b['levels'] is None for b in initial['banks']) # no inference from Category.name
        result=client.post('/trivial-board/coverage',headers=auth_headers,json={'bindings':[{'bank':'LYMPHOCYTE','kind':'category','id':category.id},{'bank':'FLASK','kind':'topic','id':topic.id}]} )
        assert result.status_code==200;data=result.json();bank=data['banks'][0]
        assert [x['count'] for x in bank['levels']]==[2,1,0,0] and bank['unclassified']==1 and bank['total']==4
        assert bank['destination']['academic']['subject_id']==subject.id
        assert bank['destination']['academic']['block_id']==block.id
        assert data['overlaps']==[{'left':'LYMPHOCYTE','right':'FLASK','count':3}]
        assert data['can_start'] is False and data['sufficiency']=='UNDETERMINED' and data['bindings_persisted'] is False
        assert data['binding_version'] is None
        assert not any(x in result.text for x in ['PRIVATE QUESTION','PRIVATE SOLUTION','correct_option_index','question_ids','question_snapshot'])
        assert not {'INSERT','UPDATE','DELETE','CREATE','ALTER'} & set(calls)
    finally:event.remove(db.bind,'before_cursor_execute',capture)
    assert db.scalar(select(func.count()).select_from(GameSession))==0
    assert db.scalar(select(func.count()).select_from(AnswerLog))==0
    empty_result=client.post('/trivial-board/coverage',headers=auth_headers,json={'bindings':[{'bank':'LYMPHOCYTE','kind':'category','id':empty.id}]}).json()
    assert empty_result['banks'][0]['status']=='EMPTY' and empty_result['banks'][0]['total']==0


def test_destinations_pagination_and_invalid_bindings(client,auth_headers,staff,db):
    items=[Category(name='Same name'),Category(name='Same name')];db.add_all(items);db.commit()
    a=client.get('/trivial-board/destinations?kind=category&limit=1',headers=auth_headers).json()
    b=client.get('/trivial-board/destinations?kind=category&limit=1&skip=1',headers=auth_headers).json()
    assert a['total']==2 and a['items'][0]['id']<b['items'][0]['id'] and a['items'][0]['academic'] is None
    assert client.get('/trivial-board/destinations?kind=category&limit=101',headers=auth_headers).status_code==422
    value={'bank':'LYMPHOCYTE','kind':'category','id':items[0].id}
    for body in [{'bindings':[value,value]},{'bindings':[value|{'bank':'SPLEEN'}]},{'bindings':[value|{'id':True}]},{'bindings':[value|{'name':'guessed'}]},{'bindings':[value],'start':True}]:
        assert client.post('/trivial-board/coverage',headers=auth_headers,json=body).status_code==422
    assert client.post('/trivial-board/coverage',headers=auth_headers,json={'bindings':[value|{'id':99999}]}).status_code==404
