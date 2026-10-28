"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import Brand from "@/components/Brand";
import {
  getCurrentUser, startTrivialGame,
  type GameMode, type GameSessionStart,
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
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const starting = useRef(false);
  const mounted = useRef(false);
  const questionHeading = useRef<HTMLHeadingElement>(null);

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
    if (session) questionHeading.current?.focus();
  }, [session]);

  async function start() {
    if (!authenticated || topicId === null || mode !== "TRIVIAL" || starting.current || session) return;
    starting.current = true;
    setLoading(true);
    setError("");
    try {
      const result = await startTrivialGame(topicId);
      if (!mounted.current) return;
      const first = result.questions[0];
      if (!first || first.question_type !== "TRIVIAL" || !first.options || first.options.length < 2) {
        setError("No se ha recibido una pregunta válida. Vuelve al panel y elige otra temática.");
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
          ? "Esta temática no tiene preguntas de Trivial disponibles. Elige otra desde el panel."
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

  const firstQuestion = session?.questions[0];

  return (
    <div className="min-h-screen bg-background text-slate-900">
      <header className="site-header">
        <nav aria-label="Partida" className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-5 sm:px-8 lg:px-12">
          <Brand />
          <button onClick={logout} className="button-primary">Cerrar sesión</button>
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
            </> : firstQuestion ? <>
              <p className="text-sm font-semibold text-sky-800">Pregunta 1 de {session.questions.length}</p>
              <h2 ref={questionHeading} tabIndex={-1} className="mt-4 break-words text-xl font-bold leading-8 text-blue-950 outline-none" id="question-heading">{firstQuestion.text}</h2>
              <fieldset className="mt-6 space-y-3" aria-labelledby="question-heading">
                <legend className="sr-only">Selecciona una respuesta</legend>
                {firstQuestion.options?.map((option, index) => (
                  <label key={index} className={`flex cursor-pointer items-start gap-3 rounded-xl border p-4 transition-colors focus-within:ring-2 focus-within:ring-sky-700 ${selectedIndex === index ? "border-sky-700 bg-sky-50" : "border-slate-300 hover:bg-slate-50"}`}>
                    <input type="radio" name="answer" value={index} checked={selectedIndex === index} onChange={() => setSelectedIndex(index)} className="mt-1 h-4 w-4 shrink-0 accent-sky-800" />
                    <span className="break-words leading-6">{option}</span>
                  </label>
                ))}
              </fieldset>
              <p className="mt-6 text-sm leading-6 text-slate-600">Esta versión permite explorar la primera pregunta. Tu selección aún no se envía ni se puntúa.</p>
            </> : <>
              <h2 className="text-xl font-bold text-blue-950">Practica eligiendo una respuesta</h2>
              <p className="mt-3 leading-7 text-slate-600">Cargaremos las preguntas de la temática que has elegido. Por ahora podrás explorar la primera pregunta y sus opciones.</p>
              <p className="mt-3 text-sm leading-6 text-slate-600">Al comenzar se registra una partida. Si vuelves al panel, aparecerá como «Sin finalizar».</p>
              {error && <p role="alert" className="notice-error mt-5">{error}</p>}
              <button onClick={start} disabled={loading} className="button-primary mt-6 w-full sm:w-auto">{loading ? "Cargando partida…" : "Comenzar partida"}</button>
              {loading && <p role="status" className="mt-3 text-sm text-slate-600">Buscando tus preguntas…</p>}
            </>}
        </section>
      </main>
    </div>
  );
}
