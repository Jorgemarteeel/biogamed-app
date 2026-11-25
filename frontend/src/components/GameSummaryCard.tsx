import Link from "next/link";
import { describeContentContext } from "@/lib/game-review";
import { gameSummary } from "@/lib/game-summary";
import type { GameHistorySummary } from "@/services/api";

function GameIcon({ name }: { name: string }) {
  return <svg viewBox="0 0 40 40" width="36" height="36" fill="none" aria-hidden="true" focusable="false">
    {name === "Pasapalabra" ? <><circle cx="20" cy="20" r="15" stroke="currentColor" strokeWidth="6" strokeDasharray="6 3" /><path d="m15 26 5-13 5 13m-8-5h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></>
      : name === "Trivial" ? <><rect x="6" y="6" width="28" height="28" rx="6" stroke="currentColor" strokeWidth="2" /><circle cx="14" cy="14" r="2" fill="currentColor" /><circle cx="20" cy="20" r="2" fill="currentColor" /><circle cx="26" cy="26" r="2" fill="currentColor" /></>
        : <><rect x="8" y="5" width="24" height="30" rx="4" stroke="currentColor" strokeWidth="2" /><path d="M14 14h12m-12 6h12m-12 6h7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></>}
  </svg>;
}

export default function GameSummaryCard({ game, topicName, compact = false }: { game: GameHistorySummary; topicName: string; compact?: boolean }) {
  // INMUNOQUEST is the retained internal name of the board format. TRIVIAL
  // sessions belong to the earlier individual questionnaire, never the board.
  const mode = String(game.game_mode);
  const name = mode === "PASAPALABRA" ? "Pasapalabra" : mode === "INMUNOQUEST" ? "Trivial" : mode === "TRIVIAL" ? "Trivial individual" : "Juego no identificado";
  const saved = game.content_context;
  const academic = saved?.academic;
  const context = describeContentContext(saved);
  const summary = gameSummary(game);
  const knownCount = (value: number | null | undefined): value is number => Number.isInteger(value) && value! >= 0;
  const correct = knownCount(summary.correct) ? summary.correct : null;
  const errors = knownCount(summary.errors) ? summary.errors : null;
  const pending = game.shared_match_id != null && knownCount(game.pending_count) ? game.pending_count : null;
  const date = new Date(game.created_at);
  const dateLabel = Number.isNaN(date.getTime()) ? "Fecha no disponible" : new Intl.DateTimeFormat("es-ES", { dateStyle: "medium", timeZone: "Atlantic/Canary" }).format(date);
  const subjectLine = [academic?.subject_name, academic?.academic_year?.replace("-", "–")].filter(Boolean).join(" · ");
  const originalTopic = academic?.topic_name || saved?.topic_name;
  const topicLine = [originalTopic, context?.difficulty].filter(Boolean).join(" · ");
  const legacyLine = !academic?.edition_id ? [academic?.block_name, academic?.category_name || context?.category].filter((label, index, all) => label && label !== originalTopic && all.indexOf(label) === index).join(" · ") : "";
  const finished = game.is_completed || game.match_status === "FINISHED";
  const status = game.completion_reason === "ABANDONMENT" ? "Finalizada por abandono" : finished ? "Completada" : game.shared_match_id != null && game.match_status === "RUNNING" ? "En curso" : "Sin finalizar";

  return <article className={`min-w-0 rounded-2xl border border-slate-200 bg-white shadow-sm ${compact ? "p-4" : "p-5"}`}>
    <div className="flex min-w-0 items-center gap-3">
      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-sky-50 text-blue-900"><GameIcon name={name} /></span>
      <h2 className="min-w-0 break-words text-xl font-bold leading-7 text-blue-950">{name}</h2>
    </div>
    <p className="mt-4 flex flex-wrap gap-x-2 gap-y-1 text-base font-bold leading-6">
      {correct !== null && <span className="text-emerald-800">{correct} {correct === 1 ? "acierto" : "aciertos"}</span>}
      {errors !== null && <span className="text-red-800">{correct !== null && <span aria-hidden="true">· </span>}{errors} {errors === 1 ? "fallo" : "fallos"}</span>}
      {pending !== null && <span className="text-slate-700">{(correct !== null || errors !== null) && <span aria-hidden="true">· </span>}{pending} {pending === 1 ? "pendiente" : "pendientes"}</span>}
      {correct === null && errors === null && <span className="text-slate-600">{finished ? "Resultado no registrado" : "Sin puntuación disponible"}</span>}
    </p>
    <p className="mt-2 text-sm leading-5 text-slate-600">{status} · {dateLabel}</p>
    <div className="mt-3 space-y-1 text-sm leading-5 text-slate-600">
      {subjectLine && <p className="break-words">{subjectLine}</p>}
      {topicLine && <p className="break-words">{topicLine}</p>}
      {legacyLine && <p className="break-words">{legacyLine}</p>}
      {!originalTopic && <p className="break-words">{game.topic_id === null ? "Temática histórica no disponible" : `${topicName} · Catálogo actual; nombre original no registrado`}</p>}
      {!context && <p>Clasificación histórica no disponible</p>}
    </div>
    {(game.is_completed || game.shared_match_id != null) && <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1">
      <Link href={`/partidas/${game.id}`} className="text-link inline-flex min-h-11 items-center text-sm">Revisar respuestas</Link>
      {game.shared_match_id != null && <Link className="text-link inline-flex min-h-11 items-center text-sm" href={`/pasapalabra/${game.shared_match_id}`}>{game.match_status === "RUNNING" ? game.format_key === "pasapalabra-online-v1" ? "Reanudar partida en línea" : "Reanudar partida local" : "Ver enfrentamiento"}</Link>}
    </div>}
  </article>;
}
