"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import { getTopics, type GameMode, type Topic } from "@/services/api";
import { topicIllustration } from "@/lib/topic-presentation";

const modes = [
  { id: "TRIVIAL" as const, name: "Trivial", description: "Responde preguntas y descubre cuánto sabes." },
  { id: "PASAPALABRA" as const, name: "Pasapalabra", description: "Dos jugadores y dos roscos numerados de vocabulario científico." },
];

function GameIllustration({ mode }: { mode: GameMode }) {
  return <svg viewBox="0 0 320 190" role="img" aria-label={mode === "TRIVIAL" ? "Rueda de cuatro categorías con tarjetas de preguntas" : "Rosco numerado"} className="h-40 w-full sm:h-44">
    <rect width="320" height="190" rx="22" fill={mode === "TRIVIAL" ? "#e0f2fe" : "#ccfbf1"} />
    <circle cx="160" cy="94" r="68" fill="white" opacity=".75" />
    {mode === "TRIVIAL" ? <>
      <path d="M160 94V35a59 59 0 0 1 59 59Z" fill="#0369a1" /><path d="M160 94h59a59 59 0 0 1-59 59Z" fill="#f97316" /><path d="M160 94v59a59 59 0 0 1-59-59Z" fill="#0d9488" /><path d="M160 94h-59a59 59 0 0 1 59-59Z" fill="#1e3a8a" />
      <circle cx="160" cy="94" r="23" fill="white" /><text x="160" y="104" textAnchor="middle" fontSize="30" fontWeight="800" fill="#1e3a8a">?</text>
      <g transform="rotate(-12 55 105)"><rect x="25" y="77" width="65" height="54" rx="9" fill="white" stroke="#94a3b8" strokeWidth="2" /><path d="M37 92h37M37 102h28M37 112h33" stroke="#0369a1" strokeWidth="3" strokeLinecap="round" /></g>
      <g transform="rotate(12 265 105)"><rect x="230" y="77" width="65" height="54" rx="9" fill="white" stroke="#94a3b8" strokeWidth="2" /><path d="M242 92h37M242 102h28M242 112h33" stroke="#f97316" strokeWidth="3" strokeLinecap="round" /></g>
    </> : <>
      {Array.from({ length: 20 }, (_, index) => {
        const angle = (index * Math.PI * 2) / 20 - Math.PI / 2;
        const x = 160 + Math.cos(angle) * 61;
        const y = 94 + Math.sin(angle) * 61;
        return <g key={index}><circle cx={x} cy={y} r="10" fill={index % 4 === 0 ? "#0d9488" : "#1e3a8a"} /><text x={x} y={y + 5} textAnchor="middle" fontSize="10" fontWeight="700" fill="white">{index + 1}</text></g>;
      })}
      <circle cx="160" cy="94" r="37" fill="white" /><path d="M143 91h34M149 102h22" stroke="#0d9488" strokeWidth="5" strokeLinecap="round" />
    </>}
  </svg>;
}

function TopicPicker({ mode, onBack }: { mode: GameMode; onBack: () => void }) {
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
          <Link key={topic.id} prefetch={false} href={`/game?topicId=${topic.id}&mode=${mode}`} aria-label={`Elegir temática ${topic.name} para ${name}`} className="group flex w-full min-w-0 max-w-[280px] flex-col rounded-2xl border border-sky-200 bg-white p-4 text-left shadow-sm transition motion-reduce:transition-none motion-reduce:transform-none hover:-translate-y-1 hover:border-sky-600 hover:shadow-lg focus-visible:border-sky-700 sm:w-[calc((100%-1rem)/2)] lg:w-[calc((100%-2rem)/3)]">
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
  const [mode, setMode] = useState<GameMode | null>(null);
  const lastMode = useRef<GameMode | null>(null);
  if (mode) return <TopicPicker key={mode} mode={mode} onBack={() => setMode(null)} />;

  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-widest text-sky-800">Paso 1 · El juego</p>
      <h2 className="mt-2 text-2xl font-bold text-blue-950">¿A qué quieres jugar hoy?</h2>
      <p className="mb-6 mt-2 text-sm leading-6 text-slate-600">Elige un juego y una temática.</p>
      <div className="grid gap-5 sm:grid-cols-2">
        {modes.map((item) => (
          <button key={item.id} ref={(node) => { if (node && lastMode.current === item.id) { node.focus(); lastMode.current = null; } }} onClick={() => { lastMode.current = item.id; setMode(item.id); }} className="group flex min-w-0 flex-col rounded-2xl border border-sky-200 bg-white p-5 text-left shadow-sm transition motion-reduce:transition-none motion-reduce:transform-none hover:-translate-y-1 hover:border-sky-600 hover:shadow-lg focus-visible:border-sky-700 sm:p-6">
            <GameIllustration mode={item.id} /><span className="mt-5 text-2xl font-black text-blue-950">{item.name}</span><span className="mt-2 text-sm leading-6 text-slate-600">{item.description}</span><span className="mt-5 font-bold text-sky-800 group-hover:underline">Elegir juego <span aria-hidden="true">→</span></span>
          </button>
        ))}
      </div>
    </div>
  );
}
