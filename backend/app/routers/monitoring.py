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


EXPORT_LIMIT = 10000
FORMAT_LABELS = {
    "TRIVIAL-legacy": "Trivial · individual",
    "PASAPALABRA-legacy": "Pasapalabra · sesión individual",
    "pasapalabra-local-v1": "Pasapalabra · local (cuenta e invitado)",
    "pasapalabra-online-v1": "Pasapalabra · en línea (dos cuentas)",
}
STATUS_LABELS = {"NORMAL": "Finalizada", "ABANDONMENT": "Abandono", "OPEN": "Abierta registrada", "UNKNOWN": "Estado sin determinar"}


def csv_cell(value):
    if value is None:
        return ""
    text = str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def activity_csv(rows):
    import csv
    import io
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(["Referencia", "Fecha de inicio (Atlantic/Canary, ISO 8601 con desfase)", "Formato", "Estado", "Participantes registrados", "Invitados"])
    for row in rows:
        moment = row["started"]
        if moment is not None:
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)  # stored naive datetimes are UTC
            moment = moment.astimezone(ZoneInfo("Atlantic/Canary")).isoformat()
        code = row["format"]
        label = FORMAT_LABELS.get(f"{row['game']}-legacy" if code == "legacy" else code, "Formato no identificado")
        writer.writerow([csv_cell(v) for v in [row["key"], moment, label, STATUS_LABELS.get(row["status"], row["status"]), row["registered"], row["guests"]]])
    return output.getvalue().encode("utf-8-sig")


@router.get("/activity.csv")
def export_activity(start:date|None=None,end:date|None=None,game:str=Query("ALL",pattern="^(ALL|TRIVIAL|PASAPALABRA)$"),db:Session=Depends(get_db),staff:User=Depends(require_content_staff)):
    from fastapi.responses import Response
    # Exactly the same read-only query, filter rules, deduplication and rows as the screen.
    report = activity(start=start, end=end, game=game, skip=0, limit=EXPORT_LIMIT, db=db, staff=staff)
    if report["total"] > EXPORT_LIMIT:
        raise HTTPException(422, f"La exportación supera {EXPORT_LIMIT} registros. Acota las fechas y vuelve a consultar.")
    return Response(activity_csv(report["items"]), media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": 'attachment; filename="biogamed-seguimiento.csv"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        "X-Export-Count": str(report["total"]),
    })


@router.get("/difficulties")
def difficulties(start:date|None=None,end:date|None=None,game:str=Query("ALL",pattern="^(ALL|TRIVIAL|PASAPALABRA)$"),minimum:int=Query(5,ge=1,le=100000),skip:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),staff:User=Depends(require_content_staff)):
    from sqlalchemy import and_, or_, case, cast, Text
    from sqlalchemy.dialects.postgresql import JSONB
    if end == date.max: raise HTTPException(422,"Fecha final fuera de rango")
    lo,hi=bounds(start,end)
    # Restrict to registered sessions; a shared session must match its registered participant.
    moment=func.coalesce(PasapalabraMatch.created_at,GameSession.created_at)
    stmt=select(AnswerLog.id.label('answer_id'),AnswerLog.game_session_id,AnswerLog.question_id,GameSession.user_id,GameSession.game_mode,
        func.coalesce(GameSession.format_key,GameSession.game_mode+'-legacy').label('format'),
        AnswerLog.question_text,AnswerLog.question_type,AnswerLog.options,AnswerLog.letter,AnswerLog.correct_option_index,AnswerLog.exact_word,AnswerLog.accepted_answers,AnswerLog.selected_index,AnswerLog.text_answer,AnswerLog.is_correct,
        func.row_number().over(partition_by=(AnswerLog.game_session_id,AnswerLog.question_id),order_by=(AnswerLog.answered_at.desc(),AnswerLog.id.desc())).label('rank')
    ).join(GameSession,GameSession.id==AnswerLog.game_session_id).outerjoin(PasapalabraMatch,PasapalabraMatch.id==GameSession.shared_match_id).outerjoin(MatchParticipant,MatchParticipant.session_id==GameSession.id).where(or_(GameSession.shared_match_id.is_(None),and_(MatchParticipant.user_id==GameSession.user_id,MatchParticipant.match_id==GameSession.shared_match_id)))
    if lo: stmt=stmt.where(moment>=lo)
    if hi: stmt=stmt.where(moment<hi)
    if game!='ALL': stmt=stmt.where(GameSession.game_mode==game)
    ranked=stmt.subquery()
    r=ranked.c
    postgres=db.bind.dialect.name=='postgresql'
    def json_key(col): return cast(cast(col,JSONB),Text) if postgres else cast(col,Text)
    length=func.jsonb_array_length(cast(r.options,JSONB)) if postgres else func.json_array_length(r.options)
    # CASE prevents applying array length to incomplete historical JSON values.
    array_type=func.jsonb_typeof(cast(r.options,JSONB)) if postgres else func.json_type(r.options)
    size=case((array_type=='array',length),else_=0)
    valid=and_(r.rank==1,r.is_correct.is_not(None),r.question_type==r.game_mode,func.length(func.trim(r.question_text))>0,
        or_(and_(r.game_mode=='TRIVIAL',size>0,r.selected_index>=0,r.selected_index<size,r.correct_option_index>=0,r.correct_option_index<size,r.is_correct==(r.selected_index==r.correct_option_index)),
            and_(r.game_mode=='PASAPALABRA',r.text_answer.is_not(None),func.length(func.trim(r.exact_word))>0)))
    total=db.scalar(select(func.count()).select_from(ranked).where(r.rank==1)) or 0
    evaluated=db.scalar(select(func.count()).select_from(ranked).where(valid)) or 0
    keys=[r.question_id,r.game_mode,r.format,r.question_text,r.question_type,json_key(r.options),r.letter,r.correct_option_index,r.exact_word,json_key(r.accepted_answers)]
    grouped=select(r.question_id,r.game_mode,r.format,r.question_text,func.min(r.answer_id).label('copy_id'),func.count().label('evaluated'),func.count(func.distinct(r.user_id)).label('accounts'),func.sum(r.is_correct.cast(Integer)).label('correct'),func.sum(case((r.is_correct.is_(False),1),else_=0)).label('wrong')).where(valid).group_by(*keys).subquery()
    g=grouped.c
    eligible=select(grouped).where(g.evaluated>=minimum).subquery()
    e=eligible.c
    count=db.scalar(select(func.count()).select_from(eligible)) or 0
    items=[]
    for row in db.execute(select(eligible).order_by((e.wrong*1.0/e.evaluated).desc(),e.evaluated.desc(),e.question_id,e.format,e.copy_id).offset(skip).limit(limit)).mappings():
        items.append(dict(question_id=row['question_id'],version_reference=f"Q{row['question_id']}/C{row['copy_id']}",game=row['game_mode'],format=row['format'],format_label=FORMAT_LABELS.get(row['format'],'Formato no identificado'),text=row['question_text'],evaluated=row['evaluated'],accounts=row['accounts'],correct=row['correct'],wrong=row['wrong'],error_percent=100*row['wrong']/row['evaluated']))
    return dict(scope='platform',timezone='Atlantic/Canary',evaluated=evaluated,excluded_records=total-evaluated,total=count,items=items)
