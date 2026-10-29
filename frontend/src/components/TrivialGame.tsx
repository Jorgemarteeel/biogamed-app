"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { isAxiosError } from "axios";
import { submitTrivialGame, type GameResult, type GameSessionStart } from "@/services/api";

export default function TrivialGame({ session }: { session: GameSessionStart }) {
  const [questionIndex, setQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<GameResult | null>(null);
  const sending = useRef(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const mounted = useRef(false);
  const question = session.questions[questionIndex];
  const selectedIndex = answers[question.id];
  const allAnswered = session.questions.every((item) => answers[item.id] !== undefined);
  const isLast = questionIndex === session.questions.length - 1;

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  useEffect(() => {
    heading.current?.focus();
  }, [questionIndex, result]);

  async function finish() {
    if (!allAnswered || sending.current || result) return;
    sending.current = true;
    setSubmitting(true);
    setError("");
    try {
      const response = await submitTrivialGame(session.session_id, session.questions.map((item) => ({
        question_id: item.id,
        selected_index: answers[item.id],
      })));
      if (mounted.current) setResult(response);
    } catch (err: unknown) {
      if (!mounted.current) return;
      const status = isAxiosError(err) ? err.response?.status : undefined;
      if (status === 401) return;
      setError(status === 403 || status === 404
        ? "No puedes acceder a esta partida. Vuelve al panel para comenzar otra."
        : status === 409
          ? "Una pregunta de esta partida ya no está disponible. Vuelve al panel para comenzar otra."
          : "No se pudo obtener el resultado. Tus respuestas siguen aquí; puedes volver a enviarlas.");
    } finally {
      sending.current = false;
      if (mounted.current) setSubmitting(false);
    }
  }

  const journey = (
    <nav aria-label={result ? "Resultados por pregunta" : "Recorrido de preguntas"} className="my-3">
      <ol className="flex flex-wrap gap-2">
        {session.questions.map((item, index) => {
          const current = !result && index === questionIndex;
          const answered = answers[item.id] !== undefined;
          const correction = result?.corrections.find((entry) => entry.question_id === item.id);
          const status = result
            ? correction ? correction.is_correct ? "Correcta" : "Incorrecta" : "Sin corrección"
            : answered ? "Respondida" : "Pendiente";
          const appearance = result
            ? correction ? correction.is_correct ? "border-emerald-300 bg-emerald-50 text-emerald-900" : "border-red-300 bg-red-50 text-red-900" : "border-slate-300 bg-white text-slate-700"
            : answered ? "border-sky-300 bg-sky-50 text-sky-900" : "border-dashed border-slate-400 bg-white text-slate-700";
          const className = `flex min-h-11 min-w-11 flex-col items-center justify-center rounded-lg border px-2 py-1 text-center transition-colors hover:border-sky-700 disabled:cursor-wait disabled:opacity-60 ${appearance} ${current ? "ring-2 ring-orange-700 ring-offset-2" : ""}`;
          const label = `Pregunta ${index + 1}${current ? ", actual" : ""}: ${status.toLowerCase()}`;
          const marker = result ? correction ? correction.is_correct ? "✓" : "×" : "?" : answered ? "●" : "○";
          const content = <>
            <span aria-hidden="true" className={`text-base font-bold leading-5 ${current ? "underline decoration-2 underline-offset-2" : ""}`}>{index + 1}</span>
            <span aria-hidden="true" className="text-xs font-bold leading-4">{marker}</span>
          </>;
          return (
            <li key={item.id}>
              {result
                ? <a href={`#correction-${item.id}`} aria-label={`${label}. Ver corrección`} className={className}>{content}</a>
                : <button type="button" onClick={() => setQuestionIndex(index)} disabled={submitting} aria-current={current ? "step" : undefined} aria-label={`${label}. Ir a la pregunta`} className={className}>{content}</button>}
            </li>
          );
        })}
      </ol>
      <p className="mt-2 flex flex-wrap gap-x-3 text-xs leading-5 text-slate-600">
        {result ? <>
          <span>✓ Correcta</span><span>× Incorrecta</span><span>? Sin corrección</span>
        </> : <>
          <span><span className="underline decoration-2 underline-offset-2">Subrayada</span>: actual</span>
          <span>○ Pendiente</span><span>● Respondida (sin corregir)</span>
        </>}
      </p>
    </nav>
  );

  if (result) {
    return (
      <div>
        <p className="text-xs font-bold uppercase tracking-widest text-sky-800">Partida completada</p>
        <h2 ref={heading} tabIndex={-1} className="mt-3 text-3xl font-black text-blue-950 outline-none">Tu resultado</h2>
        <p className="mt-5 text-4xl font-black text-blue-950">{result.score} <span className="text-xl font-semibold text-slate-600">de {result.total_questions} aciertos</span></p>
        <p className="mt-3 leading-7 text-slate-600">Tu resultado se ha guardado. Revisa tus respuestas para seguir aprendiendo.</p>
        {journey}
        <ol className="mt-8 space-y-5" aria-label="Corrección de respuestas">
          {session.questions.map((item, index) => {
            const correction = result.corrections.find((entry) => entry.question_id === item.id);
            return (
              <li key={item.id} className="rounded-xl border border-slate-200 p-5">
                <p className={`text-sm font-bold ${correction?.is_correct ? "text-emerald-800" : "text-red-800"}`}>
                  {index + 1}. {correction ? correction.is_correct ? "Correcta" : "Incorrecta" : "Corrección no disponible"}
                </p>
                <h3 id={`correction-${item.id}`} tabIndex={-1} className="mt-2 scroll-mt-6 break-words font-bold leading-7 text-blue-950 focus:outline-2 focus:outline-offset-4 focus:outline-sky-700">{item.text}</h3>
                {correction && <dl className="mt-4 space-y-3 text-sm leading-6">
                  <div><dt className="font-semibold text-slate-600">Tu respuesta</dt><dd className="break-words text-slate-900">{correction.selected_index !== null ? item.options?.[correction.selected_index] ?? "No disponible" : "Sin respuesta"}</dd></div>
                  <div><dt className="font-semibold text-emerald-800">Respuesta correcta</dt><dd className="break-words text-slate-900">{correction.correct_option_index !== null ? item.options?.[correction.correct_option_index] ?? "No disponible" : "No disponible"}</dd></div>
                </dl>}
              </li>
            );
          })}
        </ol>
        <Link href="/dashboard" className="button-primary mt-8 w-full sm:w-auto">Volver al panel</Link>
      </div>
    );
  }

  return (
    <div aria-busy={submitting}>
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm font-semibold text-sky-800">
        <p>Pregunta {questionIndex + 1} de {session.questions.length}</p>
        <p>{Object.keys(answers).length} respondidas</p>
      </div>
      {journey}
      <h2 ref={heading} tabIndex={-1} className="mt-5 break-words text-xl font-bold leading-8 text-blue-950 outline-none" id="question-heading">{question.text}</h2>
      <fieldset disabled={submitting} className="mt-6 space-y-3 disabled:opacity-70" aria-labelledby="question-heading">
        <legend className="sr-only">Selecciona una respuesta</legend>
        {question.options?.map((option, index) => (
          <label key={`${question.id}-${index}`} className={`flex cursor-pointer items-start gap-3 rounded-xl border p-4 transition-colors focus-within:ring-2 focus-within:ring-sky-700 ${selectedIndex === index ? "border-sky-700 bg-sky-50" : "border-slate-300 hover:bg-slate-50"}`}>
            <input type="radio" name={`answer-${question.id}`} value={index} checked={selectedIndex === index} onChange={() => setAnswers((previous) => ({ ...previous, [question.id]: index }))} className="mt-1 h-4 w-4 shrink-0 accent-sky-800" />
            <span className="min-w-0 break-words leading-6">{option}</span>
          </label>
        ))}
      </fieldset>
      <p className="mt-5 text-sm leading-6 text-slate-600">Puedes revisar y cambiar tus respuestas antes de finalizar.</p>
      {error && <p role="alert" className="notice-error mt-5">{error}</p>}
      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-between">
        <button onClick={() => setQuestionIndex((index) => Math.max(0, index - 1))} disabled={questionIndex === 0 || submitting} className="button-secondary">Anterior</button>
        {isLast
          ? <button onClick={finish} disabled={!allAnswered || submitting} className="button-primary">{submitting ? "Enviando respuestas…" : "Finalizar y ver resultado"}</button>
          : <button onClick={() => setQuestionIndex((index) => answers[session.questions[index].id] === undefined ? index : Math.min(index + 1, session.questions.length - 1))} disabled={selectedIndex === undefined || submitting} className="button-primary">Siguiente pregunta</button>}
      </div>
      {submitting && <p role="status" className="mt-4 text-sm text-slate-600">Estamos corrigiendo tus respuestas…</p>}
    </div>
  );
}
