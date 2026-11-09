"""Global staff-only stored activity; no reconciliation or game mutations."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, Integer
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_content_staff
from app.models import User, GameSession, AnswerLog
from app.models.pasapalabra import PasapalabraMatch, MatchParticipant

router=APIRouter(prefix="/monitoring",tags=["Monitoring"])

def bounds(start,end):
    if start and end and start>end:raise HTTPException(422,"El inicio no puede ser posterior al fin")
    tz=ZoneInfo("Atlantic/Canary")
    return (datetime.combine(start,time.min,tz).astimezone(timezone.utc) if start else None,
            datetime.combine(end+timedelta(days=1),time.min,tz).astimezone(timezone.utc) if end and end<date.max else None)

@router.get("/activity")
def activity(start:date|None=None,end:date|None=None,game:str=Query("ALL",pattern="^(ALL|TRIVIAL|PASAPALABRA)$"),skip:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),staff:User=Depends(require_content_staff)):
    if end==date.max:raise HTTPException(422,"Fecha final fuera de rango")
    lo,hi=bounds(start,end)
    def filtered(stmt,col,mode=None):
        if lo:stmt=stmt.where(col>=lo)
        if hi:stmt=stmt.where(col<hi)
        if mode is not None and game!="ALL":stmt=stmt.where(mode==game)
        return stmt
    # Explicit public-safe columns: never load question snapshots or response contents.
    sessions=db.execute(select(GameSession.id,GameSession.user_id,GameSession.shared_match_id,GameSession.created_at,GameSession.game_mode,GameSession.format_key,GameSession.is_completed,GameSession.wrong_count,GameSession.pending_count,GameSession.question_ids)).mappings().all()
    stmt=filtered(select(PasapalabraMatch.id,PasapalabraMatch.created_at,PasapalabraMatch.status,PasapalabraMatch.outcome,PasapalabraMatch.rules_version),PasapalabraMatch.created_at)
    matches=db.execute(stmt).mappings().all() if game!="TRIVIAL" else []
    ids={m['id'] for m in matches}
    standalone=db.execute(filtered(select(GameSession.id,GameSession.created_at,GameSession.game_mode,GameSession.is_completed),GameSession.created_at,GameSession.game_mode).where(GameSession.shared_match_id.is_(None))).mappings().all()
    rows=[dict(key=f"match:{m['id']}",started=m['created_at'],game="PASAPALABRA",format=m['rules_version'],status="NORMAL" if m['status']=="FINISHED" and m['outcome']=="NORMAL" else "ABANDONMENT" if m['outcome']=="ABANDONMENT" else "OPEN" if m['status']=="RUNNING" else "UNKNOWN") for m in matches]
    rows += [dict(key=f"session:{s['id']}",started=s['created_at'],game=s['game_mode'],format="legacy",status="NORMAL" if s['is_completed'] else "UNKNOWN") for s in standalone]
    singleids={s['id'] for s in standalone}
    relevant=[s for s in sessions if s['shared_match_id'] in ids or s['id'] in singleids]
    users={str(s['user_id']) for s in relevant}
    tallies={x[0]:(x[1],x[2]) for x in db.execute(select(AnswerLog.game_session_id,func.count(),func.sum(AnswerLog.is_correct.cast(Integer))).where(AnswerLog.game_session_id.in_([s['id'] for s in relevant])).group_by(AnswerLog.game_session_id))}
    groups={}
    for s in relevant:
        key=s['format_key'] or s['game_mode']+"-legacy"
        g=groups.setdefault(key,dict(format=key,sessions=0,correct=0,wrong=0,pending=0,unknown_sessions=0))
        g['sessions']+=1
        total,correct=tallies.get(s['id'],(0,0));g['correct']+=correct or 0;g['wrong']+=total-(correct or 0)
        if s['shared_match_id'] is not None and s['pending_count'] is not None:g['pending']+=s['pending_count']
        elif not s['is_completed'] or total!=len(s['question_ids']):g['unknown_sessions']+=1
    roster=db.execute(select(MatchParticipant.match_id,MatchParticipant.user_id).where(MatchParticipant.match_id.in_(ids))).all()
    for row in rows:
        if row['key'].startswith('match:'):
            mid=int(row['key'].split(':')[1]);people=[p for p in roster if p[0]==mid]
            row['registered']=sum(p[1] is not None for p in people);row['guests']=sum(p[1] is None for p in people)
        else:row['registered']=1;row['guests']=0
    rows.sort(key=lambda x:(str(x['started']),x['key']),reverse=True)
    return dict(scope="platform",timezone="Atlantic/Canary",unique_registered=len(users),started=len(rows),normal=sum(r['status']=="NORMAL" for r in rows),abandoned=sum(r['status']=="ABANDONMENT" for r in rows),open=sum(r['status']=="OPEN" for r in rows),unknown=sum(r['status']=="UNKNOWN" for r in rows),groups=list(groups.values()),total=len(rows),items=rows[skip:skip+limit])
