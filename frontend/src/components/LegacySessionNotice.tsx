"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import type { GameMode } from "@/services/api";

export default function LegacySessionNotice({ topicId, mode }: { topicId: number; mode: GameMode }) {
  const message = useRef<HTMLDivElement>(null);
  useEffect(() => { message.current?.focus(); }, []);
  return <div ref={message} tabIndex={-1} role="alert" className="notice-warning mt-6">
    <p>Esta partida se inició con una versión anterior y ya no puede continuarse. Puedes empezar una nueva</p>
    <div className="mt-3 flex flex-wrap gap-3">
      {/* Full navigation also resets GameStart when this is already the active URL. */}
      <a href={`/game?topicId=${topicId}&mode=${mode}`} className="button-secondary">Preparar otra partida</a>
      <Link href="/historial" className="text-link inline-flex min-h-11 items-center">Ver historial</Link>
    </div>
  </div>;
}
