"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import Brand from "@/components/Brand";
import TrivialGame from "@/components/TrivialGame";
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

  async function start() {
    if (!authenticated || topicId === null || mode !== "TRIVIAL" || starting.current || session) return;
    starting.current = true;
    setLoading(true);
    setError("");
    try {
      const result = await startTrivialGame(topicId);
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
            </> : session ? <TrivialGame session={session} /> : <>
              <h2 className="text-xl font-bold text-blue-950">Practica eligiendo una respuesta</h2>
              <p className="mt-3 leading-7 text-slate-600">Responde las preguntas de la temática que has elegido. Podrás revisar tus elecciones y, al finalizar, consultar la puntuación y las respuestas correctas.</p>
              <p className="mt-3 text-sm leading-6 text-slate-600">Si abandonas o recargas antes de terminar, perderás tus selecciones y la partida quedará «Sin finalizar».</p>
              {error && <p role="alert" className="notice-error mt-5">{error}</p>}
              <button onClick={start} disabled={loading} className="button-primary mt-6 w-full sm:w-auto">{loading ? "Cargando partida…" : "Comenzar partida"}</button>
              {loading && <p role="status" className="mt-3 text-sm text-slate-600">Buscando tus preguntas…</p>}
            </>}
        </section>
      </main>
    </div>
  );
}
