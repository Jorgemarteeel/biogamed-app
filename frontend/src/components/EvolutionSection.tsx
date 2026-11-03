"use client";

import { useState } from "react";
import Link from "next/link";
import type { PersonalBestMark } from "@/services/api";

function groupLabel(mark: PersonalBestMark) {
  const topic = mark.topic_name ?? `Temática ${mark.topic_id}`;
  const category = mark.category_name ?? `Categoría ${mark.category_id}`;
  return `${mark.game_mode === "TRIVIAL" ? "Trivial" : "Pasapalabra"} · ${topic}${topic === category ? "" : ` · Categoría ${category}`} · Nivel ${mark.difficulty} · ${mark.total_questions} ${mark.total_questions === 1 ? "pregunta" : "preguntas"}`;
}

function dateLabel(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Fecha no disponible" : new Intl.DateTimeFormat("es-ES", { dateStyle: "medium", timeZone: "Atlantic/Canary" }).format(date);
}

export default function EvolutionSection({ marks }: { marks: PersonalBestMark[] }) {
  const [selected, setSelected] = useState(0);
  const mark = marks[Math.min(selected, marks.length - 1)];
  const points = mark?.results ?? [];
  const chartWidth = Math.max(360, 100 + (points.length - 1) * 68);
  const coordinates = points.map((result, index) => ({
    x: 58 + index * 68,
    y: 42 + (mark.total_questions - result.score) * 112 / mark.total_questions,
  }));

  return <section aria-labelledby="evolution-heading" className="mt-9">
    <h2 id="evolution-heading" className="text-xl font-bold text-blue-950">Evolución de resultados</h2>
    <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Se comparan partidas similares. Las puntuaciones pueden variar por las preguntas y la repetición; una subida no demuestra por sí sola una mejora del aprendizaje.</p>
    {marks.length === 0 ? <p className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 text-slate-600">Todavía no hay resultados comparables para mostrar.</p> : <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      {marks.length > 1 && <div className="mb-4"><label htmlFor="evolution-group" className="block font-semibold text-blue-950">Grupo de partidas</label><select id="evolution-group" className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-700" value={selected} onChange={(event) => setSelected(Number(event.target.value))}>{marks.map((item, index) => <option key={`${item.game_mode}-${item.topic_id}-${item.category_id}-${item.difficulty}-${item.total_questions}`} value={index}>{groupLabel(item)}</option>)}</select></div>}
      <h3 className="font-bold leading-7 text-blue-950">{groupLabel(mark)}</h3>
      {mark.category_name_source === "current" && <p className="mt-1 text-sm text-slate-600">El nombre de categoría corresponde al catálogo actual.</p>}
      {mark.category_name_source === null && <p className="mt-1 text-sm text-slate-600">El nombre de categoría no está disponible.</p>}
      {points.length > 1 ? <div className="mt-5">
        <div className="max-w-full overflow-x-auto" role="region" aria-label="Gráfica de evolución; desplaza para ver todas las partidas">
        <svg viewBox={`0 0 ${chartWidth} 205`} style={{ width: chartWidth, minWidth: "100%" }} className="block h-auto" role="img" aria-label={`Resultados de ${points.length} partidas en orden de inicio, de 0 a ${mark.total_questions} aciertos. La lista siguiente detalla cada punto.`}>
          <text x="8" y="22" fill="#334155" fontSize="13">Aciertos</text>
          <line x1="50" y1="42" x2="50" y2="154" stroke="#64748b" strokeWidth="2" />
          <line x1="50" y1="154" x2={chartWidth - 20} y2="154" stroke="#64748b" strokeWidth="2" />
          <text x="12" y="47" fill="#334155" fontSize="13">{mark.total_questions}</text>
          <text x="28" y="159" fill="#334155" fontSize="13">0</text>
          <polyline points={coordinates.map((point) => `${point.x},${point.y}`).join(" ")} fill="none" stroke="#0369a1" strokeWidth="3" />
          {coordinates.map((point, index) => <g key={points[index].session_id}><circle cx={point.x} cy={point.y} r="6" fill="#0f766e" stroke="white" strokeWidth="2" /><text x={point.x} y={Math.max(34, point.y - 12)} textAnchor="middle" fill="#0f172a" fontSize="12" fontWeight="bold">{points[index].score}/{mark.total_questions}</text><text x={point.x} y="176" textAnchor="middle" fill="#334155" fontSize="12">{index + 1}</text></g>)}
          <text x={chartWidth / 2} y="199" textAnchor="middle" fill="#334155" fontSize="13">Partida (número en la lista)</text>
        </svg>
        </div>
      </div> : <p className="mt-4 text-sm font-semibold text-sky-800">Hace falta otra partida comparable para observar una evolución.</p>}
      <ol className="mt-5 space-y-3" aria-label="Resultados en orden de inicio">{points.map((result, index) => <li key={result.session_id} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 rounded-xl bg-sky-50 px-4 py-3 text-sm"><span><span className="font-bold text-blue-950">{index + 1}. {result.score} de {result.total_questions} aciertos</span> · Inicio: {dateLabel(result.started_at)}</span><Link href={`/partidas/${result.session_id}`} className="text-link inline-flex min-h-11 items-center">Revisar resultado</Link></li>)}</ol>
    </div>}
  </section>;
}
