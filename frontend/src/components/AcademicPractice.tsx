"use client";
import {useEffect, useRef, useState} from "react";
import {useRouter, useSearchParams} from "next/navigation";
import Link from "next/link";
import {isAxiosError} from "axios";
import api, {type AcademicContext as Context, type GameAvailability, type GameSessionStart} from "@/services/api";
import {Frame} from "@/components/Pasapalabra";
import preparation from "./AcademicPractice.module.css";
import BackLink from "@/components/BackLink";
import TrivialGame from "@/components/TrivialGame";
import GameIllustration from "@/components/GameIllustration";
import GameChoiceCards from "@/components/GameChoiceCards";
import PasapalabraModePicker, {PasapalabraModeIllustration} from "@/components/PasapalabraModePicker";
import {AcademicCards, SubjectContents} from "@/components/AcademicCatalog";

import {practiceHref, practiceQuery, practiceBackHref, questionsForDifficulty} from "@/lib/academic";

type Item={id:number;name:string;description:string|null;availability?:Record<string,number>};
type Catalog={items?:Item[];context?:{subject?:Item;block?:Item};academic?:Context;availability?:Record<string,number>};
function errorMessage(error:unknown){
  const status=isAxiosError(error)?error.response?.status:undefined;
  return status===401?"Inicia sesión para continuar. Conservamos este recorrido.":status===404?"La asignatura, bloque o categoría no está disponible en esta ruta.":status===409?"La disponibilidad ha cambiado. Revisa los filtros y vuelve a consultar.":"No se pudo confirmar la petición. Comprueba tu conexión y reintenta.";
}
export default function AcademicPractice(){const search=useSearchParams().toString();return <Practice key={search} query={search}/>;}
function Practice({query}:{query:string}){
  const router=useRouter();
  const selected=practiceQuery(new URLSearchParams(query));
  const {ids,mode,difficulty,play,step}=selected;
  const changingContent=new URLSearchParams(query).get("edit")==="content";
  const showGames=!selected.explicitMode||step==="game";
  const showModes=mode==="PASAPALABRA"&&(!selected.explicitPlay||step==="mode");
  const prepared=!changingContent&&!showGames&&!showModes;
  const [information,setInformation]=useState<Item[]>([]);
  const [catalog,setCatalog]=useState<Catalog|null>(null);
  const [bank,setBank]=useState<GameAvailability|null>(null);
  const [gameBanks,setGameBanks]=useState<Partial<Record<"TRIVIAL"|"PASAPALABRA",GameAvailability>>>({});
  const [error,setError]=useState(selected.valid?"":"El enlace de práctica no es válido. Revisa la ruta o vuelve a las asignaturas.");
  const [loading,setLoading]=useState(selected.valid);
  const [unavailablePath,setUnavailablePath]=useState(false);
  const [attempt,setAttempt]=useState(0);
  const [busy,setBusy]=useState(false);
  const [uncertain,setUncertain]=useState(false);
  const [guest,setGuest]=useState("");
  const [session,setSession]=useState<GameSessionStart|null>(null);
  const pending=useRef<{url:string;body:Record<string,unknown>}|null>(null);
  const lock=useRef(false);
  const heading=useRef<HTMLHeadingElement>(null);
  const difficultyField=useRef<HTMLSelectElement>(null);
  const level=ids.category?"prepare":ids.block?"categories":ids.subject?"blocks":"subjects";
  const pageKey=level+"Page";
  const page=ids[pageKey]??1;
  const path=ids.category?`/practice/subjects/${ids.subject}/blocks/${ids.block}/categories/${ids.category}`:ids.block?`/practice/subjects/${ids.subject}/blocks/${ids.block}/categories`:ids.subject?`/practice/subjects/${ids.subject}/blocks`:"/practice/subjects";
  useEffect(()=>{
    let live=true;
    if(!practiceQuery(new URLSearchParams(query)).valid)return;
    if(!localStorage.getItem("token")){try{sessionStorage.setItem("pasapalabra-return","/practicar"+(query?`?${query}`:""));}catch{}router.replace("/login");return;}
    async function load(){
      try{
        const {data}=await api.get<Catalog>(path,{params:level==="prepare"?undefined:{skip:(page-1)*12,limit:13},timeout:10000});
        if(data.academic){const metadata=(await api.get<Catalog>(`/practice/subjects/${data.academic.subject_id}/blocks`,{params:{skip:0,limit:1},timeout:10000})).data;data.context={...metadata.context,...data.context};}
        const banks:Partial<Record<"TRIVIAL"|"PASAPALABRA",GameAvailability>>={};
        if(data.academic&&!changingContent){
          const a=data.academic;
          const modes=showGames?["TRIVIAL","PASAPALABRA"] as const:step==="prepare"?[mode as "TRIVIAL"|"PASAPALABRA"]:[];
          await Promise.all(modes.map(async game=>{banks[game]=(await api.post<GameAvailability>(`/game/academic/preparations?mode=${game}`,{subject_id:a.subject_id,block_id:a.block_id,category_id:a.category_id},{timeout:10000})).data;}));
        }
        if(live){setCatalog(data);setGameBanks(banks);setBank(banks[mode as "TRIVIAL"|"PASAPALABRA"]??null);setUnavailablePath(false);setLoading(false);}

      }catch(e){if(live){setError(errorMessage(e));setUnavailablePath(isAxiosError(e)&&e.response?.status===404);setLoading(false);}}
    }
    void load();return()=>{live=false;};
  },[query,path,level,page,mode,step,showGames,selected.explicitMode,changingContent,attempt,router]);
  useEffect(()=>{if(loading)return;const focus=new URLSearchParams(query).get("focus");if(focus==="difficulty")difficultyField.current?.focus({preventScroll:true});else if(!selected.explicitMode||focus==="prepare")heading.current?.focus({preventScroll:true});},[loading,selected.explicitMode,query]);
  useEffect(()=>{try{const saved=sessionStorage.getItem("academic-guest");if(saved)Promise.resolve().then(()=>setGuest(saved));}catch{}},[]);
  const href=(changes:Record<string,string|number|undefined>)=>practiceHref(query,changes);
  const academic=session?.content_context?.academic??catalog?.academic;
  const combinations=bank?.combinations??[];
  const available=questionsForDifficulty(bank,difficulty);
  const cardAvailability={TRIVIAL:questionsForDifficulty(gameBanks.TRIVIAL,"all"),PASAPALABRA:questionsForDifficulty(gameBanks.PASAPALABRA,"all")};
  const levels=[...new Set((showGames?Object.values(gameBanks).flatMap(b=>b?.combinations??[]):combinations).map(c=>c.difficulty))].sort((a,b)=>(a??5)-(b??5));
  const difficultyCompatible=difficulty==="all"||levels.some(v=>(v===null?"unknown":String(v))===difficulty);
  const canStart=prepared&&selected.explicitMode&&(mode!=="PASAPALABRA"||selected.explicitPlay)&&!!bank&&available>=(mode==="PASAPALABRA"?40:1)&&(mode!=="PASAPALABRA"||play==="ONLINE"||!!guest.trim());
  async function start(){
    if(lock.current||!academic||(!uncertain&&!canStart))return;
    lock.current=true;setBusy(true);setError("");
    const selection={subject_id:academic.subject_id,block_id:academic.block_id,category_id:academic.category_id,...(difficulty==="unknown"?{difficulty_unknown:true}:difficulty!=="all"?{difficulty:Number(difficulty)}:{})};
    pending.current??={url:mode==="TRIVIAL"?"/game/academic/start":play==="ONLINE"?"/pasapalabra/rooms":"/pasapalabra/local/start",body:{...selection,...(mode==="PASAPALABRA"?{operation_id:crypto.randomUUID(),...(play==="LOCAL"?{guest_name:guest.trim()}:{})}:{})}};
    try{
      const {data}=await api.post(pending.current.url,pending.current.body,{timeout:10000});
      pending.current=null;setUncertain(false);
      if(mode==="TRIVIAL")setSession(data);else router.push(play==="ONLINE"?`/pasapalabra/rooms/${data.id}`:`/pasapalabra/${data.id}`);
    }catch(e){
      setError(errorMessage(e));
      if(isAxiosError(e)&&e.response&&e.response.status<500&&e.response.status!==408){pending.current=null;setUncertain(false);}
      else setUncertain(true);
    }finally{lock.current=false;setBusy(false);}
  }
  const context=catalog?.context;
  return <div className={`${preparation.page} ${!session?preparation.preparing:""}`}><Frame backControl={!session?<BackLink href={practiceBackHref(query,unavailablePath)} disabled={busy||uncertain}/>:undefined} title={session?(academic?.subject_name??"Práctica académica"):academic?"Prepara tu partida":context?.subject?.name??"Elige asignatura"}>
    <div className="w-full min-w-0 space-y-4">
      {error&&<div role="alert" className="notice-warning">{error} {!session&&selected.valid&&<button className="text-link ml-3 min-h-11" disabled={busy||uncertain} onClick={()=>{setError("");setLoading(true);setAttempt(v=>v+1);}}>Volver a consultar</button>} {error.includes("sesión")&&<Link href="/login" className="text-link">Iniciar sesión</Link>}</div>}
      {loading?<p role="status">Consultando contenido académico…</p>:session?<TrivialGame session={session} topicName={academic?.category_name??"Práctica académica"}/>:catalog?<>
        {ids.subject?<>
          <div className="w-full space-y-3" onClickCapture={e=>{if((busy||uncertain)&&(e.target as HTMLElement).closest('a[href^="/practicar"]'))e.preventDefault();}}>
          {academic&&<div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-sky-200 bg-sky-50 px-4 py-2" aria-label="Contenido elegido"><p className="min-w-0 break-words text-sm font-semibold text-blue-950">{academic.subject_name} → {academic.block_name} → <strong>{academic.category_name}</strong></p><button className="text-link min-h-11 shrink-0" disabled={busy||uncertain} onClick={()=>router.push(href({edit:changingContent?undefined:"content",focus:"prepare"}),{scroll:false})}>{changingContent?"Conservar contenido":"Cambiar contenido"}</button></div>}
          {(!academic||changingContent)?<SubjectContents onInformation={setInformation} initialBlocks={level==="blocks"?catalog.items:undefined} initialCategories={level==="categories"?catalog.items:undefined} selectedBlock={academic?{id:academic.block_id,name:academic.block_name,description:null}:context?.block} query={query} disabled={busy||uncertain} onNavigate={target=>{if(!busy&&!uncertain)router.push(target,{scroll:false});}}/>:null}
          {academic&&!changingContent?<section aria-label="Preparación académica" className="min-w-0 space-y-3">
            {showGames?<><h2 ref={heading} tabIndex={-1} className="text-xl font-black text-blue-950 outline-none">Elige el juego</h2><GameChoiceCards compact availability={cardAvailability} selected={selected.explicitMode?(mode==="PASAPALABRA"?"PASAPALABRA":"TRIVIAL"):undefined} disabled={busy||uncertain} onSelect={game=>router.push(href({mode:game,step:game==="TRIVIAL"?"prepare":selected.explicitPlay?"prepare":"mode",focus:"prepare"}),{scroll:false})}/></>:<>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="flex min-w-0 items-center gap-3 rounded-xl border border-sky-200 bg-white px-3 py-2" aria-label="Juego elegido"><span className="shrink-0 [&_svg]:h-12 [&_svg]:w-20"><GameIllustration mode={mode==="PASAPALABRA"?"PASAPALABRA":"TRIVIAL"}/></span><strong className="text-blue-950">{mode==="TRIVIAL"?"Trivial":"Pasapalabra"}</strong><button className="text-link ml-auto min-h-11 shrink-0 text-sm" disabled={busy||uncertain} onClick={()=>router.push(href({step:"game",focus:"prepare"}),{scroll:false})}>Cambiar juego</button></div>
              {mode==="PASAPALABRA"&&!showModes&&<div className="flex min-w-0 items-center gap-2 rounded-xl border border-sky-200 bg-white px-3 py-2" aria-label="Modo elegido"><span className="shrink-0 [&_svg]:h-12 [&_svg]:w-20"><PasapalabraModeIllustration online={play==="ONLINE"}/></span><p className="min-w-0 text-sm font-bold text-blue-950">{play==="LOCAL"?"En este dispositivo":"En línea"}<span className="block font-normal text-slate-600">{play==="LOCAL"?"Tú y un invitado":"Con un amigo · Dos cuentas"}</span></p><button className="text-link ml-auto min-h-11 shrink-0 text-sm" disabled={busy||uncertain} onClick={()=>router.push(href({step:"mode",focus:"prepare"}),{scroll:false})}>Cambiar modalidad</button></div>}
            </div>
            {showModes?<><h2 ref={heading} tabIndex={-1} className="text-xl font-black text-blue-950 outline-none">¿Cómo queréis jugar a Pasapalabra?</h2><PasapalabraModePicker compact selected={selected.explicitPlay?(play==="ONLINE"?"ONLINE":"LOCAL"):undefined} disabled={busy||uncertain} onSelect={value=>router.push(href({play:value,step:"prepare",focus:"prepare"}),{scroll:false})}/></>:<div className="space-y-3">
            <h2 ref={heading} tabIndex={-1} className="text-lg font-black text-blue-950 outline-none">{mode==="TRIVIAL"?"Preparar Trivial":play==="LOCAL"?"Preparar Pasapalabra local":"Preparar sala de Pasapalabra"}</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="font-semibold">Dificultad<select ref={difficultyField} className="form-input" value={difficulty} disabled={busy||uncertain} onChange={e=>router.push(href({difficulty:e.target.value,focus:"difficulty"}),{scroll:false})}><option value="all">Sin filtrar dificultad</option>{levels.map(v=><option key={v??"unknown"} value={v??"unknown"}>{v===null?"Sin clasificar":`Nivel ${v}`}</option>)}{!difficultyCompatible&&<option value={difficulty}>{difficulty==="unknown"?"Sin clasificar":`Nivel ${difficulty}`} · Sin preguntas</option>}</select></label>
              {mode==="PASAPALABRA"&&selected.explicitPlay&&play==="LOCAL"&&<label className="font-semibold">Nombre del invitado<input className="form-input" maxLength={255} value={guest} disabled={busy||uncertain} onChange={e=>{setGuest(e.target.value);try{sessionStorage.setItem("academic-guest",e.target.value);}catch{}}}/></label>}
            </div>
            <div className="space-y-3 rounded-xl bg-sky-50 p-4" aria-label="Resumen de preparación">
        {bank&&bank.total_questions>0&&!difficultyCompatible&&<p role="status" className="notice-warning">La dificultad elegida no está disponible para {mode==="TRIVIAL"?"Trivial":"Pasapalabra"} en esta categoría. Selecciona otra para continuar; no hemos cambiado tu filtro.</p>}
        <p role="status" className="font-semibold text-blue-950">{!bank?"Disponibilidad no disponible.":bank.total_questions===0?"Esta categoría todavía no tiene preguntas jugables para este juego.":available===0?"No hay preguntas para la dificultad seleccionada.":mode==="TRIVIAL"?`${available} ${available===1?"pregunta disponible":"preguntas disponibles"} · Partida de ${Math.min(10,available)} ${Math.min(10,available)===1?"pregunta":"preguntas"}.`:`${available} preguntas disponibles de las 40 necesarias · 20 por jugador · 10 minutos individuales.`}</p>
        {mode==="PASAPALABRA"&&available>0&&available<40&&<p className="notice-warning">Preguntas insuficientes. Elige otra dificultad o categoría; los filtros no se cambiarán automáticamente.</p>}
        <button className="button-primary" disabled={busy||(uncertain&&mode==="TRIVIAL")||(!uncertain&&!canStart)} onClick={()=>void start()}>{busy?"Preparando…":uncertain?(mode==="TRIVIAL"?"Inicio sin confirmar":"Reintentar la misma operación"):mode==="PASAPALABRA"&&play==="ONLINE"?"Crear sala privada":"Comenzar partida"}</button>
        {uncertain&&mode==="TRIVIAL"&&<p className="notice-warning">No repetimos este inicio para evitar duplicados. <Link className="text-link" href="/historial">Revisa tu historial</Link> antes de preparar otra partida.</p>}
        <details className="text-sm text-slate-600"><summary className="min-h-11 cursor-pointer font-semibold text-sky-900">Sobre el inicio de la partida</summary><p>{mode==="TRIVIAL"?"La partida comienza solo al pulsar el botón. Recargar después de iniciarla conserva el registro, pero no las respuestas sin enviar.":"La selección se comprueba otra vez al comenzar. Recargar una partida no pausa el reloj."}</p></details>
            </div></div>}
            </>}
          </section>:null}
        </div></>:<><h2 ref={heading} tabIndex={-1} className="text-xl font-black text-blue-950 outline-none">Elige asignatura</h2><AcademicCards items={catalog.items??[]} query={query} page={page}/></>}
      </>:null}
      {!session&&(context?.subject?.description||information.some(item=>item.description))&&<details className="text-sm text-slate-600"><summary className="min-h-11 cursor-pointer font-semibold text-sky-900">Sobre este contenido</summary><p className="max-w-3xl">{context?.subject?.description}</p>{information.filter(item=>item.description).map((item,index)=><p key={`${index}-${item.id}`} className="mt-2 max-w-3xl"><strong>{item.name}: </strong>{item.description}</p> )}</details>}
      {!session&&<div className="flex flex-wrap gap-4 text-sm"><Link className="text-link inline-flex min-h-11 items-center" href="/dashboard?banks=1">Explorar otros contenidos</Link><Link className="text-link inline-flex min-h-11 items-center" href="/pasapalabra?join=1">Unirme con código</Link></div>}
    </div>
  </Frame></div>;
}