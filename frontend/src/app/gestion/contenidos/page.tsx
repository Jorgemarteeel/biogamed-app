"use client";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import Image from "next/image";
import { isAxiosError } from "axios";
import Brand from "@/components/Brand";
import ProfileMenu from "@/components/ProfileMenu";
import api, { getCurrentUser } from "@/services/api";

type Subject = {id:number;name:string};
type Edition = {id:number;subject_id:number;subject_name:string;academic_year:string};
type Topic = {id:number;name:string;description:string|null;icon:string|null};
type Slot = {bank:string;label:string;topic_id:number|null;missing_icon:boolean;decks:{level:number;count:number}[]};
type Overview = {subject:string;year:string;topics:Topic[];board:{slots:Slot[]}};
type Question = {id:number;question_type:string;text:string;difficulty:number;reference_answer:string|null;note_reference:string|null;letter:string|null;exact_word:string|null;accepted_answers:string[]|null;is_active:boolean};
type Preview = {subject:string;year:string;total:number;valid:number;proof:string|null;errors:{row:number;column:string;message:string}[];groups:{topic:string;game:string;count:number}[];preview:{row:number;topic:string;game:string;text:string;level:number}[]};
type RecoveryRef = { operation: string; edition: number; topic: number | null };
type RecoveryResult = { status: "unknown" | "confirmed"; count?: number; subject_id: number; subject: string; year: string; topic: string | null };
const recoveryKey = (userId: string) => "biogamed:edition-import:" + userId;
function readRecovery(userId: string): RecoveryRef | null {
  const raw = window.sessionStorage.getItem(recoveryKey(userId));
  if (!raw) return null;
  const value = JSON.parse(raw);
  if (!value || typeof value.operation !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value.operation) ||
      !Number.isSafeInteger(value.edition) || value.edition < 1 ||
      !(value.topic === null || (Number.isSafeInteger(value.topic) && value.topic > 0)) ||
      Object.keys(value).sort().join(",") !== "edition,operation,topic") {
    throw new Error("Referencia de importación inválida.");
  }
  return value;
}
const emptyQuestion = {question_type:"INMUNOQUEST",text:"",difficulty:1,reference_answer:"",note_reference:"",letter:"",exact_word:"",alternatives:""};
const boardSlotName: Record<string, string> = {LYMPHOCYTE:"Tipo de casilla 1",MACROPHAGE:"Tipo de casilla 2",SPLEEN:"Tipo de casilla 3",FLASK:"Tipo de casilla 4",DNA:"Tipo de casilla 5"};
const gameName = (game:string)=>game === "INMUNOQUEST" ? "Trivial" : "Pasapalabra";
function failure(err:unknown) {
  const detail = isAxiosError(err) ? err.response?.data?.detail : undefined;
  return typeof detail === "string" ? detail : err instanceof Error && !isAxiosError(err) ? err.message : Array.isArray(detail) ? detail.map(x=>x.msg).join(" · ") : "No se pudo completar la operación. Revisa los datos e inténtalo de nuevo.";
}
async function loadSubjects() {
  const items: Subject[] = [];
  for (let skip=0; ; skip+=100) {
    const {data}=await api.get<Subject[]>("/subjects?limit=100&skip="+skip);
    items.push(...data);
    if(data.length<100)return items;
  }
}
async function loadEditions() {
  const items: Edition[] = [];
  for (let skip=0; ; skip+=100) {
    const {data}=await api.get<{items:Edition[];has_more:boolean}>("/academic-editions?limit=100&skip="+skip);
    items.push(...data.items);
    if(!data.has_more)return items;
  }
}
export default function Contents() {
  const [userId,setUserId]=useState("");
  const [recoveryRef,setRecoveryRef]=useState<RecoveryRef|null>(null);
  const [recoveryResult,setRecoveryResult]=useState<RecoveryResult>();
  const [recoveryError,setRecoveryError]=useState("");
  const [recovering,setRecovering]=useState(false);
  const restore=useCallback(async(ref:RecoveryRef)=>{
    setRecoveryRef(ref);setRecovering(true);setRecoveryError("");
    try {
      const {data}=await api.get<RecoveryResult>("/edition-content/"+ref.edition+"/receipts/"+ref.operation,{params:ref.topic?{topic_id:ref.topic}:{}});
      setRecoveryResult(data);
    } catch(err) {
      setRecoveryResult(undefined);
      const status=isAxiosError(err)?err.response?.status:undefined;
      setRecoveryError(status===401?"Vuelve a iniciar sesión para consultar tu importación.":status===403?"Tu cuenta ya no tiene permisos para consultar esta importación.":"No se pudo consultar el resultado. La importación podría haberse guardado.");
    } finally {setRecovering(false);}
  },[]);
  const [allowed,setAllowed]=useState(false);
  const boardDirty=useRef(false);
  const [subjects,setSubjects]=useState<Subject[]>([]);
  const [editions,setEditions]=useState<Edition[]>([]);
  const [subject,setSubject]=useState("");
  const [edition,setEdition]=useState("");
  const [overview,setOverview]=useState<Overview>();
  const [topic,setTopic]=useState("");
  const [questions,setQuestions]=useState<{items:Question[];total:number}>();
  const [page,setPage]=useState(0);
  const [revision,setRevision]=useState(0);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const [pendingDestination,setPendingDestination]=useState<(()=>void)|null>(null);
  const [busy,setBusy]=useState(false);
  const [subjectName,setSubjectName]=useState("");
  const [year,setYear]=useState("");
  const [code,setCode]=useState("");
  const [topicName,setTopicName]=useState("");
  const [description,setDescription]=useState("");
  const [editingTopic,setEditingTopic]=useState<number|null>(null);
  const [draft,setDraft]=useState(emptyQuestion);
  const [editingQuestion,setEditingQuestion]=useState<number|null>(null);
  const [questionOpen,setQuestionOpen]=useState(false);
  const [importOpen,setImportOpen]=useState(false);
  const [file,setFile]=useState<File>();
  const [preview,setPreview]=useState<Preview>();
  const [previewPage,setPreviewPage]=useState(0);
  const [operation,setOperation]=useState("");
  const [mapping,setMapping]=useState<Record<string,number|null>>({});
  const [legacy,setLegacy]=useState<{total:number;items:{id:number;text:string;game:string;subject_id:number|null;block_id:number|null;category_id:number|null;topic_id:number|null}[]}>();
  const [legacyPage,setLegacyPage]=useState(0);
  const upload=useRef<HTMLInputElement>(null);
  const iconUpload=useRef<HTMLInputElement>(null);
  const selected=overview?.topics.find(t=>String(t.id)===topic);
  const base="/edition-content/"+edition;
  useEffect(()=>{
    getCurrentUser().then(user=>{
      if(user.role==="teacher"||user.role==="admin"){
        setAllowed(true);setUserId(user.id);
        try {const ref=readRecovery(user.id);if(ref)void restore(ref);}
        catch {setRecoveryError("El almacenamiento de sesión no está disponible o su referencia es inválida. No se ha reenviado ninguna importación.");}
      }else setError("Acceso exclusivo para docentes y administradores.");
    }).catch(err=>setError(failure(err)));
  },[restore]);
  useEffect(()=>{
    if(!allowed)return;
    let active=true;
    Promise.all([loadSubjects(),loadEditions()]).then(([subjects,editions])=>{
      if(active){setSubjects(subjects);setEditions(editions);}
    }).catch(err=>{if(active)setError(failure(err));});
    return()=>{active=false;};
  },[allowed,revision]);
  useEffect(()=>{
    if(!edition)return;
    let active=true;
    api.get<Overview>(base).then(({data})=>{if(active){setOverview(data);if(!boardDirty.current)setMapping(Object.fromEntries(data.board.slots.map(s=>[s.bank,s.topic_id])));}}).catch(err=>{if(active)setError(failure(err));});
    return()=>{active=false;};
  },[edition,base,revision]);
  useEffect(()=>{
    if(!topic||!edition)return;
    let active=true;
    api.get(base+"/questions",{params:{topic_id:topic,skip:page*20}}).then(({data})=>{if(active)setQuestions(data);}).catch(err=>{if(active)setError(failure(err));});
    return()=>{active=false;};
  },[topic,edition,base,page,revision]);
  async function act(action:()=>Promise<unknown>,success:string){
    if(busy)return;
    setBusy(true);setError("");setNotice("");
    try{const result=await action();setNotice(typeof result==="string"?result:success);setRevision(r=>r+1);}
    catch(err){setError(failure(err));}
    finally{setBusy(false);}
  }
  function loadUnassigned(page=0){
    return act(async()=>{
      const {data}=await api.get("/edition-content/legacy/pending",{params:{skip:page*20}});
      setLegacy(data);setLegacyPage(page);
    },"Listado actualizado.");
  }
  function resetImport(){setFile(undefined);setPreview(undefined);setOperation("");setPreviewPage(0);if(upload.current)upload.current.value="";}
  function changeDestination(action:()=>void){
    const proceed=()=>{
      boardDirty.current=false;action();setQuestions(undefined);setTopicName("");setDescription("");setEditingTopic(null);
      setDraft(emptyQuestion);setEditingQuestion(null);setQuestionOpen(false);setImportOpen(false);resetImport();setError("");setNotice("");
    };
    if((questionOpen&&draft.text)||topicName||(importOpen&&file)||boardDirty.current){
      setPendingDestination(()=>proceed);
      return;
    }
    proceed();
  }
  async function template(){
    await act(async()=>{
      const {data}=await api.get(base+"/template",{params:topic?{topic_id:topic}:{},responseType:"blob"});
      const url=URL.createObjectURL(data),a=document.createElement("a");a.href=url;a.download=topic?"preguntas-tematica.csv":"preguntas-edicion.csv";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    },"Plantilla preparada.");
  }
  async function importFile(confirm=false){
    if(!file)return;
    await act(async()=>{
      const form=new FormData();form.append("file",file);
      if(topic)form.append("topic_id",topic);
      if(confirm){
        const ref={operation,edition:Number(edition),topic:topic?Number(topic):null};
        try {window.sessionStorage.setItem(recoveryKey(userId),JSON.stringify(ref));}
        catch {throw new Error("No se puede guardar la referencia de recuperación. No se ha enviado la importación.");}
        setRecoveryRef(ref);setRecoveryResult(undefined);
        form.append("proof",preview!.proof!);form.append("operation_id",operation);
      }
      const {data}=await api.post(base+(confirm?"/confirm":"/validate"),form);
      if(confirm){await restore({operation,edition:Number(edition),topic:topic?Number(topic):null});resetImport();return "Importadas "+data.count+" preguntas. Abre la temática para consultar su listado.";}
      else{setPreview(data);setPreviewPage(0);setOperation(crypto.randomUUID());}
    },confirm?"Importación confirmada. Las preguntas aparecen en sus temáticas.":"Validación terminada. Revisa el resultado antes de confirmar.");
  }
  function questionPayload(){
    return {question_type:draft.question_type,text:draft.text,difficulty:Number(draft.difficulty),
      reference_answer:draft.question_type==="INMUNOQUEST"?draft.reference_answer:null,
      note_reference:draft.question_type==="INMUNOQUEST"?(draft.note_reference||null):null,
      letter:draft.question_type==="PASAPALABRA"?draft.letter:null,
      exact_word:draft.question_type==="PASAPALABRA"?draft.exact_word:null,
      accepted_answers:draft.question_type==="PASAPALABRA"?(draft.alternatives?draft.alternatives.split("\n"):[]):null};
  }
  async function saveQuestion(e:FormEvent){e.preventDefault();await act(async()=>{
    const path=base+"/topics/"+topic+"/questions";
    if(editingQuestion)await api.put(path+"/"+editingQuestion,questionPayload());else await api.post(path,questionPayload());
    setDraft(emptyQuestion);setEditingQuestion(null);setQuestionOpen(false);
  },"Pregunta guardada.");}
  const card="space-y-4 rounded-2xl border border-slate-200 bg-white p-5";
  return <div className="min-h-screen bg-background text-slate-900">
    <header className="site-header"><div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3"><Brand/><ProfileMenu/></div></header>
    <main className="mx-auto max-w-6xl space-y-5 px-5 py-6">
      <Link href="/dashboard" className="text-link">← Volver al panel</Link>
      <h1 className="text-3xl font-black text-blue-950">Contenidos</h1>
      {error&&<p role="alert" className="notice-error">{error}</p>}{notice&&<p role="status" className="notice-success">{notice}</p>}
      {(recoveryRef||recoveryError)&&<section className={card} aria-label="Resultado de importación">
        {recovering?<p role="status">Consultando la importación…</p>:recoveryResult?.status==="confirmed"?<>
          <h2 className="text-xl font-bold">Importación confirmada</h2>
          <p role="status">{recoveryResult.count} preguntas importadas · {recoveryResult.subject} · {recoveryResult.year.replace("-","–")}{recoveryResult.topic?" · "+recoveryResult.topic:""}</p>
          <button type="button" className="button-secondary" onClick={()=>changeDestination(()=>{
            setSubject(String(recoveryResult.subject_id));setEdition(String(recoveryRef!.edition));setOverview(undefined);setTopic(recoveryRef!.topic?String(recoveryRef!.topic):"");setPage(0);setRevision(r=>r+1);
          })}>Ver preguntas importadas</button>
        </>:<p role="status">{recoveryError||"Todavía no se puede acreditar el resultado. La confirmación podría seguir ejecutándose."}</p>}
        {recoveryRef&&<button type="button" className="button-secondary" disabled={recovering} onClick={()=>void restore(recoveryRef)}>Consultar de nuevo</button>}
      </section>}
      {pendingDestination&&<section role="alertdialog" aria-label="Cambiar destino" aria-describedby="discard-warning" className={card}>
        <p id="discard-warning">Hay cambios sin guardar. ¿Quieres descartarlos y cambiar de destino?</p>
        <div className="flex flex-wrap gap-3"><button type="button" className="button-primary" onClick={()=>{pendingDestination();setPendingDestination(null);}}>Descartar y cambiar</button>
        <button type="button" className="button-secondary" onClick={()=>setPendingDestination(null)}>Seguir editando</button></div>
      </section>}
      {allowed&&<>
      <section className={card}>
        <h2 className="text-xl font-bold">Asignatura y curso académico</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="form-label">Asignatura<select className="form-input" value={subject} disabled={busy} onChange={e=>changeDestination(()=>{setSubject(e.target.value);setEdition("");setOverview(undefined);setTopic("");})}>
            <option value="">Selecciona una asignatura</option>{subjects.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
          <label className="form-label">Curso académico<select className="form-input" value={edition} disabled={busy||!subject} onChange={e=>changeDestination(()=>{setEdition(e.target.value);setOverview(undefined);setTopic("");})}>
            <option value="">Selecciona un curso</option>{editions.filter(e=>String(e.subject_id)===subject).map(e=><option key={e.id} value={e.id}>{e.academic_year.replace("-","–")}</option>)}</select></label>
        </div>
        <details><summary className="cursor-pointer font-semibold">Crear asignatura</summary><form className="mt-3 flex flex-wrap gap-3" onSubmit={e=>{e.preventDefault();void act(async()=>{const {data}=await api.post("/subjects",{name:subjectName});setSubject(String(data.id));setSubjectName("");setEdition("");setTopic("");},"Asignatura creada.");}}>
          <label>Nombre<input className="form-input" value={subjectName} required maxLength={255} onChange={e=>setSubjectName(e.target.value)}/></label><button className="button-secondary" disabled={busy}>Crear asignatura</button></form></details>
        {subject&&<details><summary className="cursor-pointer font-semibold">Crear edición de esta asignatura</summary><form className="mt-3 flex flex-wrap gap-3" onSubmit={e=>{e.preventDefault();void act(async()=>{const {data}=await api.post("/academic-editions",{subject_id:Number(subject),subject_code:code||null,academic_year:year});setEdition(String(data.id));setTopic("");setYear("");setCode("");},"Edición creada.");}}>
          <label>Curso académico<input className="form-input" placeholder="2026-2027" value={year} required onChange={e=>setYear(e.target.value)}/></label>
          <label>Código de asignatura<input className="form-input" placeholder="Solo si es su primera edición" value={code} onChange={e=>setCode(e.target.value)}/></label>
          <button className="button-secondary" disabled={busy}>Crear edición</button></form></details>}
      </section>
      {overview&&<>
        <p className="rounded-xl sticky top-0 z-10 bg-blue-50 p-3 font-bold">{overview.subject} · {overview.year.replace("-","–")}{selected?" · "+selected.name:""}</p>
        <section className={card}>
          <h2 className="text-xl font-bold">Temáticas del curso</h2>
          <label className="form-label">Temática<select className="form-input" value={topic} onChange={e=>changeDestination(()=>{setTopic(e.target.value);setPage(0);})}>
            <option value="">Toda la edición · importar varias temáticas</option>{overview.topics.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
          <form className="space-y-3" onSubmit={e=>{e.preventDefault();void act(async()=>{
            const payload={name:topicName,description:description||null};
            const {data}=editingTopic?await api.put(base+"/topics/"+editingTopic,payload):await api.post(base+"/topics",payload);
            setTopic(String(data.id));setTopicName("");setDescription("");setEditingTopic(null);
          },"Temática guardada.");}}>
            <h3 className="font-bold">{editingTopic?"Editar temática":"Crear temática"}</h3>
            <label className="form-label">Nombre<input className="form-input" required maxLength={255} value={topicName} onChange={e=>setTopicName(e.target.value)}/></label>
            <label className="form-label">Descripción<textarea className="form-input" maxLength={5000} value={description} onChange={e=>setDescription(e.target.value)}/></label>
            <div className="flex flex-wrap gap-3"><button className="button-secondary" disabled={busy}>{editingTopic?"Guardar temática":"Crear temática"}</button>
            <button type="button" className="button-secondary" onClick={()=>{setEditingTopic(null);setTopicName("");setDescription("");}}>Cancelar</button></div>
          </form>
          {selected&&<div className="space-y-3 border-t border-slate-200 pt-3">
            <button className="button-secondary" onClick={()=>{setEditingTopic(selected.id);setTopicName(selected.name);setDescription(selected.description||"");}}>Editar {selected.name}</button>
            {selected.icon&&<Image unoptimized src={selected.icon} alt={"Icono de "+selected.name} width={96} height={96}/>}
            <input ref={iconUpload} className="hidden" aria-label="Icono PNG" type="file" accept="image/png" onChange={e=>{
              const f=e.target.files?.[0];if(f){void act(async()=>{const form=new FormData();form.append("file",f);await api.post(base+"/topics/"+topic+"/icon",form);},"Icono guardado.");}
            }}/>
            <button className="button-secondary" disabled={busy} onClick={()=>iconUpload.current?.click()}>{selected.icon?"Sustituir icono":"Subir icono"}</button>
            <p className="text-sm text-slate-600">PNG, hasta 512 KiB y 1024 × 1024 píxeles. El icono se usa en esta temática y curso.</p>
          </div>}
        </section>
        <section className={card}>
          <div className="flex flex-wrap gap-3">{selected&&<button className="button-secondary" onClick={()=>{setQuestionOpen(v=>!v);setImportOpen(false);}}>Crear pregunta</button>}
            <button className="button-secondary" onClick={()=>{setImportOpen(v=>!v);setQuestionOpen(false);}}>Importar CSV {selected?"en esta temática":"en esta edición"}</button></div>
          {questionOpen&&<form className="space-y-3" onSubmit={saveQuestion}>
            <h2 className="text-xl font-bold">{editingQuestion?"Editar pregunta":"Nueva pregunta"} · {selected?.name}</h2>
            <label className="form-label">Juego<select className="form-input" value={draft.question_type} disabled={editingQuestion!==null} onChange={e=>setDraft({...emptyQuestion,question_type:e.target.value})}><option value="INMUNOQUEST">Trivial</option><option value="PASAPALABRA">Pasapalabra</option></select></label>
            <label className="form-label">Nivel de dificultad<select className="form-input" value={draft.difficulty} onChange={e=>setDraft({...draft,difficulty:Number(e.target.value)})}>{[1,2,3,4].map(n=><option key={n}>{n}</option>)}</select></label>
            <label className="form-label">Enunciado<textarea className="form-input" required value={draft.text} onChange={e=>setDraft({...draft,text:e.target.value})}/></label>
            {draft.question_type==="INMUNOQUEST"?<>
              <label className="form-label">Respuesta de referencia<textarea className="form-input" required value={draft.reference_answer} onChange={e=>setDraft({...draft,reference_answer:e.target.value})}/></label>
              <label className="form-label">Referencia a apuntes (opcional)<input className="form-input" maxLength={120} value={draft.note_reference} onChange={e=>setDraft({...draft,note_reference:e.target.value})}/></label>
            </>:<>
              <label className="form-label">Letra<input className="form-input" required maxLength={1} value={draft.letter} onChange={e=>setDraft({...draft,letter:e.target.value})}/></label>
              <label className="form-label">Solución<input className="form-input" required value={draft.exact_word} onChange={e=>setDraft({...draft,exact_word:e.target.value})}/></label>
              <label className="form-label">Alternativas (una por línea)<textarea className="form-input" value={draft.alternatives} onChange={e=>setDraft({...draft,alternatives:e.target.value})}/></label>
            </>}
            <div className="flex gap-3"><button className="button-primary" disabled={busy}>Guardar pregunta</button><button className="button-secondary" type="button" onClick={()=>{setQuestionOpen(false);setDraft(emptyQuestion);setEditingQuestion(null);}}>Cancelar</button></div>
          </form>}
          {importOpen&&<div className="space-y-3">
            <h2 className="text-xl font-bold">Importar preguntas · {selected?.name||"Toda la edición"}</h2>
            <p>{selected?"La temática se fija aquí.":"Crea antes las temáticas y escribe su nombre exacto en cada fila."} En juego escribe Trivial o Pasapalabra. Cada fila indica dificultad 1–4 y enunciado. Trivial usa respuesta_referencia y referencia_apuntes opcional. Pasapalabra usa letra, solucion y alternativas opcionales, una por línea. Deja vacíos los campos del otro juego.</p>
            <p className="text-sm">CSV UTF-8, separador ;. Máximo 500 preguntas y 2 MiB. Validar no guarda preguntas.</p>
            <button className="button-secondary" disabled={busy} onClick={()=>void template()}>Descargar plantilla</button>
            <div className="flex flex-wrap items-center gap-3"><button className="button-secondary" disabled={busy} onClick={()=>upload.current?.click()}>Seleccionar archivo CSV</button>
              <span className="min-w-0 max-w-full break-all">{file?.name||"Ningún archivo seleccionado"}</span>
              <input ref={upload} type="file" className="hidden" aria-label="Archivo CSV" accept=".csv,text/csv" disabled={busy} onChange={e=>{const f=e.target.files?.[0];if(f){setFile(f);setPreview(undefined);setOperation("");}}}/></div>
            <button className="button-primary" disabled={busy||!file} onClick={()=>void importFile()}>Validar sin guardar</button>
            {preview&&<div className="space-y-3">
              <p role="status">{preview.subject} · {preview.year.replace("-","–")} · {preview.total} {preview.total===1?"pregunta":"preguntas"} · {preview.errors.length} {preview.errors.length===1?"error":"errores"}</p>
              {preview.errors.length>0&&<ul role="alert">{preview.errors.map((e,i)=><li key={i}>Fila {e.row} · {({difficulty:"Nivel de dificultad",dificultad:"Nivel de dificultad",tematica:"Temática",text:"Enunciado",reference_answer:"Respuesta de referencia"} as Record<string,string>)[e.column]||e.column} · {e.message}</li>)}</ul>}
              <ul>{preview.groups.map(g=><li key={g.topic+g.game}>{g.topic} · {gameName(g.game)} · {g.count} {g.count===1?"pregunta":"preguntas"}</li>)}</ul>
              <div className="overflow-x-auto"><table className="min-w-full text-left text-sm"><thead><tr>{["Fila","Temática","Juego","Nivel","Enunciado"].map(h=><th scope="col" key={h} className="p-2">{h}</th>)}</tr></thead>
                <tbody>{preview.preview.slice(previewPage*10,previewPage*10+10).map(r=><tr key={r.row}><td className="p-2">{r.row}</td><td className="p-2">{r.topic}</td><td className="p-2">{gameName(r.game)}</td><td className="p-2">{r.level}</td><td className="p-2">{r.text}</td></tr>)}</tbody></table></div>
              {preview.preview.length>10&&<div className="flex gap-3"><button className="button-secondary" disabled={!previewPage} onClick={()=>setPreviewPage(p=>p-1)}>Anterior</button><button className="button-secondary" disabled={(previewPage+1)*10>=preview.preview.length} onClick={()=>setPreviewPage(p=>p+1)}>Siguiente</button></div>}
              {preview.proof&&<button className="button-primary" disabled={busy} onClick={()=>void importFile(true)}>Confirmar importación</button>}
            </div>}
          </div>}
        </section>
        {selected&&<section className={card}>
          <h2 className="text-xl font-bold">Preguntas de {selected.name}</h2>
          {!questions&&<p role="status">Cargando preguntas…</p>}
          {questions?.total===0&&<p>Todavía no hay preguntas en esta temática.</p>}
          <ul className="divide-y divide-slate-200">{questions?.items.map(q=><li key={q.id} className="space-y-2 py-3">
            <p className="font-semibold">{q.text}</p><p>{gameName(q.question_type)} · Nivel {q.difficulty} · {q.is_active?"Activa":"Retirada"}</p>
            <div className="flex flex-wrap gap-3"><button className="button-secondary" onClick={()=>{setDraft({question_type:q.question_type,text:q.text,difficulty:q.difficulty,reference_answer:q.reference_answer||"",note_reference:q.note_reference||"",letter:q.letter||"",exact_word:q.exact_word||"",alternatives:q.accepted_answers?.join("\n")||""});setEditingQuestion(q.id);setQuestionOpen(true);setImportOpen(false);}}>Editar</button>
              <button className="button-secondary" disabled={busy} onClick={()=>void act(()=>api.patch(base+"/topics/"+topic+"/questions/"+q.id,null,{params:{active:!q.is_active}}),q.is_active?"Pregunta retirada.":"Pregunta reactivada.")}>{q.is_active?"Retirar":"Reactivar"}</button></div>
          </li>)}</ul>
          {questions&&questions.total>20&&<div className="flex gap-3"><button className="button-secondary" disabled={!page} onClick={()=>setPage(p=>p-1)}>Anterior</button><button className="button-secondary" disabled={(page+1)*20>=questions.total} onClick={()=>setPage(p=>p+1)}>Siguiente</button></div>}
        </section>}
        <section className={card}>
          <h2 className="text-xl font-bold">Contenido del tablero de Trivial</h2>
          <p>Asigna una temática distinta a cada tipo de casilla. Puedes guardar mientras lo completas. La tabla cuenta preguntas abiertas activas por nivel. No habilita partidas ni acredita suficiencia pedagógica.</p>
          <div className="overflow-x-auto"><table className="min-w-full text-left text-sm"><thead><tr>{["Casilla","Temática","Icono","Nivel 1","Nivel 2","Nivel 3","Nivel 4"].map(h=><th className="p-2" key={h} scope="col">{h}</th>)}</tr></thead>
            <tbody>{overview.board.slots.map(slot=><tr key={slot.bank}><th scope="row" className="p-2">{boardSlotName[slot.bank]||slot.label}</th>
              <td className="p-2"><select className="form-input min-w-40" aria-label={"Temática de "+(boardSlotName[slot.bank]||slot.label)} value={mapping[slot.bank]||""} onChange={e=>{boardDirty.current=true;setMapping({...mapping,[slot.bank]:e.target.value?Number(e.target.value):null});}}><option value="">Pendiente</option>{overview.topics.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select></td>
              <td className="p-2">{slot.missing_icon?"Falta icono":"Disponible"}</td>{slot.decks.map(d=><td key={d.level} className="p-2">{d.count}</td>)}</tr>)}</tbody></table></div>
          <button className="button-primary" disabled={busy} onClick={()=>void act(async()=>{await api.put(base+"/board",mapping);boardDirty.current=false;},"Configuración guardada.")}>Guardar configuración del tablero</button>
          <p className="text-sm">Los recuentos corresponden a la configuración guardada.</p>
        </section>
      </>}
      <section className={card}><h2 className="text-xl font-bold">Preguntas sin curso asignado</h2>
        <p>Son preguntas anteriores que aún no están vinculadas a un año académico. Revisa su procedencia para determinar el curso que les corresponde. Sus relaciones e historial se conservan.</p>
        <button className="button-secondary" disabled={busy} onClick={()=>void loadUnassigned()}>Ver preguntas sin curso asignado</button>
        {legacy&&<><p>{legacy.total} preguntas sin curso asignado</p><ul>{legacy.items.map(q=><li key={q.id} className="py-2">#{q.id} · {q.game==="INMUNOQUEST"?"Trivial":q.game==="TRIVIAL"?"Trivial individual":"Pasapalabra"} · {q.text}</li>)}</ul>
          <div className="flex gap-3"><button className="button-secondary" disabled={busy||!legacyPage} onClick={()=>void loadUnassigned(legacyPage-1)}>Página anterior</button><button className="button-secondary" disabled={busy||(legacyPage+1)*20>=legacy.total} onClick={()=>void loadUnassigned(legacyPage+1)}>Página siguiente</button></div></>}
      </section>
      </>}
    </main>
  </div>;
}
