"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import { Frame } from "@/components/Pasapalabra";
import LegacySessionNotice from "@/components/LegacySessionNotice";
import TrivialGame from "@/components/TrivialGame";
import { clearTrivialDraft, readTrivialDraft, type TrivialDraft } from "@/lib/trivial-draft";
import { isLegacySessionError, resumeTrivialGame, type GameSessionStart } from "@/services/api";

export default function TrivialSession({ id }: { id: number }) {
  const router = useRouter();
  const [game, setGame] = useState<{ session: GameSessionStart; draft: TrivialDraft }>();
  const [error, setError] = useState("");
  const [canRetry, setCanRetry] = useState(false);
  const [legacy, setLegacy] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!window.localStorage.getItem("token")) {
      try { window.sessionStorage.setItem("pasapalabra-return", `/trivial/${id}`); }
      catch { /* sign-in remains available when tab storage is disabled */ }
      router.replace("/login");
      return;
    }
    let active = true;
    resumeTrivialGame(id).then((session) => {
      if (active) setGame({ session, draft: readTrivialDraft(session) });
    }).catch((reason: unknown) => {
      if (!active) return;
      const response = isAxiosError(reason) ? reason.response : undefined;
      if (response?.status === 401) return;
      if (response?.status === 409 && response.data?.detail?.code === "TRIVIAL_ALREADY_COMPLETED") {
        clearTrivialDraft(id);
        router.replace(`/partidas/${id}`);
      } else if (isLegacySessionError(reason)) {
        setLegacy(true);
      } else if (response?.status === 404 || response?.status === 403) {
        setError("Esta partida no está disponible para tu cuenta.");
      } else if (response?.status === 409) {
        setError("No se puede recuperar la copia original de las preguntas de esta partida.");
      } else {
        setError("No se pudo recuperar la partida. Comprueba la conexión e inténtalo de nuevo.");
        setCanRetry(true);
      }
    });
    return () => { active = false; };
  }, [id, router, attempt]);

  return <Frame title="Trivial individual">{game
    ? <TrivialGame session={game.session} initialDraft={game.draft} topicName={game.session.topic_id === null ? "Práctica académica" : `Temática ${game.session.topic_id}`} />
    : legacy ? <LegacySessionNotice topicId={null} mode="TRIVIAL" />
    : error ? <><p className="notice-error" role="alert">{error}</p>{canRetry && <button className="button-secondary mt-4" onClick={() => { setError(""); setAttempt((value) => value + 1); }}>Reintentar</button>}</>
    : <p role="status">Recuperando partida…</p>}
  </Frame>;
}
