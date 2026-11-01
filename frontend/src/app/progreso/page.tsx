"use client";

import { useEffect, useState } from "react";
import { isAxiosError } from "axios";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Brand from "@/components/Brand";
import ProgressContent from "@/components/ProgressContent";
import { getCurrentUser, getGameProgress, type GameProgress } from "@/services/api";

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
      {state === "ready" && progress && <ProgressContent progress={progress} />}
      <Link href="/historial" className="text-link mt-8 inline-flex min-h-11 items-center">Mi historial →</Link>
    </main>
  </div>;
}
