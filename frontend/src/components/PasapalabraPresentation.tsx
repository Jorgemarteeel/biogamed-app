"use client";
import {useState, type ReactNode} from "react";
import Link from "next/link";
import { resolvedInOrder, type Match } from "@/lib/pasapalabra";
import styles from "./PasapalabraPresentation.module.css";
import layout from "./PasapalabraLayout.module.css";

export function StateLegend() {
  const states = [
    ["·", "Pendiente", "bg-blue-950 text-white"],
    ["↻", "Pasada", "bg-amber-800 text-white"],
    ["✓", "Acertada", "bg-green-800 text-white"],
    ["×", "Fallada", "bg-red-800 text-white"],
    ["◎", "Pregunta actual", "bg-sky-50 text-sky-900 ring-2 ring-sky-600"],
  ];
  return <ul aria-label="Leyenda del rosco" className="mb-5 flex flex-wrap gap-x-4 gap-y-3 text-sm font-medium text-slate-700">
    {states.map(([symbol, label, color]) => <li key={label} className="flex items-center gap-2">
      <span aria-hidden="true" className={`flex h-6 w-6 items-center justify-center rounded-full font-bold ${color}`}>{symbol}</span>{label}
    </li>)}
  </ul>;
}

export function Corrections({ match, compact = false }: { match: Match; compact?: boolean }) {
  const [last, ...earlier] = resolvedInOrder(match);
  function entry(answer: NonNullable<typeof last>, small = false) {
    return <article className={small ? layout.latest : "min-w-0 space-y-3"} aria-label={`${answer.name}, pregunta ${answer.number}`}>
      <div className={small ? layout.latestHeader : "space-y-3"}>
      <p className="break-words text-sm font-bold text-sky-900">{answer.name} · Pregunta {answer.number}</p>
      <p className={`font-black ${answer.is_correct ? "text-green-800" : "text-red-800"}`}>{answer.is_correct ? "✓ Respuesta acertada" : "× Respuesta fallada"}</p></div>
      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div><dt className="font-semibold text-slate-600">Respuesta introducida</dt><dd tabIndex={small ? 0 : undefined} className="break-words text-base">{answer.text_answer}</dd></div>
        <div><dt className="font-semibold text-slate-600">Solución</dt><dd tabIndex={small ? 0 : undefined} className="break-words text-base font-bold text-blue-950">{answer.exact_word}</dd></div>
      </dl>
    </article>;
  }
  return <section aria-label="Correcciones" className={compact ? layout.corrections : "rounded-2xl border border-sky-200 bg-white p-4"} data-has-history={compact && earlier.length > 0 ? "true" : undefined}>
    <h2 className="font-black text-blue-950">Última respuesta resuelta</h2>
    {last ? entry(last, compact) : <p className="text-sm text-slate-600">{match.status === "FINISHED" ? (match.play_mode === "ONLINE" ? "No registraste respuestas resueltas en este enfrentamiento." : "No se registraron respuestas resueltas en este enfrentamiento.") : (match.play_mode === "ONLINE" ? "Tu próxima respuesta resuelta aparecerá aquí." : "La próxima respuesta resuelta aparecerá aquí.")}</p>}
    {earlier.length > 0 && <details className={compact ? layout.history : "mt-3 border-t border-slate-200"} onKeyDown={e=>{if(e.key==='Escape'){e.preventDefault();e.currentTarget.open=false;e.currentTarget.querySelector('summary')?.focus();}}}>
      <summary className="cursor-pointer rounded-lg font-bold text-sky-900 focus-visible:outline-2 focus-visible:outline-sky-700">Respuestas anteriores ({earlier.length})</summary>
      <div className={compact ? layout.historyPanel : ""} tabIndex={0} role="region" aria-label="Respuestas anteriores"><button className="button-secondary" onClick={e=>{const details=e.currentTarget.closest('details');if(details){details.open=false;details.querySelector('summary')?.focus();}}}>Cerrar respuestas anteriores</button>
      <ol className="divide-y divide-slate-200">{earlier.map(answer => <li key={`${answer.position}-${answer.number}`} className="py-4">{entry(answer)}</li>)}</ol></div>
    </details>}
  </section>;
}

