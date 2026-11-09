from sqlalchemy import select
from app.models import Category, Subject, Question
from test_academic_selection import bank


def test_catalog_auth_hierarchy_metadata_and_empty(client, db, bank, auth_headers):
    selection,topics,users=bank
    base=f"/practice/subjects/{selection['subject_id']}/blocks/{selection['block_id']}"
    empty=Category(name='Vacía',block_id=selection['block_id'])
    db.add(empty);db.commit()
    assert client.get('/practice/subjects').status_code==401
    subjects=client.get('/practice/subjects',headers=auth_headers)
    assert subjects.status_code==200 and subjects.json()['items'][0]['id']==selection['subject_id']
    categories=client.get(base+'/categories',headers=auth_headers).json()['items']
    assert categories[0]['availability']=={'TRIVIAL':40,'PASAPALABRA':40}
    assert categories[1]['availability']=={'TRIVIAL':0,'PASAPALABRA':0}
    assert all(set(c)=={'id','name','description','availability'} for c in categories)
    assert 'correct_answer' not in str(categories) and 'exact_word' not in str(categories)
    q=db.scalar(select(Question).where(Question.question_type=='PASAPALABRA'));q.is_active=False;db.commit()
    detail=client.get(base+f"/categories/{selection['category_id']}",headers=auth_headers).json()
    assert detail['availability']['PASAPALABRA']==39
    assert detail['academic']['subject_id']==selection['subject_id']
    other=Subject(name='Ajena');db.add(other);db.commit()
    assert client.get(base.replace(f"subjects/{selection['subject_id']}",f'subjects/{other.id}')+'/categories',headers=auth_headers).status_code==404
    assert client.get(base+'/categories/999999',headers=auth_headers).status_code==404
    # Reading does not authorize staff question contracts.
    assert client.get('/subjects',headers=auth_headers).status_code==403


def test_catalog_stable_pagination_and_bounds(client,db,bank,auth_headers):
    selection,_,_=bank
    db.add_all([Subject(name=f'Pagination {i}') for i in range(15)]);db.commit()
    first=client.get('/practice/subjects?skip=0&limit=5',headers=auth_headers).json()['items']
    second=client.get('/practice/subjects?skip=5&limit=5',headers=auth_headers).json()['items']
    assert len(first)==len(second)==5
    assert max(x['id'] for x in first)<min(x['id'] for x in second)
    assert first==client.get('/practice/subjects?skip=0&limit=5',headers=auth_headers).json()['items']
    for query in ['skip=-1','limit=0','limit=101']:
        assert client.get('/practice/subjects?'+query,headers=auth_headers).status_code==422