"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { getTopics, type GameMode, type Topic } from "@/services/api";

const modes = [
  { id: "TRIVIAL" as const, name: "Trivial", label: "Elige la respuesta", description: "Pon a prueba tus conocimientos escogiendo la opción correcta entre varias respuestas.", icon: "✓" },
  { id: "PASAPALABRA" as const, name: "Pasapalabra", label: "Encuentra la palabra", description: "Practica vocabulario científico respondiendo a definiciones con la ayuda de una letra.", icon: "Aa" },
];

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
      <button onClick={onBack} className="mb-5 min-h-11 rounded-lg px-3 py-2 text-sm font-bold text-sky-800 hover:bg-sky-100">← Cambiar de juego</button>
      <p className="text-xs font-bold uppercase tracking-widest text-sky-800">Paso 2 · {name}</p>
      <h2 ref={heading} tabIndex={-1} className="mt-2 text-2xl font-bold text-blue-950 outline-none">Elige qué quieres practicar</h2>
      <p className="mb-6 mt-2 text-sm leading-6 text-slate-600">Estas temáticas tienen preguntas disponibles para {name}.</p>
      {loading ? <p role="status" className="rounded-2xl border border-slate-200 bg-white p-6">Cargando temáticas…</p>
        : error ? <div className="rounded-2xl border border-red-200 bg-white p-6"><p role="alert" className="notice-error">{error}</p><button onClick={() => { setError(""); setLoading(true); setAttempt((value) => value + 1); }} className="button-secondary mt-4">Reintentar</button></div>
        : topics.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8"><h3 className="font-bold text-blue-950">Todavía no hay temáticas para {name}</h3><p className="mt-2 text-slate-600">Puedes volver y elegir el otro juego.</p></div>
        : <div className="grid gap-5 sm:grid-cols-2">{topics.map((topic) => (
          <article key={topic.id} className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="break-words text-xl font-bold text-blue-950">{topic.name}</h3>
            <p className="mt-3 flex-1 break-words text-sm leading-6 text-slate-600">{topic.description || "Practica los conceptos de esta temática a tu ritmo."}</p>
            <Link prefetch={false} href={`/game?topicId=${topic.id}&mode=${mode}`} aria-label={`Jugar ${name}: ${topic.name}`} className="button-primary mt-6">Jugar {name}</Link>
          </article>
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
      <p className="mb-6 mt-2 text-sm leading-6 text-slate-600">Primero elige cómo practicar. Después podrás seleccionar una temática.</p>
      <div className="grid gap-5 sm:grid-cols-2">
        {modes.map((item) => (
          <article key={item.id} className={`flex min-w-0 flex-col rounded-2xl border p-6 sm:p-7 ${item.id === "TRIVIAL" ? "border-sky-200 bg-sky-50/40" : "border-teal-200 bg-teal-50/40"}`}>
            <span aria-hidden="true" className={`mb-6 flex h-12 w-12 items-center justify-center rounded-xl text-2xl font-black ${item.id === "TRIVIAL" ? "bg-sky-100 text-sky-800" : "bg-teal-100 text-teal-800"}`}>{item.icon}</span>
            <p className={`text-xs font-bold uppercase tracking-wider ${item.id === "TRIVIAL" ? "text-sky-800" : "text-teal-800"}`}>{item.label}</p>
            <h3 className="mt-2 text-2xl font-black text-blue-950">{item.name}</h3>
            <p className="mt-3 flex-1 text-sm leading-7 text-slate-600">{item.description}</p>
            <button ref={(node) => { if (node && lastMode.current === item.id) { node.focus(); lastMode.current = null; } }} onClick={() => { lastMode.current = item.id; setMode(item.id); }} className="button-primary mt-7">Elegir {item.name}</button>
          </article>
        ))}
      </div>
    </div>
  );
}
