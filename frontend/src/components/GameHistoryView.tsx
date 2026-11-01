"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import Brand from "@/components/Brand";
import GameReview from "@/components/GameReview";
import { describeContentContext, historyReviewItems } from "@/lib/game-review";
import { getGameHistoryDetail, getTopics, type GameHistoryDetail } from "@/services/api";

type LoadState = "loading" | "ready" | "unavailable" | "error";

export default function GameHistoryView({ sessionId }: { sessionId: number | null }) {
  const router = useRouter();
  const [state, setState] = useState<LoadState>(sessionId === null ? "unavailable" : "loading");
  const [game, setGame] = useState<GameHistoryDetail | null>(null);
  const [topicName, setTopicName] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (sessionId === null) return;
    if (!window.localStorage.getItem("token")) {
      router.replace("/login");
      return;
    }
    let active = true;
    async function load() {
      const [gameResult, topicsResult] = await Promise.allSettled([
        getGameHistoryDetail(sessionId as number), getTopics(),
      ]);
      if (!active || !window.localStorage.getItem("token")) return;
      if (gameResult.status === "rejected") {
        const status = isAxiosError(gameResult.reason) ? gameResult.reason.response?.status : undefined;
        if (status === 401) return; // The shared client redirects rejected sessions.
        setState(status === 403 || status === 404 ? "unavailable" : "error");
        return;
      }
      setGame(gameResult.value);
      setTopicName(topicsResult.status === "fulfilled"
        ? topicsResult.value.find((topic) => topic.id === gameResult.value.topic_id)?.name ?? null
        : null);
      setState("ready");
    }
    void load();
    return () => { active = false; };
  }, [router, sessionId, attempt]);

  function logout() {
    window.localStorage.removeItem("token");
    router.replace("/login");
  }

  const mode = game?.game_mode === "PASAPALABRA" ? "Pasapalabra" : "Trivial";
  const context = game ? describeContentContext(game.content_context) : null;
  const date = game ? new Date(game.created_at) : null;
  const dateLabel = date && !Number.isNaN(date.getTime())
    ? new Intl.DateTimeFormat("es-ES", { dateStyle: "long", timeStyle: "short", timeZone: "Atlantic/Canary" }).format(date)
    : "Fecha no disponible";
  const answers = game?.is_completed ? historyReviewItems(game) : [];

  return <div className="min-h-screen bg-background text-slate-900">
    <header className="site-header">
      <nav aria-label="Partida anterior" className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-5 sm:px-8 lg:px-12">
        <Brand />
        <button onClick={logout} className="button-primary">Cerrar sesión</button>
      </nav>
    </header>
    <main className="mx-auto max-w-3xl px-5 py-10 sm:px-8 sm:py-14" aria-busy={state === "loading"}>
      <Link href="/dashboard" className="text-link inline-flex min-h-11 items-center">← Volver al panel</Link>
      <p className="mt-6 text-xs font-bold uppercase tracking-widest text-orange-700">Tu historial de práctica</p>
      <h1 className="mt-3 text-3xl font-black tracking-tight text-blue-950 sm:text-4xl">Detalle de partida</h1>
      <section aria-label="Partida anterior" className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 sm:p-8">
        {state === "loading" && <p role="status" className="text-slate-600">Cargando partida…</p>}
        {state === "unavailable" && <p role="alert" className="notice-warning">Esta partida no está disponible para tu cuenta.</p>}
        {state === "error" && <>
          <p role="alert" className="notice-error">No se pudo consultar la partida. Comprueba la conexión e inténtalo de nuevo.</p>
          <button onClick={() => { setState("loading"); setAttempt((value) => value + 1); }} className="button-secondary mt-4">Reintentar</button>
        </>}
        {state === "ready" && game && <>
          <p className="text-xs font-bold uppercase tracking-widest text-sky-800">{game.is_completed ? "Partida completada" : "Sin finalizar"}</p>
          <h2 className="mt-3 text-2xl font-black text-blue-950">{mode}</h2>
          <dl className="mt-6 grid gap-4 text-sm sm:grid-cols-2">
            <div><dt className="font-semibold text-slate-600">Temática</dt><dd className="mt-1 break-words text-blue-950">{topicName ?? `Temática ${game.topic_id}`}</dd></div>
            <div><dt className="font-semibold text-slate-600">Fecha de inicio</dt><dd className="mt-1 text-blue-950">{dateLabel}</dd></div>
            <div><dt className="font-semibold text-slate-600">Puntuación</dt><dd className="mt-1 text-blue-950">{game.is_completed ? `${game.score} de ${game.question_ids.length} aciertos` : "No disponible: partida sin finalizar"}</dd></div>
          </dl>
          {context ? <dl className="mt-6 grid gap-4 border-t border-slate-200 pt-6 text-sm sm:grid-cols-2">
            <div><dt className="font-semibold text-slate-600">Categoría al iniciar</dt><dd className="mt-1 break-words text-blue-950">{context.category}</dd></div>
            <div><dt className="font-semibold text-slate-600">Dificultad al iniciar</dt><dd className="mt-1 text-blue-950">{context.difficulty}</dd></div>
          </dl> : <p className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600">Esta partida es anterior al registro del contexto de categoría y dificultad; no consta esa clasificación histórica.</p>}
          {!game.is_completed ? <p className="mt-8 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-700">La partida quedó sin finalizar. No hay una corrección guardada ni se puede reanudar desde aquí.</p>
            : <>
              {(answers.length === 0 || answers.length < game.question_ids.length) && <p className="mt-8 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-700">{answers.length === 0 ? "Esta partida no conserva respuestas detalladas; no es posible mostrar su corrección." : `Solo se conservan ${answers.length} de ${game.question_ids.length} respuestas detalladas.`}</p>}
              <GameReview items={answers} />
            </>}
        </>}
      </section>
    </main>
  </div>;
}