export function ResultHero({ match, celebrate, children }: { match: Match; celebrate: boolean; children?: ReactNode }) {
  const winner = match.participants.find(p => p.position === match.winner_position);
  const abandoned = match.outcome === "ABANDONMENT";
  return <section aria-labelledby="match-result-title" data-celebrating={celebrate && !abandoned ? "true" : "false"}
    className={`${styles.result} ${layout.resultHero} ${celebrate && !abandoned ? styles.entrance : ""} relative overflow-hidden rounded-3xl border text-center ${abandoned ? "border-slate-300 bg-white" : "border-amber-200 bg-gradient-to-br from-sky-50 via-white to-amber-50"}`}>
    {celebrate && !abandoned && <div className={styles.confetti} aria-hidden="true">{Array.from({ length: 28 }, (_, i) => <span key={i} style={{ left: `${(i * 37) % 100}%`, backgroundColor: ["#0369a1", "#f97316", "#0d9488", "#eab308"][i % 4], animationDelay: `${(i % 5) * 0.08}s` }} />)}</div>}
    <div aria-hidden="true" className={`${layout.resultIcon} flex items-center justify-center rounded-full ${abandoned ? "bg-slate-100 text-slate-600" : "bg-amber-100 text-amber-800"}`}>
      <svg viewBox="0 0 64 64" className="h-12 w-12" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M20 10h24v15c0 10-5 15-12 15s-12-5-12-15V10Z M20 15H10v6c0 9 7 13 13 13 M44 15h10v6c0 9-7 13-13 13 M32 40v13 M22 55h20"/><path d="m32 17 2.5 5 5.5.8-4 4 .9 5.5-4.9-2.6-4.9 2.6.9-5.5-4-4 5.5-.8Z" fill="currentColor" strokeWidth="1"/></svg>
    </div>
    <p className="mb-3 text-xs font-bold uppercase tracking-widest text-sky-800">{abandoned ? "Enfrentamiento cerrado" : "Finalización normal"}</p>
    <h2 id="match-result-title" tabIndex={0} className="mx-auto max-w-4xl break-words font-black text-blue-950">{winner ? `¡${winner.name} gana!` : "¡Empate!"}</h2>
    <p className={`${layout.resultIntro} mx-auto max-w-2xl break-words text-slate-600`}>{abandoned ? `${match.play_mode === "ONLINE" && match.self_position !== match.winner_position ? "Victoria por abandono. Has abandonado y tu rival gana." : "Victoria por abandono del rival."} Se conservan los resultados obtenidos; este enfrentamiento no cuenta para mejores marcas.` : "Estos son los resultados finales de ambos jugadores."}</p>
    {children??<div className={`${layout.resultScores} grid max-w-3xl text-left sm:grid-cols-2`}>{match.participants.map(p => <article key={p.position} className={`min-w-0 rounded-2xl border bg-white ${p.position === match.winner_position || match.winner_position === null ? "border-amber-400 ring-1 ring-amber-300" : "border-slate-200"}`}>
      <h3 tabIndex={0} className="break-words font-black text-blue-950">{p.name}</h3><p className="mt-1 text-xs text-slate-500">{match.play_mode === "ONLINE" ? (p.position === match.self_position ? "Tu resultado personal" : "Rival · resumen público") : p.registered ? "Anfitrión · tu resultado personal" : "Invitado · sin progreso propio"}</p>
      <dl className="mt-4 grid grid-cols-3 gap-2 text-center">{[["Aciertos", p.correct], ["Fallos", p.wrong], ["Pendientes", p.pending]].map(([label, value]) => <div key={label}><dt className="text-xs font-semibold text-slate-600">{label}</dt><dd className="mt-1 text-2xl font-black text-blue-950">{value}</dd></div>)}</dl>
    </article>)}</div>}
    <div className="mx-auto flex max-w-xl flex-col justify-center gap-3 sm:flex-row"><Link className="button-primary justify-center" href={`/partidas/${match.personal_session_id}`}>Ver mi historial</Link><Link className="button-secondary justify-center" href="/dashboard">Preparar otra partida</Link></div>
  </section>;
}

