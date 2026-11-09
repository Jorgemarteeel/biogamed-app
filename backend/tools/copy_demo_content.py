"""Content-only import from an offline read-only export into a verified demo DB.

Never connects to the source. Default is a full transaction rolled back (dry run).
The dump/real restore must be verified separately before --apply. See docs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, select, text

TABLES = ("subjects", "content_blocks", "categories", "topics", "questions")
FOREIGN_KEYS = {"content_blocks": {"subject_id": "subjects"},
                "categories": {"block_id": "content_blocks"},
                "questions": {"topic_id": "topics", "category_id": "categories"}}
ALLOWED_OVERLAYS = {("categories", "block_id"), ("questions", "category_id")}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def guard(identity, source, expected_database, expected_system):
    if (identity["database"] != expected_database
            or identity["system_identifier"] != expected_system
            or not expected_database.startswith("demo_") and expected_database != "biogamed_demo"
            or identity["system_identifier"] == source["identity"]["system_identifier"]):
        raise ValueError("Destination is not the explicitly verified isolated demo cluster")
    if set(source["tables"]) != set(TABLES):
        raise ValueError("Only the five content tables are accepted")
    for rows in source["tables"].values():
        ids = [row["id"] for row in rows]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate source IDs")


def activity(conn):
    names = conn.execute(text("select tablename from pg_tables where schemaname='public' "
                              "and (tablename in ('users','game_engine_sessions','answer_logs') "
                              "or tablename like 'pasapalabra_%') order by tablename")).scalars()
    return {name: dict(conn.execute(text(
        "select count(*) as count, md5(coalesce(string_agg(md5(to_jsonb(x)::text),'' "
        "order by to_jsonb(x)::text),'')) as fingerprint from " + name + " x"
    )).mappings().one()) for name in names}


def run(conn, source, plan, expected_database, expected_system):
    identity = dict(conn.execute(text("select current_database() as database, "
        "(select system_identifier::text from pg_control_system()) as system_identifier")).mappings().one())
    guard(identity, source, expected_database, expected_system)
    # No DDL/writes before the identity/content guard. One lock for repeatable runs.
    conn.execute(text("select pg_advisory_xact_lock(728113604)"))
    before = activity(conn)
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS demo_import"))
    conn.execute(text("""CREATE TABLE IF NOT EXISTS demo_import.state (
        key text PRIMARY KEY, value jsonb NOT NULL)"""))
    def state_get(key):
        return conn.execute(text("select value from demo_import.state where key=:key"), {"key":key}).scalar()
    def state_put(key, value):
        conn.execute(text("insert into demo_import.state values (:key,cast(:value as jsonb)) "
            "on conflict (key) do update set value=excluded.value"), {"key":key,"value":json.dumps(value)})
    namespace = source["identity"]["system_identifier"] + ":" + source["identity"]["database"]
    state = state_get(namespace) or {"maps":{}, "objects":{}, "overlays":{}, "retired":{}}
    md = MetaData()
    tables = {name:Table(name, md, autoload_with=conn) for name in TABLES}
    def row(table, target_id):
        return dict(conn.execute(select(tables[table]).where(tables[table].c.id == target_id)).mappings().one())
    def insert(table, fields):
        return conn.execute(tables[table].insert().values(**fields).returning(tables[table].c.id)).scalar_one()
    def mapped(table, source_id):
        return state["maps"][table][str(source_id)]["target_id"] if source_id is not None else None
    inserted = {t:0 for t in TABLES}
    for name in TABLES:
        mapping = state["maps"].setdefault(name,{})
        for original in source["tables"][name]:
            if set(original) != {column.name for column in tables[name].columns}:
                raise ValueError("Source/target content columns differ: " + name)
            sid = str(original["id"])
            if sid in mapping:
                record = mapping[sid]
                if record["source_hash"] != digest(original) or record["target_hash"] != digest(row(name,record["target_id"])):
                    raise ValueError("Owned content changed; explicit reconciliation needed: " + name + ":" + sid)
                continue
            fields = {k:v for k,v in original.items() if k != "id"}
            for field,parent in FOREIGN_KEYS.get(name,{}).items():
                fields[field] = mapped(parent,fields[field])
            target_id = insert(name, fields)
            mapping[sid] = {"target_id":target_id,"source_hash":digest(original),"target_hash":digest(row(name,target_id))}
            inserted[name] += 1
    def object_id(key, name, fields):
        saved = state["objects"].get(key)
        if saved:
            if digest(row(name,saved["id"])) != saved["hash"]:
                raise ValueError("Provisional object changed: " + key)
            if {k:v for k,v in row(name,saved["id"]).items() if k!='id'} != fields:
                raise ValueError("Provisional specification changed: " + key)
            return saved["id"]
        target_id = insert(name,fields)
        state["objects"][key] = {"id":target_id,"table":name,"hash":digest(row(name,target_id))}
        return target_id
    def overlay(name, source_id, field, value):
        if (name,field) not in ALLOWED_OVERLAYS:
            raise ValueError("Unsupported provisional relation")
        record = state["maps"][name][str(source_id)]
        conn.execute(tables[name].update().where(tables[name].c.id==record["target_id"]).values(**{field:value}))
        state["overlays"][name+":"+str(source_id)+":"+field] = value
        record["target_hash"] = digest(row(name,record["target_id"]))
    if plan.get("organization"):
        org = plan["organization"]
        subject = object_id("subject", "subjects", {"name":org["name"],"description":org["description"]})
        original_categories = {c["id"]:c for c in source["tables"]["categories"]}
        original_questions = {q["id"]:q for q in source["tables"]["questions"]}
        assigned_categories,assigned_questions = set(),set()
        for block in org["blocks"]:
            bid = object_id("block:"+block["key"], "content_blocks", {"subject_id":subject,"name":block["name"],"description":block["description"]})
            for cid in block.get("source_categories",[]):
                if cid in assigned_categories or original_categories[cid]["block_id"] is not None:
                    raise ValueError("Cannot replace an official category relation")
                assigned_categories.add(cid)
                overlay("categories",cid,"block_id",bid)
            for category in block.get("categories",[]):
                cid = object_id("category:"+category["key"], "categories", {"block_id":bid,"name":category["name"],"description":category["description"]})
                for qid in category["source_question_ids"]:
                    if qid in assigned_questions or original_questions[qid]["category_id"] is not None or not original_questions[qid]["is_active"]:
                        raise ValueError("Cannot reclassify classified/retired questions")
                    assigned_questions.add(qid)
                    overlay("questions",qid,"category_id",cid)
    # Explicit ID + complete prior-row fingerprint, never a frontend/name filter.
    for technical in plan.get("retire_questions",[]):
        qid = technical["id"]
        key = str(qid)
        if any(m["target_id"] == qid for m in state["maps"]["questions"].values()):
            raise ValueError("A technical scenario collides with imported content")
        current = row("questions",qid)
        if digest(current) != state["retired"].get(key,technical["hash"]):
            raise ValueError("Technical scenario changed: " + key)
        conn.execute(tables["questions"].update().where(tables["questions"].c.id==qid).values(is_active=False))
        state["retired"][key] = digest(row("questions",qid))
    reverse = {t:{m["target_id"]:int(sid) for sid,m in mapping.items()} for t,mapping in state["maps"].items()}
    hashes = {}
    for name in TABLES:
        normalized = []
        for original in source["tables"][name]:
            sid = original["id"]
            target = row(name,mapped(name,sid))
            target["id"] = sid
            for field,parent in FOREIGN_KEYS.get(name,{}).items():
                key = name+":"+str(sid)+":"+field
                if key in state["overlays"]:
                    if target[field] != state["overlays"][key]:
                        raise ValueError("Provisional relation no longer matches")
                    target[field] = original[field]
                elif target[field] is not None:
                    target[field] = reverse[parent][target[field]]
            if digest(target) != digest(original):
                raise ValueError("Content verification failed: " + name+":"+str(sid))
            normalized.append(target)
        hashes[name] = {"count":len(normalized),"source":digest(source["tables"][name]),"target_normalized":digest(normalized)}
    after = activity(conn)
    if before != after:
        raise ValueError("Accounts or activity changed: rolling back")
    state_put(namespace,state)
    return {"destination":identity,"inserted":inserted,"verified_content":hashes,"activity_unchanged":before==after,
            "activity":after,"maps":state["maps"],"provisional_objects":state["objects"],"overlays":state["overlays"],
            "technical_questions_retired":len(state["retired"]),"provenance":plan.get("provenance",{})}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot",type=Path)
    parser.add_argument("plan",type=Path)
    parser.add_argument("--expected-database",required=True)
    parser.add_argument("--expected-system",required=True)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    if args.output.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError("Keep reports/content outside the repository")
    source=json.loads(args.snapshot.read_text(encoding="utf-8"))
    plan=json.loads(args.plan.read_text(encoding="utf-8"))
    engine=create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as conn:
        transaction=conn.begin()
        try:
            report=run(conn,source,plan,args.expected_database,args.expected_system)
            if args.apply: transaction.commit()
            else: transaction.rollback()
        except Exception:
            transaction.rollback()
            raise
    report["applied"]=args.apply
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"applied":args.apply,"inserted":report["inserted"],"activity_unchanged":report["activity_unchanged"],
                      "technical_questions_retired":report["technical_questions_retired"]}))

if __name__=="__main__":
    main()
