"use client";

import Brand from "@/components/Brand";
import ProfileMenu from "@/components/ProfileMenu";
import GamePicker from "@/components/GamePicker";
import GameSummaryCard from "@/components/GameSummaryCard";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import Link from "next/link";
import { canManageSubjects } from "@/lib/subjects";
import {
  getCurrentUser, getRecentGames, getTopics,
  type GameHistorySummary, type Topic, type UserResponse,
} from "@/services/api";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserResponse | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [games, setGames] = useState<GameHistorySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [historyOpen, setHistoryOpen] = useState(false);

  useEffect(() => {
    if (!window.localStorage.getItem("token")) {
      router.replace("/login");
      return;
    }
    let active = true;
    async function loadDashboard() {
      try {
        // Validate the token before displaying the authenticated area.
        const currentUser = await getCurrentUser();
        if (!active) return;
        setUser(currentUser);
        const [topicResult, historyResult] = await Promise.allSettled([
          getTopics(), getRecentGames(),
        ]);
        if (!active || !window.localStorage.getItem("token")) return;
        if (topicResult.status === "fulfilled") {
          setTopics(topicResult.value);
        } else {
          // This list only labels the history; the picker loads its own filtered topics.
          setTopics([]);
        }
        if (historyResult.status === "fulfilled") {
          setGames(historyResult.value);
        } else {
          setHistoryError("No se pudo cargar tu historial.");
        }
        setLoading(false);
      } catch (err: unknown) {
        if (!active) return;
        // The shared interceptor clears rejected tokens and redirects to login.
        if (isAxiosError(err) && err.response?.status === 401) return;
        setError("No se pudo verificar tu sesión. Comprueba la conexión e inténtalo de nuevo.");
        setLoading(false);
      }
    }
    void loadDashboard();
    return () => { active = false; };
  }, [router, attempt]);

  function retry() {
    setLoading(true);
    setError("");
    setHistoryError("");
    setAttempt((value) => value + 1);
  }

  function logout() {
    window.localStorage.removeItem("token");
    setUser(null);
    setTopics([]);
    setGames([]);
    setLoading(true);
    router.replace("/login");
  }

  return (
    <div className="min-h-screen bg-background font-sans text-slate-900">
      <header className="site-header">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-5 sm:px-8 lg:px-12">
          <Brand />
          <div className="flex w-full min-w-0 items-center justify-between gap-4 sm:w-auto">
            <ProfileMenu name={user?.name} />
            <button onClick={logout} className="button-primary shrink-0">
              Cerrar sesión
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8 sm:py-10 lg:px-12" aria-busy={loading}>
        <div className="mb-6">
          <p className="text-xs font-bold uppercase tracking-widest text-orange-700">Tu espacio de aprendizaje</p>
          <h1 className="mt-3 break-words text-3xl font-black tracking-tight text-blue-950 sm:text-4xl">
            {user ? `Hola, ${user.name || user.email}` : "Panel de estudio"}
          </h1>
          <p className="mt-2 max-w-2xl leading-7 text-slate-600">Elige tu juego y después la temática que quieres practicar.</p>
          {user && <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1">
            {canManageSubjects(user.role) && <Link href="/gestion/asignaturas" className="text-link inline-flex min-h-11 items-center">Gestión de contenidos →</Link>}
          </div>}
        </div>

        {loading ? (
          <div role="status" className="rounded-2xl border border-slate-200 bg-white p-8 text-slate-600">
            Cargando tu panel…
          </div>
        ) : (
          <div className="space-y-8">
            <section className="min-w-0" aria-label="Selección de juego y temática">
              {error ? (
                <div className="rounded-2xl border border-red-200 bg-white p-6">
                  <p role="alert" className="notice-error">{error}</p>
                  <button onClick={retry} className="button-secondary mt-4">Volver a intentar</button>
                </div>
              ) : user ? <GamePicker /> : null}
            </section>

            {user && (
              <section aria-labelledby="history-heading" className="rounded-2xl border border-slate-200 bg-white text-blue-950">
                <h2 id="history-heading"><button type="button" aria-expanded={historyOpen} aria-controls="recent-games" onClick={() => setHistoryOpen((value) => !value)} className="flex min-h-16 w-full items-center justify-between gap-4 rounded-2xl px-6 py-4 text-left text-xl font-bold hover:bg-sky-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700">
                  <span>Mis últimas partidas</span><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className={`h-6 w-6 shrink-0 transition-transform ${historyOpen ? "rotate-180" : ""}`}><path d="m5 9 7 7 7-7" /></svg>
                </button></h2>
                <div id="recent-games" hidden={!historyOpen} className="border-t border-slate-200 px-6 pb-6">
                {historyError ? (
                  <div className="mt-4">
                    <p role="alert" className="notice-error">{historyError}</p>
                    <button onClick={retry} className="text-link mt-3 min-h-11">Reintentar</button>
                  </div>
                ) : games.length === 0 ? (
                  <p className="mt-4 text-sm leading-7 text-slate-600">Aún no has iniciado ninguna partida. Cuando juegues, podrás consultar aquí tus resultados recientes.</p>
                ) : (
                  <ul className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {games.map((game) => (
                      <li key={game.id}><GameSummaryCard game={game} topicName={topics.find((topic) => topic.id === game.topic_id)?.name ?? `Temática ${game.topic_id}`} compact /></li>
                    ))}
                  </ul>
                )}
                <Link href="/historial" className="text-link mt-5 inline-flex min-h-11 items-center">Ver todo el historial →</Link>
                </div>
              </section>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
