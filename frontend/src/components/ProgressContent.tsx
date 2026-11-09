import Link from "next/link";
import BestMarkCard from "@/components/BestMarkCard";
import EvolutionSection from "@/components/EvolutionSection";
import type { ActivityCounts, GameProgress } from "@/services/api";

const items: { key: keyof ActivityCounts; label: string; help: string; icon: string }[] = [
  { key: "started", label: "Iniciadas", help: "Partidas que has comenzado.", icon: "▶" },
  { key: "completed", label: "Completadas", help: "Partidas con resultado guardado.", icon: "✓" },
  { key: "unfinished", label: "Sin finalizar", help: "Partidas iniciadas que aún no tienen resultado.", icon: "○" },
];

function Counts({ counts, compact = false }: { counts: ActivityCounts; compact?: boolean }) {
  return <div className="grid gap-3 sm:grid-cols-3">
    {items.map(({ key, label, help, icon }) => <div key={key} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <span aria-hidden="true" className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-100 font-bold text-sky-900">{icon}</span>
      <p className="mt-3 text-3xl font-black text-blue-950">{counts[key]}</p>
      <h3 className="mt-1 font-bold text-blue-950">{label}</h3>
      {!compact && <p className="mt-1 text-sm text-slate-600">{help}</p>}
    </div>)}
  </div>;
}

export default function ProgressContent({ progress }: { progress: GameProgress }) {
  return <>
    {progress.started === 0 && <div className="mt-6 rounded-2xl border border-sky-200 bg-sky-50 p-5"><p className="font-semibold text-blue-950">Todavía no has iniciado ninguna partida.</p><Link href="/dashboard" className="text-link mt-2 inline-flex min-h-11 items-center">Elegir juego →</Link></div>}
    <section aria-labelledby="activity-heading" className="mt-7"><h2 id="activity-heading" className="mb-4 text-xl font-bold text-blue-950">Resumen de actividad</h2><Counts counts={progress} /></section>
    <section aria-labelledby="modes-heading" className="mt-9"><h2 id="modes-heading" className="text-xl font-bold text-blue-950">Por modalidad</h2><div className="mt-4 grid gap-5 lg:grid-cols-2">{(["TRIVIAL", "PASAPALABRA"] as const).map((mode) => <div key={mode} className="rounded-2xl border border-slate-200 bg-sky-50 p-4"><h3 className="mb-3 text-lg font-bold text-blue-950">{mode === "TRIVIAL" ? "Trivial" : "Pasapalabra"}</h3>{mode === "PASAPALABRA" && <p className="mb-3 text-sm text-slate-600">Estos recuentos describen únicamente tu actividad registrada, no los resultados de tus rivales.</p>}<Counts counts={progress.by_mode[mode]} compact /></div>)}</div></section>
    <section aria-labelledby="marks-heading" className="mt-9">
      <h2 id="marks-heading" className="text-xl font-bold text-blue-950">Mis mejores marcas</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Se comparan partidas de la misma modalidad, temática, categoría, nivel y cantidad de preguntas. Cada marca usa el nombre de temática conservado en su partida; si no consta, se indica el catálogo actual.</p>
      {progress.best_marks.length === 0 ? <p className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 text-slate-600">Todavía no hay partidas con clasificación suficiente para calcular tus mejores marcas.</p>
        : <ul className="mt-5 grid gap-4 md:grid-cols-2">{progress.best_marks.map((mark) => <li key={`${mark.game_mode}-${mark.topic_id}-${mark.category_id}-${mark.difficulty}-${mark.total_questions}-${mark.format_key ?? "legacy"}-${mark.academic?.subject_id ?? "legacy"}-${mark.academic?.block_id ?? "legacy"}`}><BestMarkCard mark={mark} /></li>)}</ul>}
    </section>
    <EvolutionSection marks={progress.best_marks} />
  </>;
}
