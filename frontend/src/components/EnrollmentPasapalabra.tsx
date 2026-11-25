"use client";
import {useEffect,useRef,useState} from "react";
import {useRouter} from "next/navigation";
import {isAxiosError} from "axios";
import Image from "next/image";
import api from "@/services/api";
import {Frame} from "@/components/Pasapalabra";
import Select from "@/components/MonitoringGameSelect";
import PasapalabraModePicker from "@/components/PasapalabraModePicker";
import {PasapalabraEntry} from "@/components/PasapalabraOnline";

type Subject={id:number;name:string;academic_year:string};
type Topic={id:number;name:string;icon:string|null;levels:{level:number;available:number}[]};
function failure(error:unknown){
  const detail=isAxiosError(error)?error.response?.data?.detail:null;
  if(typeof detail==="string")return detail;
  if(detail?.code==="INSUFFICIENT_QUESTIONS")return `Hay ${detail.available} de las ${detail.required} preguntas necesarias para esta temática y nivel.`;
  if(isAxiosError(error)&&error.response?.status===429)return "Demasiados intentos. Espera antes de volver a confirmar al acompañante.";
  return "No se pudo completar la operación. Comprueba la conexión e inténtalo de nuevo.";
}
export default function EnrollmentPasapalabra(){
  const router=useRouter(),lock=useRef(false),pending=useRef<{operation_id:string;selection:Record<string,number>;mode:string}|null>(null);
  const [subjects,setSubjects]=useState<Subject[]>([]),[topics,setTopics]=useState<Topic[]>([]);
  const [subject,setSubject]=useState(""),[topic,setTopic]=useState(""),[level,setLevel]=useState("1");
  const [year,setYear]=useState(""),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [ready,setReady]=useState(false),[mode,setMode]=useState<"LOCAL"|"ONLINE">(),[join,setJoin]=useState(false);
  const [dni,setDni]=useState(""),[password,setPassword]=useState(""),[uncertain,setUncertain]=useState(false),[attempt,setAttempt]=useState(0);
  useEffect(()=>{let live=true;api.get<Subject[]>("/pasapalabra/subjects").then(({data})=>{if(live){setSubjects(data);const q=new URLSearchParams(window.location.search);if(data.some(s=>String(s.id)===q.get("subject"))){setSubject(q.get("subject")!);setTopic(q.get("topic")||"");setLevel(["1","2","3","4"].includes(q.get("level")||"")?q.get("level")!:"1");}}}).catch(e=>{if(live)setError(failure(e));}).finally(()=>{if(live)setLoading(false);});return()=>{live=false;};},[attempt]);
  useEffect(()=>{if(!subject)return;let live=true;api.get<{academic_year:string;topics:Topic[]}>(`/pasapalabra/subjects/${subject}/topics`).then(({data})=>{if(live){setTopics(data.topics);setYear(data.academic_year);}}).catch(e=>{if(live){setTopics([]);setError(failure(e));}}).finally(()=>{if(live)setLoading(false);});return()=>{live=false;};},[subject,attempt]);
  const chosen=topics.find(t=>String(t.id)===topic),available=chosen?.levels.find(l=>String(l.level)===level)?.available??0;
  function change(values:{subject?:string;topic?:string;level?:string}){
    const s=values.subject??subject,t=values.topic??topic,l=values.level??level;
    setSubject(s);setTopic(t);setLevel(l);setReady(false);setMode(undefined);setError("");setPassword("");pending.current=null;
    const q=new URLSearchParams();if(s)q.set("subject",s);if(t)q.set("topic",t);q.set("level",l);window.history.replaceState(null,"",`/pasapalabra?${q}`);
  }
  async function prepare(){if(lock.current)return;lock.current=true;setBusy(true);setError("");try{const {data}=await api.post("/pasapalabra/preparations",{subject_id:Number(subject),topic_id:Number(topic),difficulty:Number(level)});if(!data.can_start){setError(`Hay ${data.available} de las 40 preguntas necesarias en ${chosen?.name}, nivel ${level}. Elige otra combinación o consulta al docente.`);return;}setYear(data.academic.academic_year);setReady(true);}catch(e){setError(failure(e));}finally{lock.current=false;setBusy(false);}}
  async function start(){
    if(lock.current||!mode)return;lock.current=true;setBusy(true);setError("");
    pending.current??={operation_id:crypto.randomUUID(),selection:{subject_id:Number(subject),topic_id:Number(topic),difficulty:Number(level)},mode};
    try{const {data}=await api.post(mode==="LOCAL"?"/pasapalabra/local/start":"/pasapalabra/rooms",{...pending.current.selection,operation_id:pending.current.operation_id,...(mode==="LOCAL"?{guest_dni:dni,guest_password:password}:{})},{timeout:10000});setPassword("");router.push(mode==="LOCAL"?`/pasapalabra/${data.id}`:`/pasapalabra/rooms/${data.id}`);}
    catch(e){setError(failure(e));if(isAxiosError(e)&&e.response&&e.response.status<500&&e.response.status!==408){pending.current=null;setUncertain(false);}else setUncertain(true);}
    finally{setPassword("");lock.current=false;setBusy(false);}
  }
  return <Frame title="Preparar Pasapalabra">
    <div className="mx-auto max-w-3xl space-y-5">
      <p>Elige asignatura, temática y nivel. Tu matrícula determina el curso académico.</p>
      {error&&<p role="alert" className="notice-error">{error} <button className="text-link" disabled={busy} onClick={()=>setAttempt(a=>a+1)}>Volver a consultar</button></p>}
      {loading&&<p role="status">Consultando tus matrículas y el contenido disponible…</p>}
      {!loading&&!subjects.length&&!error&&<p role="status">No tienes asignaturas habilitadas para jugar. Consulta con tu docente.</p>}
      <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5" aria-label="Contenido de Pasapalabra">
        <Select label="Asignatura" value={subject||"none"} disabled={busy||uncertain} onValueChange={v=>{setLoading(true);setTopics([]);setYear("");change({subject:v==="none"?"":v,topic:""});}} options={[{value:"none",label:"Selecciona una asignatura"},...subjects.map(s=>({value:String(s.id),label:s.name}))]}/>
        {subject&&<p>Curso académico: <strong>{year.replace("-","–")||"Consultando…"}</strong> · según tu matrícula</p>}
        <Select label="Temática" value={topic||"none"} disabled={busy||uncertain||loading||!subject} onValueChange={v=>change({topic:v==="none"?"":v})} options={[{value:"none",label:"Selecciona una temática"},...topics.map(t=>({value:String(t.id),label:t.name}))]}/>
        <Select label="Nivel de dificultad" value={level} disabled={busy||uncertain||!chosen} onValueChange={v=>change({level:v})} options={[1,2,3,4].map(n=>({value:String(n),label:`Nivel ${n}`}))}/>
        {chosen&&<><p role="status">{chosen.name} · Nivel {level}: {available} preguntas disponibles. Se necesitan 40 distintas: 20 por jugador.</p>{available<40&&<p>Esta combinación todavía no tiene contenido suficiente para iniciar una partida.</p>}{chosen.icon&&<Image unoptimized src={chosen.icon} width={80} height={80} alt={`Icono de ${chosen.name}`}/>}</>}
        {!ready&&<button className="button-primary" disabled={busy||loading||!chosen||available<40} onClick={()=>void prepare()}>Continuar a modalidad</button>}
      </section>
      {ready&&<section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5"><h2 className="text-xl font-bold">Modalidad</h2><p>Ambas personas necesitan tener habilitado el mismo curso de esta asignatura. Cada cuenta conserva su resultado.</p>
        <PasapalabraModePicker registered selected={mode} disabled={busy||uncertain} onSelect={v=>{setMode(v);setError("");setPassword("");}}/>
        {mode==="LOCAL"&&<form className="space-y-3" onSubmit={e=>{e.preventDefault();void start();}}><h3 className="font-bold">Confirmar al acompañante</h3><p>El acompañante introduce sus propias credenciales. La sesión del anfitrión se mantiene.</p>
          <label className="form-label">DNI del acompañante<input className="form-input" autoComplete="off" value={dni} disabled={busy||uncertain} onChange={e=>setDni(e.target.value)} required maxLength={20}/></label>
          <label className="form-label">Contraseña del acompañante<input className="form-input" type="password" autoComplete="off" value={password} disabled={busy} onChange={e=>setPassword(e.target.value)} required maxLength={255}/></label>
          {uncertain&&<p role="status">No se pudo confirmar la respuesta del servidor. Vuelve a introducir la contraseña para reintentar el mismo inicio; no se creará otra partida.</p>}
          <button className="button-primary" disabled={busy||!dni||!password}>{busy?"Comprobando…":uncertain?"Reintentar el mismo inicio":"Confirmar y comenzar partida"}</button>
        </form>}
        {mode==="ONLINE"&&<><p>Crea la sala y comparte el código. La otra persona entra con su propia cuenta desde otro navegador o dispositivo.</p><button className="button-primary" disabled={busy} onClick={()=>void start()}>{busy?"Creando…":uncertain?"Reintentar la misma creación":"Crear sala privada"}</button></>}
      </section>}
      <button className="button-secondary" aria-expanded={join} onClick={()=>setJoin(v=>!v)}>Unirme con código</button>
      {join&&<PasapalabraEntry compact/>}
    </div>
  </Frame>;
}
