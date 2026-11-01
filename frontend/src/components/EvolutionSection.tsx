"use client";

import { useState } from "react";
import Link from "next/link";
import type { PersonalBestMark } from "@/services/api";

function groupLabel(mark: PersonalBestMark) {
  const topic = mark.topic_name ?? `Temática ${mark.topic_id}`;
  const category = mark.category_name ?? `Categoría ${mark.category_id}`;
  return `${mark.game_mode === "TRIVIAL" ? "Trivial" : "Pasapalabra"} · Temática ${topic} · Categoría ${category} · Nivel ${mark.difficulty} · ${mark.total_questions} ${mark.total_questions === 1 ? "pregunta" : "preguntas"}`;
}

function dateLabel(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Fecha no disponible" : new Intl.DateTimeFormat("es-ES", { dateStyle: "medium", timeZone: "Atlantic/Canary" }).format(date);
}

export default function EvolutionSection({ marks }: { marks: PersonalBestMark[] }) {
  const [selected, setSelected] = useState(0);
  const mark = marks[Math.min(selected, marks.length - 1)];
  const points = mark?.results ?? [];
  const coordinates = points.map((result, index) => ({
    x: 35 + index * 290 / (points.length - 1),
    y: 20 + (mark.total_questions - result.score) * 140 / mark.total_questions,
  }));

  return <section aria-labelledby="evolution-heading" className="mt-9">
    <h2 id="evolution-heading" className="text-xl font-bold text-blue-950">Evolución de resultados</h2>
    <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Las puntuaciones pueden variar por las preguntas y la repetición; no demuestran por sí solas una mejora del aprendizaje.</p>
    {marks.length === 0 ? <p className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 text-slate-600">Todavía no hay resultados comparables para mostrar.</p> : <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      {marks.length > 1 && <div className="mb-4"><label htmlFor="evolution-group" className="block font-semibold text-blue-950">Grupo de partidas</label><select id="evolution-group" className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-700" value={selected} onChange={(event) => setSelected(Number(event.target.value))}>{marks.map((item, index) => <option key={`${item.game_mode}-${item.topic_id}-${item.category_id}-${item.difficulty}-${item.total_questions}`} value={index}>{groupLabel(item)}</option>)}</select></div>}
      <h3 className="font-bold leading-7 text-blue-950">{groupLabel(mark)}</h3>
      {mark.category_name_source === "current" && <p className="mt-1 text-sm text-slate-600">El nombre de categoría corresponde al catálogo actual.</p>}
      {mark.category_name_source === null && <p className="mt-1 text-sm text-slate-600">El nombre de categoría no está disponible.</p>}
      {points.length > 1 ? <div className="mt-5">
        <svg viewBox="0 0 360 200" className="mx-auto h-auto w-full max-w-xl" role="img" aria-label={`Resultados de ${points.length} partidas en orden de inicio, de 0 a ${mark.total_questions} aciertos. La lista siguiente detalla cada punto.`}>
          <line x1="35" y1="20" x2="35" y2="160" stroke="#64748b" strokeWidth="2" />
          <line x1="35" y1="160" x2="325" y2="160" stroke="#64748b" strokeWidth="2" />
          <text x="6" y="25" fill="#334155" fontSize="14">{mark.total_questions}</text>
          <text x="16" y="165" fill="#334155" fontSize="14">0</text>
          <polyline points={coordinates.map((point) => `${point.x},${point.y}`).join(" ")} fill="none" stroke="#0369a1" strokeWidth="3" />
          {coordinates.map((point, index) => <circle key={points[index].session_id} cx={point.x} cy={point.y} r="6" fill="#0f766e" stroke="white" strokeWidth="2" />)}
          <text x="180" y="190" textAnchor="middle" fill="#334155" fontSize="13">Partidas en orden de inicio</text>
        </svg>
      </div> : <p className="mt-4 text-sm font-semibold text-sky-800">Hace falta otra partida comparable para observar una evolución.</p>}
      <ol className="mt-5 space-y-3" aria-label="Resultados en orden de inicio">{points.map((result, index) => <li key={result.session_id} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 rounded-xl bg-sky-50 px-4 py-3 text-sm"><span><span className="font-bold text-blue-950">{index + 1}. {result.score} de {result.total_questions} aciertos</span> · Inicio: {dateLabel(result.started_at)}</span><Link href={`/partidas/${result.session_id}`} className="text-link inline-flex min-h-11 items-center">Revisar resultado</Link></li>)}</ol>
    </div>}
  </section>;
}
