"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import Brand from "@/components/Brand";
import ProfileMenu from "@/components/ProfileMenu";
import TrivialGame from "@/components/TrivialGame";
import {
  getCurrentUser, getTopics, getTrivialAvailability, startTrivialGame,
  type GameAvailability, type GameMode, type GameSessionStart, type TrivialFilters,
} from "@/services/api";

export default function GameStart({ topicId, mode }: {
  topicId: number | null;
  mode: GameMode | null;
}) {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState(false);
  const [authError, setAuthError] = useState("");
  const [authAttempt, setAuthAttempt] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [session, setSession] = useState<GameSessionStart | null>(null);
  const [availability, setAvailability] = useState<GameAvailability | null>(null);
  const [availabilityError, setAvailabilityError] = useState("");
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [availabilityAttempt, setAvailabilityAttempt] = useState(0);
  const [topicName, setTopicName] = useState("");
  const [categoryChoice, setCategoryChoice] = useState("all");
  const [difficultyChoice, setDifficultyChoice] = useState("all");
  const starting = useRef(false);
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  useEffect(() => {
    if (!window.localStorage.getItem("token")) {
      router.replace("/login");
      return;
    }
    let active = true;
    getCurrentUser().then(() => {
      if (active) setAuthenticated(true);
    }).catch((err: unknown) => {
      if (!active || (isAxiosError(err) && err.response?.status === 401)) return;
      setAuthError("No se pudo verificar tu sesión. Comprueba la conexión e inténtalo de nuevo.");
    });
    return () => { active = false; };
  }, [router, authAttempt]);

  useEffect(() => {
    if (!authenticated || topicId === null || mode !== "TRIVIAL") return;
    let active = true;
    Promise.resolve().then(() => {
      if (!active) return null;
      setAvailability(null);
      setAvailabilityError("");
      setAvailabilityLoading(true);
      setTopicName("");
      setCategoryChoice("all");
      setDifficultyChoice("all");
      return Promise.all([getTrivialAvailability(topicId), getTopics("TRIVIAL").catch(() => [])]);
    }).then((response) => {
      if (!response) return;
      const [data, topics] = response;
      if (!active) return;
      if (data.topic_id !== topicId || data.game_mode !== "TRIVIAL") {
        setAvailabilityError("La disponibilidad recibida no corresponde a esta temática.");
        return;
      }
      setAvailability(data);
      setTopicName(topics.find((topic) => topic.id === topicId)?.name ?? "");
    }).catch((err: unknown) => {
      if (!active || (isAxiosError(err) && err.response?.status === 401)) return;
      setAvailabilityError("No se pudo consultar la disponibilidad. Comprueba la conexión e inténtalo de nuevo.");
    }).finally(() => { if (active) setAvailabilityLoading(false); });
    return () => { active = false; };
  }, [authenticated, topicId, mode, availabilityAttempt]);

  const categories = availability
    ? [...new Set(availability.combinations.map((item) => item.category_id))]
    : [];
  const categoryNames = new Map(availability?.combinations.map((item) =>
    [item.category_id, item.category_name] as const) ?? []);
  const categoryLabel = (id: number | null) => id === null
    ? "Sin categoría" : categoryNames.get(id) ?? `Categoría sin nombre (ID ${id})`;
  const selectedCategory = categories.length === 1
    ? categories[0]
    : categoryChoice === "all" ? undefined : Number(categoryChoice);
  const matchingCategory = availability?.combinations.filter((item) =>
    selectedCategory === undefined || item.category_id === selectedCategory) ?? [];
  const levels = [...new Set(matchingCategory.map((item) => item.difficulty)
    .filter((level): level is number => level !== null))].sort((a, b) => a - b);
  const availableCount = matchingCategory
    .filter((item) => difficultyChoice === "all"
      || (difficultyChoice === "unknown" ? item.difficulty === null
        : item.difficulty === Number(difficultyChoice)))
    .reduce((total, item) => total + item.count, 0);
  const filters: TrivialFilters = {
    ...(typeof selectedCategory === "number" ? { category_id: selectedCategory } : {}),
    ...(difficultyChoice === "unknown" ? { difficulty_unknown: true }
      : difficultyChoice === "all" ? {} : { difficulty: Number(difficultyChoice) }),
  };

  async function start() {
    if (!authenticated || topicId === null || mode !== "TRIVIAL" || starting.current
      || session || !availability || availability.topic_id !== topicId || availableCount === 0) return;
    starting.current = true;
    setLoading(true);
    setError("");
    try {
      const result = await startTrivialGame(topicId, filters);
      if (!mounted.current) return;
      if (!result.questions.length || result.questions.some((question) => question.question_type !== "TRIVIAL" || !question.options || question.options.length < 2)) {
        setError("No se han recibido preguntas válidas. Vuelve al panel y elige otra temática.");
        return;
      }
      setSession(result);
    } catch (err: unknown) {
      if (!mounted.current) return;
      const status = isAxiosError(err) ? err.response?.status : undefined;
      if (status === 401) return;
      setError(status === 404
        ? "Esta temática ya no existe. Vuelve al panel y elige otra."
        : status === 409
          ? "Esta combinación ya no tiene preguntas disponibles. Revisa la selección o vuelve a consultar la disponibilidad."
          : "No se pudo cargar la partida. Comprueba la conexión e inténtalo de nuevo.");
    } finally {
      starting.current = false;
      if (mounted.current) setLoading(false);
    }
  }

  function logout() {
    window.localStorage.removeItem("token");
    mounted.current = false;
    setSession(null);
    setAuthenticated(false);
    router.replace("/login");
  }

  return (
    <div className="min-h-screen bg-background text-slate-900">
      <header className="site-header">
        <nav aria-label="Partida" className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-5 sm:px-8 lg:px-12">
          <Brand />
          <div className="flex flex-wrap items-center gap-2"><ProfileMenu /><button onClick={logout} className="button-primary">Cerrar sesión</button></div>
        </nav>
      </header>
      <main className="mx-auto max-w-3xl px-5 py-10 sm:px-8 sm:py-14">
        <Link href="/dashboard" className="text-link inline-flex min-h-11 items-center">← Volver al panel</Link>
        <p className="mt-6 text-xs font-bold uppercase tracking-widest text-orange-700">Tu espacio de práctica</p>
        <h1 className="mt-3 text-3xl font-black tracking-tight text-blue-950 sm:text-4xl">{mode === "PASAPALABRA" ? "Pasapalabra" : mode === "TRIVIAL" ? "Trivial" : "Preparar partida"}</h1>

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 sm:p-8" aria-label="Partida" aria-busy={!authenticated && !authError || loading}>
          {authError ? <>
            <p role="alert" className="notice-error">{authError}</p>
            <button className="button-secondary mt-5" onClick={() => { setAuthError(""); setAuthAttempt((value) => value + 1); }}>Reintentar</button>
          </> : !authenticated ? <p role="status" className="text-slate-600">Comprobando tu sesión…</p>
            : topicId === null || mode === null ? <p role="alert" className="notice-warning">El enlace de la partida no es válido. Vuelve al panel para elegir un juego y una temática.</p>
            : mode === "PASAPALABRA" ? <>
              <h2 className="text-xl font-bold text-blue-950">Pasapalabra está en preparación</h2>
              <p className="mt-3 leading-7 text-slate-600">Todavía no puedes iniciar esta modalidad. Puedes volver al panel para explorar Trivial.</p>
            </> : session ? <TrivialGame session={session} topicName={topicName || `Temática ${topicId}`} /> : <>
              <h2 className="text-xl font-bold text-blue-950">Practica eligiendo una respuesta</h2>
              <p className="mt-3 leading-7 text-slate-600">Temática: {topicName || `Temática ${topicId}`}. Elige el contenido que quieres practicar antes de comenzar.</p>
              <p className="mt-3 text-sm leading-6 text-slate-600">La partida se crea al pulsar «Comenzar partida». Después, si abandonas o recargas antes de terminar, perderás tus selecciones y quedará «Sin finalizar».</p>
              {availabilityLoading && <p role="status" className="mt-5 text-sm text-slate-600">Consultando preguntas disponibles…</p>}
              {availabilityError && <div className="mt-5"><p role="alert" className="notice-error">{availabilityError}</p><button type="button" className="button-secondary mt-3" onClick={() => { setAvailability(null); setAvailabilityLoading(true); setAvailabilityError(""); setAvailabilityAttempt((value) => value + 1); }}>Reintentar consulta</button></div>}
              {availability && <div className="mt-6 grid gap-5 sm:grid-cols-2">
                <div>
                  {categories.length === 1 ? <p className="text-sm font-semibold text-blue-950">Categoría: {categoryLabel(categories[0])}</p>
                    : <><label htmlFor="category-filter" className="block text-sm font-semibold text-blue-950">Categoría</label><select id="category-filter" value={categoryChoice} disabled={loading} onChange={(event) => { setCategoryChoice(event.target.value); setDifficultyChoice("all"); setError(""); }} className="mt-2 min-h-11 w-full rounded-lg border border-slate-400 bg-white px-3">
                      <option value="all">{categories.includes(null) ? "Todas, incluidas sin categoría" : "Todas las categorías"}</option>
                      {categories.filter((id): id is number => id !== null).map((id) => <option key={id} value={id}>{categoryLabel(id)}</option>)}
                    </select></>}
                  {categories.length > 1 && categories.includes(null) && <p className="mt-2 text-xs text-slate-600">Hay preguntas sin categoría; se incluyen al elegir todas.</p>}
                </div>
                <div><label htmlFor="difficulty-filter" className="block text-sm font-semibold text-blue-950">Dificultad</label><select id="difficulty-filter" value={difficultyChoice} disabled={loading} onChange={(event) => { setDifficultyChoice(event.target.value); setError(""); }} className="mt-2 min-h-11 w-full rounded-lg border border-slate-400 bg-white px-3">
                  <option value="all">Sin filtrar dificultad</option>
                  {levels.map((level) => <option key={level} value={level}>Nivel {level}</option>)}
                  {matchingCategory.some((item) => item.difficulty === null) && <option value="unknown">Dificultad sin clasificar</option>}
                </select></div>
              </div>}
              {availability && <p role="status" className="mt-5 font-semibold text-blue-950">{availableCount === 0 ? "No hay preguntas para esta selección." : `Esta partida tendrá ${Math.min(10, availableCount)} ${Math.min(10, availableCount) === 1 ? "pregunta" : "preguntas"}.`}</p>}
              {error && <p role="alert" className="notice-error mt-5">{error}</p>}
              <button onClick={start} disabled={loading || availabilityLoading || !availability || availableCount === 0} className="button-primary mt-6 w-full sm:w-auto">{loading ? "Cargando partida…" : "Comenzar partida"}</button>
              {loading && <p role="status" className="mt-3 text-sm text-slate-600">Buscando tus preguntas…</p>}
            </>}
        </section>
      </main>
    </div>
  );
}
