import Image from "next/image";
import Link from "next/link";
import { topicIllustration } from "@/lib/topic-presentation";
import type { PersonalBestMark } from "@/services/api";

export default function BestMarkCard({ mark }: { mark: PersonalBestMark }) {
  const topic = mark.topic_name ?? `Temática ${mark.topic_id}`;
  const category = mark.category_name ?? `Categoría ${mark.category_id}`;
  const showCategory = category !== topic;
  const date = new Date(mark.started_at);
  const dateLabel = Number.isNaN(date.getTime()) ? "Fecha no disponible" : new Intl.DateTimeFormat("es-ES", { dateStyle: "medium", timeZone: "Atlantic/Canary" }).format(date);

  return <article className="h-full rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <div className="flex min-w-0 items-start gap-4">
      <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-sky-50 p-2"><Image src={topicIllustration(mark.topic_name ?? "")} alt="" width={64} height={64} className="h-full w-full object-contain" /></span>
      <div className="min-w-0">
        <h3 className="break-words text-lg font-bold text-blue-950">{topic}</h3>
        <p className="mt-1 text-sm text-slate-600">{mark.game_mode === "TRIVIAL" ? "Trivial" : "Pasapalabra"} · Nivel {mark.difficulty} · {mark.total_questions} {mark.total_questions === 1 ? "pregunta" : "preguntas"}</p>
        {showCategory && <p className="mt-1 break-words text-sm text-slate-600">Categoría: {category}{mark.category_name_source === "current" ? " (nombre actual)" : mark.category_name_source === null ? " (nombre no disponible)" : ""}</p>}
      </div>
    </div>
    <p className="mt-4 text-2xl font-black text-blue-950">{mark.best_score} de {mark.total_questions} aciertos</p>
    <p className="mt-1 text-sm text-slate-600">Partida iniciada el {dateLabel} · {mark.valid_results} {mark.valid_results === 1 ? "partida válida" : "partidas válidas"} en este grupo</p>
    {mark.tied_best_results > 1 && <p className="mt-2 text-sm font-semibold text-sky-800">Mejor marca empatada en {mark.tied_best_results} partidas</p>}
    <Link href={`/partidas/${mark.session_id}`} className="text-link mt-3 inline-flex min-h-11 items-center">Revisar partida →</Link>
  </article>;
}