/** Uses only the already authorized resolved projection; never queries the bank. */
export function finalAnswerRows(match:Match,player="all",status="all") {
 return resolvedInOrder(match).filter(a=>(player==="all"||String(a.position)===player)&&(status==="all"||(status==="correct"?a.is_correct===true:a.is_correct===false)))
  .sort((a,b)=>a.position-b.position||a.number-b.number);
}
export function FinalAnswers({match}:{match:Match}) {
 const [player,setPlayer]=useState("all"),[status,setStatus]=useState("all"),[limit,setLimit]=useState(10);
 const rows=finalAnswerRows(match,player,status);
 const visiblePlayers=match.participants.filter(p=>match.play_mode!=="ONLINE"||p.position===match.self_position);
 return <section className={layout.finalReview} aria-labelledby="final-answers-title">
  <h2 id="final-answers-title" className="text-xl font-black text-blue-950">Revisar respuestas</h2>
  <p className="text-sm text-slate-600">Respuestas resueltas, ordenadas por jugador y número de pregunta. Las pendientes no tienen respuesta registrada.{match.play_mode==="ONLINE"?" Solo puedes revisar tus propias respuestas.":""}</p>
  <div className="my-3 flex flex-wrap gap-3">
   {visiblePlayers.length>1&&<label className="font-semibold">Jugador<select className="form-input" value={player} onChange={e=>{setPlayer(e.target.value);setLimit(10);}}><option value="all">Todos los jugadores</option>{visiblePlayers.map(p=><option key={p.position} value={p.position}>{p.name}</option>)}</select></label>}
   <label className="font-semibold">Estado<select className="form-input" value={status} onChange={e=>{setStatus(e.target.value);setLimit(10);}}><option value="all">Todas las resueltas</option><option value="correct">✓ Acertadas</option><option value="wrong">× Falladas</option></select></label>
  </div>
  <p role="status" className="text-sm text-slate-600">{rows.length?`${Math.min(limit,rows.length)} de ${rows.length} respuestas`:"No hay respuestas resueltas disponibles con estos filtros."}</p>
  <ol className="divide-y divide-slate-200">{rows.slice(0,limit).map((a,i)=><li key={`${a.position}-${a.number}-${i}`} className="py-4">
   <article aria-label={`${a.name}, pregunta ${a.number}`} className="min-w-0 space-y-2">
    <h3 className="break-words font-bold text-blue-950">{a.name} · Pregunta {a.number}</h3>
    <p className={`font-bold ${a.is_correct?"text-green-800":"text-red-800"}`}>{a.is_correct?"✓ Acertada":"× Fallada"}</p>
    {a.text&&<p className="break-words">{a.text}</p>}
    <dl className="grid gap-3 text-sm sm:grid-cols-2"><div><dt className="font-semibold text-slate-600">Respuesta introducida</dt><dd className="break-words">{a.text_answer??"No disponible en este registro"}</dd></div><div><dt className="font-semibold text-slate-600">Solución</dt><dd className="break-words font-bold text-blue-950">{a.exact_word??"No disponible en este registro"}</dd></div></dl>
   </article>
  </li>)}</ol>
  {limit<rows.length&&<button className="button-secondary mt-3" onClick={()=>setLimit(v=>v+10)}>Mostrar más respuestas</button>}
 </section>;
}
