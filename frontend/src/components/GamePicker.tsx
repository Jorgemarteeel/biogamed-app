"use client";
import { useRouter } from "next/navigation";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import { getTopics, type GameMode, type Topic } from "@/services/api";
import { topicIllustration } from "@/lib/topic-presentation";
import GameChoiceCards, { GAME_CHOICES as modes } from "@/components/GameChoiceCards";


export function TopicPicker({ mode, onBack, online = false }: { mode: GameMode; onBack: () => void; online?: boolean }) {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const name = modes.find((item) => item.id === mode)!.name;

  useEffect(() => {
    heading.current?.focus();
    let active = true;
    getTopics(mode).then((result) => {
      if (active) { setTopics(result); setLoading(false); }
    }).catch(() => {
      if (active) {
        setError("No se pudieron cargar las temáticas. Inténtalo de nuevo.");
        setLoading(false);
      }
    });
    return () => { active = false; };
  }, [mode, attempt]);

  return (
    <div>
      <button onClick={onBack} className="mb-2 min-h-11 rounded-lg px-3 py-2 text-sm font-bold text-sky-800 hover:bg-sky-100">← Cambiar de juego</button>
      <p className="text-xs font-bold uppercase tracking-widest text-sky-800">Paso 2 · {name}</p>
      <h2 ref={heading} tabIndex={-1} className="mb-5 mt-2 text-2xl font-bold text-blue-950 outline-none">Elige qué quieres practicar</h2>
      {loading ? <p role="status" className="rounded-2xl border border-slate-200 bg-white p-6">Cargando temáticas…</p>
        : error ? <div className="rounded-2xl border border-red-200 bg-white p-6"><p role="alert" className="notice-error">{error}</p><button onClick={() => { setError(""); setLoading(true); setAttempt((value) => value + 1); }} className="button-secondary mt-4">Reintentar</button></div>
        : topics.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8"><h3 className="font-bold text-blue-950">Todavía no hay temáticas para {name}</h3><p className="mt-2 text-slate-600">Puedes volver y elegir el otro juego.</p></div>
        : <div className="mx-auto flex max-w-[920px] flex-wrap justify-center gap-4">{topics.map((topic) => (
          <Link key={topic.id} prefetch={false} href={`/game?topicId=${topic.id}&mode=${mode}${online ? "&play=ONLINE" : ""}`} aria-label={`Elegir temática ${topic.name} para ${name}`} className="group flex w-full min-w-0 max-w-[280px] flex-col rounded-2xl border border-sky-200 bg-white p-4 text-left shadow-sm transition motion-reduce:transition-none motion-reduce:transform-none hover:-translate-y-1 hover:border-sky-600 hover:shadow-lg focus-visible:border-sky-700 sm:w-[calc((100%-1rem)/2)] lg:w-[calc((100%-2rem)/3)]">
            <span className="flex h-36 items-center justify-center rounded-xl bg-sky-50 p-4"><Image src={topicIllustration(topic.name)} alt="" width={160} height={160} className="h-full w-full object-contain" /></span>
            <span className="mt-4 break-words text-lg font-bold text-blue-950">{topic.name}</span>
            {topic.description && topic.description.trim().toLowerCase() !== "string" && <span className="mt-2 break-words text-sm leading-5 text-slate-600">{topic.description}</span>}
            <span className="mt-auto pt-4 text-sm font-bold text-sky-800 group-hover:underline">Elegir temática <span aria-hidden="true">→</span></span>
          </Link>
        ))}</div>}
    </div>
  );
}

export default function GamePicker() {
  const router = useRouter();
  const [mode, setMode] = useState<GameMode | null>(null);
  const lastMode = useRef<GameMode | null>(null);
  if (mode) return <TopicPicker key={mode} mode={mode} onBack={() => setMode(null)} />;

  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-widest text-sky-800">Paso 1 · El juego</p>
      <h2 className="mt-2 text-2xl font-bold text-blue-950">¿A qué quieres jugar hoy?</h2>
      <p className="mb-6 mt-2 text-sm leading-6 text-slate-600">Elige un juego y una temática.</p>
      <GameChoiceCards onSelect={mode => { if (mode === "PASAPALABRA") { router.push("/pasapalabra"); return; } lastMode.current = mode; setMode(mode); }} buttonRef={(mode, node) => { if (node && lastMode.current === mode) { node.focus(); lastMode.current = null; } }} />
    </div>
  );
}
