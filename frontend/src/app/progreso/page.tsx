"use client";

import { useEffect, useState } from "react";
import { isAxiosError } from "axios";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Brand from "@/components/Brand";
import { getCurrentUser, getGameProgress, type ActivityCounts, type GameProgress } from "@/services/api";

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

export default function ProgressPage() {
  const router = useRouter();
  const [progress, setProgress] = useState<GameProgress | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!window.localStorage.getItem("token")) { router.replace("/login"); return; }
    let active = true;
    async function load() {
      try {
        await getCurrentUser();
        const result = await getGameProgress();
        if (!active || !window.localStorage.getItem("token")) return;
        setProgress(result);
        setState("ready");
      } catch (error) {
        if (!active) return;
        if (isAxiosError(error) && error.response?.status === 401) return;
        setState("error");
      }
    }
    void load();
    return () => { active = false; };
  }, [router, attempt]);

  return <div className="min-h-screen bg-background text-slate-900">
    <header className="site-header"><nav aria-label="Progreso" className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-5 sm:px-8"><Brand /><button className="button-primary" onClick={() => { window.localStorage.removeItem("token"); router.replace("/login"); }}>Cerrar sesión</button></nav></header>
    <main className="mx-auto max-w-5xl px-5 py-8 sm:px-8 sm:py-12" aria-busy={state === "loading"}>
      <Link href="/dashboard" className="text-link inline-flex min-h-11 items-center">← Volver al panel</Link>
      <h1 className="mt-5 text-3xl font-black text-blue-950">Mi progreso</h1>
      <p className="mt-2 text-slate-600">Tu actividad en BioGaMed. Estos recuentos no indican aciertos.</p>
      {state === "loading" && <p role="status" className="mt-6 rounded-2xl bg-white p-6">Cargando actividad…</p>}
      {state === "error" && <div className="mt-6"><p role="alert" className="notice-error">No se pudo consultar tu actividad. Comprueba la conexión e inténtalo de nuevo.</p><button className="button-secondary mt-4" onClick={() => { setState("loading"); setAttempt((value) => value + 1); }}>Reintentar</button></div>}
      {state === "ready" && progress && <>
        {progress.started === 0 && <div className="mt-6 rounded-2xl border border-sky-200 bg-sky-50 p-5"><p className="font-semibold text-blue-950">Todavía no has iniciado ninguna partida.</p><Link href="/dashboard" className="text-link mt-2 inline-flex min-h-11 items-center">Elegir juego →</Link></div>}
        <section aria-labelledby="activity-heading" className="mt-7"><h2 id="activity-heading" className="mb-4 text-xl font-bold text-blue-950">Resumen de actividad</h2><Counts counts={progress} /></section>
        <section aria-labelledby="modes-heading" className="mt-9"><h2 id="modes-heading" className="text-xl font-bold text-blue-950">Por modalidad</h2><div className="mt-4 grid gap-5 lg:grid-cols-2">{(["TRIVIAL", "PASAPALABRA"] as const).map((mode) => <div key={mode} className="rounded-2xl border border-slate-200 bg-sky-50 p-4"><h3 className="mb-3 text-lg font-bold text-blue-950">{mode === "TRIVIAL" ? "Trivial" : "Pasapalabra"}</h3>{mode === "PASAPALABRA" && <p className="mb-3 text-sm text-slate-600">En preparación; estos recuentos describen actividad registrada.</p>}<Counts counts={progress.by_mode[mode]} compact /></div>)}</div></section>
      </>}
      <Link href="/historial" className="text-link mt-8 inline-flex min-h-11 items-center">Mi historial →</Link>
    </main>
  </div>;
}
