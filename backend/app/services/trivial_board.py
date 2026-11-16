"""Board metadata and coverage only. No game creation, RNG, clocks or DB writes."""
from functools import lru_cache
from pathlib import Path
from itertools import combinations
from fastapi import HTTPException
from sqlalchemy import select, func
from app.models import Category, Topic, Question
from app.schemas.trivial_board import Board, CoverageRequest
from app.services.game_questions import playable_question_filter

BANKS = [('LYMPHOCYTE','Linfocito'), ('MACROPHAGE','Macrófago'), ('SPLEEN','Bazo'), ('FLASK','Erlenmeyer'), ('SYRINGE','Jeringuilla')]
PENDING = [
    {'code':'BAZO_PENDING','message':'Banco Bazo pendiente de confirmación; no se sustituye.'},
    {'code':'BRAIN_PENDING','message':'Composición y reglas del reto Cerebro pendientes.'},
    {'code':'CORRECT_TURN_PENDING','message':'Continuidad del turno tras acertar pendiente.'},
    {'code':'PARTICIPANTS_PENDING','message':'Participantes e identidad pendientes de definición.'},
    {'code':'EXHAUSTION_PENDING','message':'Reutilización y agotamiento de preguntas pendientes.'},
    {'code':'EXIT_PENDING','message':'Abandono y desconexión pendientes de definición.'},
]

@lru_cache(maxsize=1)
def board():
    return Board.model_validate_json((Path(__file__).resolve().parents[1]/'data/trivial_board_v1.json').read_text(encoding='utf-8'))

def destination(db, kind, ident):
    if kind == 'topic':
        item = db.get(Topic, ident)
        if item is None: raise HTTPException(404, 'La temática seleccionada no existe.')
        return {'kind':kind,'id':item.id,'name':item.name,'academic':None}
    item = db.get(Category, ident)
    if item is None: raise HTTPException(404, 'La categoría seleccionada no existe.')
    academic = None
    if item.block is not None:
        academic = {'block_id':item.block.id,'block_name':item.block.name,'subject_id':item.block.subject.id,'subject_name':item.block.subject.name}
    return {'kind':kind,'id':item.id,'name':item.name,'academic':academic}

def eligible(binding):
    column = Question.category_id if binding.kind == 'category' else Question.topic_id
    return select(Question.id,Question.difficulty).where(playable_question_filter('TRIVIAL'),column == binding.id)

def coverage(db, request: CoverageRequest):
    chosen = {b.bank:b for b in request.bindings}
    result=[];blockers=[dict(x) for x in PENDING];subqueries={}
    for key,name in BANKS:
        b=chosen.get(key)
        row={'key':key,'name':name,'status':'PENDING' if key=='SPLEEN' else 'UNBOUND','destination':None,'levels':None,'unclassified':None,'total':None}
        if b:
            row['destination']=destination(db,b.kind,b.id)
            q=eligible(b).subquery();subqueries[key]=q
            counts=dict(db.execute(select(q.c.difficulty,func.count()).group_by(q.c.difficulty)).all())
            row.update(status='COUNTS_AVAILABLE' if sum(counts.values()) else 'EMPTY',levels=[{'level':n,'count':counts.get(n,0)} for n in range(1,5)],unclassified=counts.get(None,0),total=sum(counts.values()))
            for level in row['levels']:
                if level['count']==0:blockers.append({'code':'NO_QUESTIONS_AT_LEVEL','bank':key,'level':level['level'],'message':f"{name}: sin preguntas elegibles de nivel {level['level']}."})
        elif key!='SPLEEN':
            blockers.append({'code':'BANK_UNBOUND','bank':key,'message':f'{name}: falta una vinculación explícita.'})
        result.append(row)
    overlaps=[]
    for left,right in combinations(subqueries,2):
        a,b=subqueries[left],subqueries[right]
        count=db.scalar(select(func.count()).select_from(a.join(b,a.c.id==b.c.id)))
        if count:overlaps.append({'left':left,'right':right,'count':count})
    return {'board_version':board().version,'binding_version':None,'bindings_persisted':False,'can_start':False,'sufficiency':'UNDETERMINED','banks':result,'blockers':blockers,'overlaps':overlaps}

def options(db,kind,skip,limit):
    model=Category if kind=='category' else Topic
    ids=list(db.scalars(select(model.id).order_by(model.id).offset(skip).limit(limit)))
    return {'items':[destination(db,kind,i) for i in ids],'total':db.scalar(select(func.count()).select_from(model)),'skip':skip,'limit':limit}
