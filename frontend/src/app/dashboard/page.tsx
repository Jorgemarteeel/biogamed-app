"use client";

import Brand from "@/components/Brand";
import GamePicker from "@/components/GamePicker";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
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
            {user && <span className="min-w-0 max-w-48 truncate text-sm font-semibold text-sky-100" title={user.email}>{user.name || user.email}</span>}
            <button onClick={logout} className="button-primary shrink-0">
              Cerrar sesión
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-10 sm:px-8 sm:py-14 lg:px-12" aria-busy={loading}>
        <div className="mb-10">
          <p className="text-xs font-bold uppercase tracking-widest text-orange-700">Tu espacio de aprendizaje</p>
          <h1 className="mt-3 break-words text-3xl font-black tracking-tight text-blue-950 sm:text-4xl">
            {user ? `Hola, ${user.name || user.email}` : "Panel de estudio"}
          </h1>
          <p className="mt-3 max-w-2xl leading-7 text-slate-600">Elige tu juego y después la temática que quieres practicar.</p>
        </div>

        {loading ? (
          <div role="status" className="rounded-2xl border border-slate-200 bg-white p-8 text-slate-600">
            Cargando tu panel…
          </div>
        ) : (
          <div className="grid items-start gap-8 xl:grid-cols-[minmax(0,1fr)_320px]">
            <section className="min-w-0" aria-label="Selección de juego y temática">
              {error ? (
                <div className="rounded-2xl border border-red-200 bg-white p-6">
                  <p role="alert" className="notice-error">{error}</p>
                  <button onClick={retry} className="button-secondary mt-4">Volver a intentar</button>
                </div>
              ) : user ? <GamePicker /> : null}
            </section>

            {user && (
              <aside aria-labelledby="history-heading" className="rounded-2xl border border-slate-200 bg-white p-6 text-blue-950">
                <p className="text-xs font-bold uppercase tracking-widest text-sky-800">Paso a paso</p>
                <h2 id="history-heading" className="mt-2 text-xl font-bold">Tus últimas partidas</h2>
                {historyError ? (
                  <div className="mt-4">
                    <p role="alert" className="notice-error">{historyError}</p>
                    <button onClick={retry} className="text-link mt-3 min-h-11">Reintentar</button>
                  </div>
                ) : games.length === 0 ? (
                  <p className="mt-4 text-sm leading-7 text-slate-600">Aún no has iniciado ninguna partida. Cuando juegues, podrás consultar aquí tus resultados recientes.</p>
                ) : (
                  <ul className="mt-5 space-y-4">
                    {games.map((game) => (
                      <li key={game.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                        <p className="font-bold">{game.game_mode === "TRIVIAL" ? "Trivial" : "Pasapalabra"}</p>
                        <p className="mt-1 break-words text-sm text-slate-600">{topics.find((topic) => topic.id === game.topic_id)?.name || `Temática ${game.topic_id}`}</p>
                        <p className="mt-3 text-sm font-semibold text-sky-800">{game.is_completed ? `${game.score} de ${game.question_ids.length} aciertos` : "Sin finalizar"}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </aside>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
