"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import Brand from "@/components/Brand";
import GameSummaryCard from "@/components/GameSummaryCard";
import { HISTORY_PAGE_SIZE, visibleHistoryPage } from "@/lib/history-pagination";
import { getCurrentUser, getHistoryPage, getTopics, type GameHistorySummary, type Topic } from "@/services/api";

export default function HistoryView({ page }: { page: number }) {
  const router = useRouter();
  const [games, setGames] = useState<GameHistorySummary[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!window.localStorage.getItem("token")) { router.replace("/login"); return; }
    let active = true;
    async function load() {
      try {
        await getCurrentUser();
        const [history, topicResult] = await Promise.all([getHistoryPage((page - 1) * HISTORY_PAGE_SIZE, HISTORY_PAGE_SIZE + 1), getTopics().catch(() => [])]);
        if (!active || !window.localStorage.getItem("token")) return;
        const visible = visibleHistoryPage(history);
        setGames(visible.items);
        setHasMore(visible.hasMore);
        setTopics(topicResult);
        setState("ready");
      } catch (error) {
        if (!active) return;
        if (isAxiosError(error) && error.response?.status === 401) return;
        setState("error");
      }
    }
    void load();
    return () => { active = false; };
  }, [router, page, attempt]);

  return <div className="min-h-screen bg-background text-slate-900">
    <header className="site-header"><nav aria-label="Historial" className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-5 sm:px-8"><Brand /><button className="button-primary" onClick={() => { window.localStorage.removeItem("token"); router.replace("/login"); }}>Cerrar sesión</button></nav></header>
    <main className="mx-auto max-w-5xl px-5 py-8 sm:px-8 sm:py-12" aria-busy={state === "loading"}>
      <Link href="/dashboard" className="text-link inline-flex min-h-11 items-center">← Volver al panel</Link>
      <h1 className="mt-5 text-3xl font-black text-blue-950">Mi historial</h1>
      {state === "loading" && <p role="status" className="mt-6 rounded-2xl bg-white p-6">Cargando partidas…</p>}
      {state === "error" && <div className="mt-6"><p role="alert" className="notice-error">No se pudo consultar el historial. Comprueba la conexión e inténtalo de nuevo.</p><button className="button-secondary mt-4" onClick={() => { setState("loading"); setAttempt((value) => value + 1); }}>Reintentar</button></div>}
      {state === "ready" && <>
        {games.length === 0 ? <p className="mt-6 rounded-2xl bg-white p-6 text-slate-600">{page === 1 ? "Todavía no tienes partidas." : "No hay partidas en esta página."}</p>
          : <ol className="mt-6 grid gap-4 sm:grid-cols-2">{games.map((game) => <li key={game.id}><GameSummaryCard game={game} topicName={topics.find((topic) => topic.id === game.topic_id)?.name ?? `Temática ${game.topic_id}`} /></li>)}</ol>}
        <nav aria-label="Páginas del historial" className="mt-8 flex flex-wrap items-center justify-between gap-4">
          {page > 1 ? <Link href={page === 2 ? "/historial" : `/historial?page=${page - 1}`} className="button-secondary">Anterior</Link> : <span />}
          <span className="text-sm font-semibold text-slate-600">Página {page}</span>
          {hasMore && <Link href={`/historial?page=${page + 1}`} className="button-secondary">Siguiente</Link>}
        </nav>
      </>}
    </main>
  </div>;
}
