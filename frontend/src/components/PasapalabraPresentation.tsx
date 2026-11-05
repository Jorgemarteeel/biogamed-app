import Link from "next/link";
import { resolvedInOrder, type Match } from "@/lib/pasapalabra";
import styles from "./PasapalabraPresentation.module.css";

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

export function Corrections({ match }: { match: Match }) {
  const [last, ...earlier] = resolvedInOrder(match);
  function entry(answer: NonNullable<typeof last>) {
    return <article className="min-w-0 space-y-3" aria-label={`${answer.name}, pregunta ${answer.number}`}>
      <p className="break-words text-sm font-bold text-sky-900">{answer.name} · Pregunta {answer.number}</p>
      <p className={`text-lg font-black ${answer.is_correct ? "text-green-800" : "text-red-800"}`}>{answer.is_correct ? "✓ Respuesta acertada" : "× Respuesta fallada"}</p>
      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div><dt className="font-semibold text-slate-600">Respuesta introducida</dt><dd className="mt-1 break-words text-base">{answer.text_answer}</dd></div>
        <div><dt className="font-semibold text-slate-600">Solución</dt><dd className="mt-1 break-words text-base font-bold text-blue-950">{answer.exact_word}</dd></div>
      </dl>
    </article>;
  }
  return <section aria-label="Correcciones" className="mt-5 rounded-2xl border border-sky-200 bg-white p-5 sm:p-6">
    <h2 className="mb-4 text-xl font-black text-blue-950">Última respuesta resuelta</h2>
    {last ? entry(last) : <p className="text-slate-600">{match.status === "FINISHED" ? "No se registraron respuestas resueltas en este enfrentamiento." : "La próxima respuesta resuelta aparecerá aquí."}</p>}
    {earlier.length > 0 && <details className="mt-5 border-t border-slate-200 pt-3">
      <summary className="min-h-11 cursor-pointer rounded-lg py-3 font-bold text-sky-900 focus-visible:outline-2 focus-visible:outline-sky-700">Respuestas anteriores ({earlier.length})</summary>
      <ol className="divide-y divide-slate-200">{earlier.map(answer => <li key={`${answer.position}-${answer.number}`} className="py-5">{entry(answer)}</li>)}</ol>
    </details>}
  </section>;
}

export function ResultHero({ match, celebrate }: { match: Match; celebrate: boolean }) {
  const winner = match.participants.find(p => p.position === match.winner_position);
  const abandoned = match.outcome === "ABANDONMENT";
  return <section aria-labelledby="match-result-title" data-celebrating={celebrate && !abandoned ? "true" : "false"}
    className={`${styles.result} ${celebrate && !abandoned ? styles.entrance : ""} relative mb-6 overflow-hidden rounded-3xl border p-6 text-center sm:p-10 ${abandoned ? "border-slate-300 bg-white" : "border-amber-200 bg-gradient-to-br from-sky-50 via-white to-amber-50"}`}>
    {celebrate && !abandoned && <div className={styles.confetti} aria-hidden="true">{Array.from({ length: 28 }, (_, i) => <span key={i} style={{ left: `${(i * 37) % 100}%`, backgroundColor: ["#0369a1", "#f97316", "#0d9488", "#eab308"][i % 4], animationDelay: `${(i % 5) * 0.08}s` }} />)}</div>}
    <div aria-hidden="true" className={`mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full ${abandoned ? "bg-slate-100 text-slate-600" : "bg-amber-100 text-amber-800"}`}>
      <svg viewBox="0 0 64 64" className="h-12 w-12" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M20 10h24v15c0 10-5 15-12 15s-12-5-12-15V10Z M20 15H10v6c0 9 7 13 13 13 M44 15h10v6c0 9-7 13-13 13 M32 40v13 M22 55h20"/><path d="m32 17 2.5 5 5.5.8-4 4 .9 5.5-4.9-2.6-4.9 2.6.9-5.5-4-4 5.5-.8Z" fill="currentColor" strokeWidth="1"/></svg>
    </div>
    <p className="mb-3 text-xs font-bold uppercase tracking-widest text-sky-800">{abandoned ? "Enfrentamiento cerrado" : "Finalización normal"}</p>
    <h2 id="match-result-title" className="mx-auto max-w-4xl break-words text-3xl font-black leading-tight text-blue-950 sm:text-5xl">{winner ? `¡${winner.name} gana!` : "¡Empate!"}</h2>
    <p className="mx-auto mt-4 max-w-2xl break-words text-base leading-7 text-slate-600">{abandoned ? "Victoria por abandono del rival. Se conservan los resultados obtenidos; este enfrentamiento no cuenta para mejores marcas." : winner ? "¡Enhorabuena! Cada respuesta cuenta. Estos son los resultados finales de ambos jugadores." : `${match.participants.map(p => p.name).join(" y ")}: una partida compartida, el mismo número de aciertos. ¡Bien jugado!`}</p>
    <div className="mx-auto my-7 grid max-w-3xl gap-3 text-left sm:grid-cols-2">{match.participants.map(p => <article key={p.position} className={`min-w-0 rounded-2xl border bg-white p-5 ${p.position === match.winner_position || match.winner_position === null ? "border-amber-400 ring-1 ring-amber-300" : "border-slate-200"}`}>
      <h3 className="break-words text-lg font-black text-blue-950">{p.name}</h3><p className="mt-1 text-xs text-slate-500">{p.registered ? "Anfitrión · tu resultado personal" : "Invitado · sin progreso propio"}</p>
      <dl className="mt-4 grid grid-cols-3 gap-2 text-center">{[["Aciertos", p.correct], ["Fallos", p.wrong], ["Pendientes", p.pending]].map(([label, value]) => <div key={label}><dt className="text-xs font-semibold text-slate-600">{label}</dt><dd className="mt-1 text-2xl font-black text-blue-950">{value}</dd></div>)}</dl>
    </article>)}</div>
    <div className="mx-auto flex max-w-xl flex-col justify-center gap-3 sm:flex-row"><Link className="button-primary justify-center" href={`/partidas/${match.personal_session_id}`}>Ver mi historial</Link><Link className="button-secondary justify-center" href="/dashboard">Preparar otra partida</Link></div>
  </section>;
}
