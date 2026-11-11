"use client";
import {useEffect,useRef,useState} from "react";
import {isAxiosError} from "axios";
import api, {getQuestionTopics,getCurrentUser,type Topic} from "@/services/api";
import {writeReference} from "@/lib/import-recovery";
import Select from "@/components/MonitoringGameSelect";

type Validation = {total:number;valid:number;proof:string|null;errors:{row:number;column:string;message:string}[];preview:{row:number;text:string;difficulty:number|null;options:string[]|null;correct_option_index:number|null;letter:string|null;exact_word:string|null;accepted_answers:string[]|null}[]};
export default function QuestionImportForm({subjectId,blockId,categoryId,categoryName="Categoría actual",active=true,onImported}:{subjectId:number;blockId:number;categoryId:number;categoryName?:string;active?:boolean;onImported:()=>void}){
 const base=`/subjects/${subjectId}/blocks/${blockId}/categories/${categoryId}/imports`;
 const [mode,setMode]=useState("TRIVIAL"),[topic,setTopic]=useState(""),[topics,setTopics]=useState<Topic[]>([]);
 const [file,setFile]=useState<File|null>(null),[validation,setValidation]=useState<Validation|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState(""),[page,setPage]=useState(1);
 const [topicState,setTopicState]=useState<"idle"|"loading"|"ready"|"error">("idle");
 const locked=useRef(false),operation=useRef("");
 function invalidate(){setValidation(null);setError("");setNotice("");setPage(1);operation.current="";}
 async function loadTopics(){setTopicState("loading");try{setTopics(await getQuestionTopics());setTopicState("ready");}catch{setTopicState("error");}}
 const topicsRequested=useRef(false);
 useEffect(()=>{if(active && topicState==="idle" && !topicsRequested.current){topicsRequested.current=true;getQuestionTopics().then(data=>{setTopics(data);setTopicState("ready");}).catch(()=>setTopicState("error"));}},[active,topicState]);
 function payload(){const data=new FormData();data.set("mode",mode);data.set("topic_id",topic);if(file)data.set("file",file);return data;}
 function report(cause:unknown){
  const status=isAxiosError(cause)?cause.response?.status:undefined;
  const detail=isAxiosError(cause)?cause.response?.data?.detail:undefined;
  if(status===401)return;
  setError(status===403?"Has perdido los permisos de importación.":typeof detail==="string"?detail:detail?.message??"No se pudo confirmar la operación. Conserva el archivo y reintenta la misma acción.");
  if(detail?.errors)setValidation(v=>v?{...v,proof:null,errors:detail.errors}:v);
  if(status===403)setValidation(null);
 }
 async function validate(){if(locked.current||!file||!topic)return;locked.current=true;setBusy(true);setError("");setNotice("");
  try{const {data}=await api.post<Validation>(`${base}/validate`,payload());setValidation(data);setPage(1);operation.current=crypto.randomUUID();}
  catch(cause){report(cause);}finally{locked.current=false;setBusy(false);}}
 async function confirm(){if(locked.current||!validation?.proof)return;locked.current=true;setBusy(true);setError("");
  const data=payload();data.set("proof",validation.proof);data.set("operation_id",operation.current);
  try{const user=await getCurrentUser();
   try{writeReference(window.sessionStorage,{version:1,userId:user.id,subjectId,blockId,categoryId,operationId:operation.current});}
   catch{setError("El almacenamiento de sesión no está disponible. No se ha enviado la importación; habilítalo para poder recuperar el resultado tras recargar.");return;}
   const result=await api.post<{count:number;question_ids:number[]}>(`${base}/confirm`,data);setNotice(`Importación completada: ${result.data.count} ${result.data.count===1?"pregunta":"preguntas"}. IDs: ${result.data.question_ids.join(", ")}.`);setValidation(null);onImported();}
  catch(cause){report(cause);}finally{locked.current=false;setBusy(false);}}
 async function template(){if(locked.current)return;locked.current=true;setBusy(true);setError("");try{const response=await api.get(`${base}/template`,{params:{mode},responseType:"blob"});const url=URL.createObjectURL(response.data);const link=document.createElement("a");link.href=url;link.download=`plantilla-${mode.toLowerCase()}.csv`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(cause){report(cause);}finally{locked.current=false;setBusy(false);}}
 const rows=validation?.preview.slice((page-1)*10,page*10)??[];
 return <section aria-label="Importar preguntas">
  <div className="space-y-4" aria-busy={busy}>
   <section aria-labelledby="import-destination-heading" className="space-y-3">
    <h2 id="import-destination-heading" className="text-lg font-bold text-blue-950">1. Elegir destino</h2>
    <p className="break-words font-semibold">Categoría: {categoryName}</p>
    <div className="grid gap-4 sm:grid-cols-2"><Select label="Juego para importar" name="import-game" value={mode} disabled={busy} onValueChange={v=>{invalidate();setMode(v);}} options={[{value:"TRIVIAL",label:"Trivial"},{value:"PASAPALABRA",label:"Pasapalabra"}]}/>
    <div>{topicState === "loading" || topicState === "idle" ? <p role="status">Cargando temáticas…</p> : topicState === "error" ? <div><p role="alert">No se pudieron cargar las temáticas.</p><button type="button" className="button-secondary" onClick={()=>void loadTopics()}>Reintentar</button></div> : topics.length === 0 ? <p role="status">No hay temáticas de destino disponibles.</p> : <Select id="import-topic" name="import-topic" label="Temática de destino" disabled={busy} value={topic || "NONE"} onValueChange={value=>{invalidate();setTopic(value === "NONE" ? "" : value);}} options={[{value:"NONE",label:"Selecciona una temática"},...topics.map(t=>({value:String(t.id),label:t.name}))]}/>}</div></div>
   </section>
   <section aria-labelledby="import-file-heading" className="space-y-3 border-t border-slate-200 pt-4">
    <h2 id="import-file-heading" className="text-lg font-bold text-blue-950">2. Preparar y seleccionar CSV</h2>
    <p className="text-sm text-slate-600">{mode === "TRIVIAL" ? "Trivial: enunciado, cuatro opciones y respuesta correcta A–D." : "Pasapalabra: enunciado, letra y solución. Alternativas opcionales: una por línea dentro de una celda entrecomillada."} Dificultad: 1–4 o celda vacía.</p>
    <details className="text-sm"><summary className="text-link min-h-11 cursor-pointer">Ayuda con el CSV</summary><p>Usa comillas dobles para celdas con separadores o saltos de línea y duplica las comillas interiores.{mode === "PASAPALABRA" && " Para pistas de tipo contiene, empieza el enunciado con «Contiene la letra…»."} Las cabeceras deben coincidir con la plantilla.</p></details>
    <button type="button" className="button-secondary" disabled={busy} onClick={()=>void template()}>Descargar plantilla</button>
    <div className="flex flex-wrap items-center gap-3"><label className={`button-secondary cursor-pointer relative focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-orange-700 ${busy?"opacity-50":""}`} htmlFor="import-file">Seleccionar CSV<input id="import-file" className="absolute inset-0 h-full w-full cursor-pointer opacity-0" aria-label="Seleccionar CSV" type="file" accept=".csv,text/csv" disabled={busy} onChange={e=>{invalidate();const next=e.target.files?.[0]??null;setFile(next);if(next&&next.size>2*1024*1024)setError("Máximo 2 MiB. Selecciona otro archivo.");}}/></label><span className="min-w-0 break-all text-sm">{file?.name || "Ningún archivo seleccionado"}</span></div>
    <p className="text-sm text-slate-600">CSV UTF-8 · BOM admitido · Separador ; · Máximo 500 preguntas y 2 MiB.</p>
   </section>
   <section aria-labelledby="import-review-heading" className="space-y-3 border-t border-slate-200 pt-4">
    <h2 id="import-review-heading" className="text-lg font-bold text-blue-950">3. Validar y revisar</h2>
    <p id="import-validation-help" className="text-sm text-slate-600">{topicState==="error" ? "Reintenta la carga de temáticas para elegir un destino." : topicState!=="ready" ? "Espera a que estén disponibles las temáticas." : !topics.length ? "No hay destinos disponibles." : !topic && !file ? "Selecciona una temática y un archivo CSV." : !topic ? "Selecciona una temática." : !file ? "Selecciona un archivo CSV." : file.size>2*1024*1024 ? "Selecciona un archivo de hasta 2 MiB." : "Listo para validar. Validar no guarda preguntas."}</p>
    <button type="button" aria-describedby="import-validation-help" className="button-primary" disabled={busy||topicState!=="ready"||!topic||!file||file.size>2*1024*1024} onClick={()=>void validate()}>Validar sin guardar</button>
   {error&&<p role="alert" className="notice-error">{error}</p>}{notice&&<p role="status" className="notice-success break-words">{notice}</p>}
   {validation&&<section aria-label="Resultado de validación" className="space-y-3">
    <p className="break-words font-semibold">Destino: {categoryName} · {topics.find(t=>String(t.id)===topic)?.name} · {mode==="TRIVIAL"?"Trivial":"Pasapalabra"} · {file?.name}</p>
    <p role="status">{validation.total} registros · {validation.valid} con campos válidos · {validation.errors.length} errores. Todavía no se ha guardado ninguna pregunta.</p>
    {validation.errors.length>0&&<div><h3 className="font-bold">Qué debes corregir</h3><ul className="max-h-64 overflow-auto rounded-xl border border-slate-200 p-3">{validation.errors.map((e,i)=><li key={i} className="break-words">Registro {e.row} · {e.column}: {e.message}</li>)}</ul></div>}
    <p className="text-sm">Los registros cuentan desde la cabecera (1); una celda puede ocupar varias líneas. Las preguntas duplicadas bloquean el lote, incluso si están retiradas.</p>
    <ol className="space-y-3">{rows.map(row=><li key={row.row} className="rounded-xl border border-sky-200 p-3 break-words"><strong>Registro {row.row} · {row.difficulty===null?"Sin dificultad asignada":`Nivel ${row.difficulty}`}</strong><p className="whitespace-pre-wrap">{row.text}</p>{row.options?<ul>{row.options.map((o,i)=><li key={i}>{"ABCD"[i]}: {o}{i===row.correct_option_index?" · Correcta":""}</li>)}</ul>:<p>Letra: {row.letter} · Solución: {row.exact_word} · Alternativas: {row.accepted_answers?.join(", ")||"Ninguna"}</p>}</li>)}</ol>
    <nav aria-label="Páginas de vista previa" className="flex flex-wrap items-center gap-3"><button type="button" className="button-secondary" disabled={busy||page===1} onClick={()=>setPage(p=>p-1)}>Anterior</button><span>Página {page} de {Math.max(1,Math.ceil(validation.preview.length/10))}</span><button type="button" className="button-secondary" disabled={busy||page*10>=validation.preview.length} onClick={()=>setPage(p=>p+1)}>Siguiente</button></nav>
    {validation.proof&&<p className="font-semibold">Se importarán {validation.total} preguntas en {categoryName} · {topics.find(t=>String(t.id)===topic)?.name}.</p>}
    {validation.proof&&<div className="notice-warning"><p>Revisa categoría, temática y preguntas antes de confirmar. La validación caduca en 15 minutos; se volverá a comprobar al guardar.</p><button type="button" className="button-primary mt-3" disabled={busy} onClick={()=>void confirm()}>Confirmar importación de {validation.total} {validation.total===1?"pregunta":"preguntas"}</button></div>}
   </section>}
   </section>
  </div>
 </section>;
}
