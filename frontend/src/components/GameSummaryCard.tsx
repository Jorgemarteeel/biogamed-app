import Image from "next/image";
import Link from "next/link";
import { describeContentContext } from "@/lib/game-review";
import { gameSummary } from "@/lib/game-summary";
import { topicIllustration } from "@/lib/topic-presentation";
import type { GameHistorySummary } from "@/services/api";

export default function GameSummaryCard({ game, topicName, compact = false }: { game: GameHistorySummary; topicName: string; compact?: boolean }) {
  topicName = game.content_context?.topic_name ?? topicName;
  const context = describeContentContext(game.content_context);
  const summary = gameSummary(game);
  const date = new Date(game.created_at);
  const dateLabel = Number.isNaN(date.getTime()) ? "Fecha no disponible" : new Intl.DateTimeFormat("es-ES", { dateStyle: "medium", timeZone: "Atlantic/Canary" }).format(date);
  const category = context?.category && context.category !== topicName ? context.category : null;
  const correctLabel = summary.correct === 1 ? "acierto" : "aciertos";
  const errorLabel = summary.errors === 1 ? "error" : "errores";
  const questionLabel = summary.total === 1 ? "pregunta" : "preguntas";

  return <article className={`min-w-0 rounded-2xl border border-slate-200 bg-white shadow-sm ${compact ? "p-4" : "p-5"}`}>
    <div className="flex min-w-0 items-start gap-4">
      <span className={`flex shrink-0 items-center justify-center rounded-xl bg-sky-50 p-2 ${compact ? "h-14 w-14" : "h-16 w-16"}`}><Image src={topicIllustration(topicName)} alt="" width={64} height={64} className="h-full w-full object-contain" /></span>
      <div className="min-w-0 flex-1">
        <h2 className="break-words text-lg font-bold leading-6 text-blue-950">{topicName}</h2>
        <p className="mt-1 text-sm leading-5 text-slate-600">{game.game_mode === "TRIVIAL" ? "Trivial" : "Pasapalabra"} · {dateLabel}</p>
        {!game.content_context?.topic_name && <p className="mt-1 text-xs text-slate-600">Temática del catálogo actual; nombre original no registrado</p>}
        {context?.difficulty && <p className="mt-1 text-sm leading-5 text-slate-600">{context.difficulty}</p>}
        {category && <p className="mt-1 break-words text-sm leading-5 text-slate-600">Categoría: {category}</p>}
        {!context && <p className="mt-1 text-sm leading-5 text-slate-600">Clasificación histórica no disponible</p>}
      </div>
    </div>
    {game.is_completed || game.shared_match_id != null ? <>
      {game.shared_match_id != null && <p className="mt-4 text-sm font-bold text-slate-600">{game.completion_reason === "ABANDONMENT" ? "Finalizada por abandono" : game.match_status === "FINISHED" ? "Finalizada" : "En curso"} · {game.pending_count ?? 0} pendientes</p>}
      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 text-sm font-bold">
        {summary.correct !== null ? <span className="text-emerald-800">✓ {summary.correct} {correctLabel}</span> : <span className="text-slate-600">Aciertos no disponibles</span>}
        {summary.errors !== null && <span className="text-red-800">× {summary.errors} {errorLabel}</span>}
      </div>
      {summary.total !== null && game.shared_match_id == null && <div className="mt-3" role="img" aria-label={`${summary.correct} ${correctLabel} de ${summary.total} ${questionLabel}, ${summary.errors} ${errorLabel}`}>
        <div className="h-1.5 overflow-hidden rounded-full bg-red-200"><div className="h-full rounded-full bg-emerald-600" style={{ width: `${(summary.correct! / summary.total) * 100}%` }} /></div>
      </div>}
      <Link href={`/partidas/${game.id}`} className="text-link mt-3 inline-flex min-h-11 items-center text-sm">Revisar respuestas</Link>{game.shared_match_id != null && <Link className="text-link ml-4 inline-flex min-h-11 items-center text-sm" href={`/pasapalabra/${game.shared_match_id}`}>{game.match_status === "RUNNING" ? game.format_key === "pasapalabra-online-v1" ? "Reanudar partida en línea" : "Reanudar partida local" : "Ver enfrentamiento"}</Link>}
    </> : <p className="mt-4 text-sm font-bold text-slate-600">Sin finalizar · Sin puntuación disponible</p>}
  </article>;
}
