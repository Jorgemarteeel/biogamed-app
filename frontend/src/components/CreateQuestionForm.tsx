"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { isAxiosError } from "axios";
import CreateContentPanel from "@/components/CreateContentPanel";
import { createCategoryQuestion, editCategoryQuestion, getQuestionTopics, type CategoryQuestion, type GameMode, type QuestionStateFilter, type Topic } from "@/services/api";

export default function QuestionForm({ subjectId, blockId, categoryId, mode, level, onRefresh, question, onClose, questionState = "all", disabled = false }: {
  subjectId: number; blockId: number; categoryId: number; mode: GameMode | ""; level: string;
  questionState?: QuestionStateFilter; disabled?: boolean;
  onRefresh: () => void; question?: CategoryQuestion; onClose?: (saved: boolean, uncertain?: boolean) => void;
}) {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [topicState, setTopicState] = useState("loading");
  const [attempt, setAttempt] = useState(0);
  const [topic, setTopic] = useState(question ? String(question.topic_id) : "");
  const [kind, setKind] = useState<GameMode>(question?.question_type ?? "TRIVIAL");
  const [difficulty, setDifficulty] = useState(question?.difficulty ? String(question.difficulty) : "");
  const [text, setText] = useState(question?.text ?? "");
  const [options, setOptions] = useState(question?.options ?? ["", "", "", ""]);
  const [correct, setCorrect] = useState(question?.correct_option_index != null ? String(question.correct_option_index) : "");
  const [letter, setLetter] = useState(question?.letter ?? "");
  const [word, setWord] = useState(question?.exact_word ?? "");
  const [alternatives, setAlternatives] = useState(question?.accepted_answers?.join("\n") ?? "");
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<CategoryQuestion | null>(null);
  const [cancelPending, setCancelPending] = useState(false);
  const [saveUncertain, setSaveUncertain] = useState(false);
  const confirmation = useRef<HTMLDivElement>(null);
  useEffect(() => { if (created) confirmation.current?.focus(); }, [created]);
  useEffect(() => { if (question) document.getElementById("create-text")?.focus(); }, [question]);
  useEffect(() => {
    let active = true;
    getQuestionTopics().then((data) => { if (active) { setTopics(data); setTopicState("ready"); } })
      .catch(() => { if (active) setTopicState("error"); });
    return () => { active = false; };
  }, [attempt]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (disabled || submitting.current || created || cancelPending) return;
    setError("");
    if (!text.trim() || (kind === "TRIVIAL" && options.some((value) => !value.trim()))) {
      setError("El enunciado y las opciones no pueden estar vacíos."); return;
    }
    submitting.current = true; setBusy(true);
    const common = { text, topic_id: Number(topic), difficulty: difficulty ? Number(difficulty) : null };
    try {
      const save = question
        ? (payload: Parameters<typeof createCategoryQuestion>[3]) => editCategoryQuestion(subjectId, blockId, categoryId, question.id, payload)
        : (payload: Parameters<typeof createCategoryQuestion>[3]) => createCategoryQuestion(subjectId, blockId, categoryId, payload);
      const result = await save(
        kind === "TRIVIAL" ? { ...common, question_type: kind, options, correct_option_index: Number(correct) }
          : { ...common, question_type: kind, letter, exact_word: word,
            accepted_answers: alternatives.trim() ? alternatives.split("\n") : [] });
      setCreated(result);
      setSaveUncertain(false);
    } catch (failure) {
      const status = isAxiosError(failure) ? failure.response?.status : undefined;
      if (question && (status === undefined || status >= 500)) setSaveUncertain(true);
      const detail = isAxiosError(failure) ? failure.response?.data?.detail : undefined;
      const message = typeof detail === "string" ? detail : Array.isArray(detail)
        ? detail.map((item: { msg: string }) => item.msg).join(" ") : "";
      setError(status === 403 ? "Ya no tienes permiso para guardar preguntas."
        : status === 404 ? "La temática o la categoría ya no está disponible. Revisa la selección."
          : status === 422 ? `Revisa los campos. ${message}`
            : question ? "No se pudo confirmar el guardado. Los campos se conservan para reintentar."
              : "No se pudo confirmar la creación. Los campos se conservan. Si hubo un fallo de red, actualiza el listado antes de reintentar para evitar duplicados.");
    } finally { submitting.current = false; setBusy(false); }
  }
  const excluded = created && ((mode && mode !== created.question_type)
    || (questionState !== "all" && (questionState === "active") !== created.is_active)
    || (level === "unknown" ? created.difficulty !== null : level && Number(level) !== created.difficulty));
  const content = <>
    <p className="mb-4 text-sm text-slate-600">La pregunta se guardará en esta categoría. Elige por separado su temática de juego. No se deduce de la categoría.</p>
    {topicState === "loading" && <p role="status">Cargando temáticas…</p>}
    {topicState === "error" && <div><p role="alert">No se pudieron cargar las temáticas.</p><button type="button" className="button-secondary" onClick={() => { setTopicState("loading"); setAttempt((n) => n + 1); }}>Reintentar temáticas</button></div>}
    {topicState === "ready" && topics.length === 0 && <p role="status">No hay temáticas de juego disponibles.</p>}
    <form onSubmit={submit} className="space-y-4" aria-label={question ? "Editar pregunta" : "Crear pregunta"}>
      <fieldset disabled={disabled || busy || !!created || cancelPending} className="min-w-0 space-y-4">
        <div><label className="form-label" htmlFor="create-topic">Temática de juego (Topic)</label><select id="create-topic" className="form-input" required value={topic} onChange={(e) => setTopic(e.target.value)}><option value="">Selecciona una temática</option>{topics.map((t) => <option key={t.id} value={t.id}>{t.name} · ID {t.id}</option>)}</select></div>
        <div className="grid gap-4 sm:grid-cols-2"><div><label className="form-label" htmlFor="create-mode">Modalidad{question ? " (se conserva)" : " de la nueva pregunta"}</label><select id="create-mode" className="form-input" disabled={!!question} value={kind} onChange={(e) => setKind(e.target.value as GameMode)}><option value="TRIVIAL">Trivial</option><option value="PASAPALABRA">Pasapalabra</option></select></div>
          <div><label className="form-label" htmlFor="create-difficulty">Dificultad opcional</label><select id="create-difficulty" className="form-input" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}><option value="">Sin clasificar</option>{[1, 2, 3, 4].map((n) => <option key={n} value={n}>Nivel {n}</option>)}</select></div></div>
        <div><label className="form-label" htmlFor="create-text">Enunciado</label><textarea id="create-text" className="form-input" required value={text} onChange={(e) => setText(e.target.value)} /></div>
        {kind === "TRIVIAL" ? <>
          {options.map((option, index) => <div key={index}><label className="form-label" htmlFor={`create-option-${index}`}>Opción {index + 1}</label><input id={`create-option-${index}`} className="form-input" required maxLength={255} value={option} onChange={(e) => setOptions(options.map((v, i) => i === index ? e.target.value : v))} /></div>)}
          <div><label className="form-label" htmlFor="create-correct">Opción correcta</label><select id="create-correct" className="form-input" required value={correct} onChange={(e) => setCorrect(e.target.value)}><option value="">Selecciona la solución</option>{options.map((_, i) => <option key={i} value={i}>Opción {i + 1}</option>)}</select></div>
        </> : <>
          <p id="letter-help" className="text-sm text-slate-600">La solución debe empezar por la letra. Para una pista de tipo «contiene», inicia el enunciado con «Contiene la letra »; la solución deberá contenerla. Las alternativas son equivalencias aprobadas y pueden empezar por otra letra.</p>
          <div><label className="form-label" htmlFor="create-letter">Letra</label><input id="create-letter" className="form-input" aria-describedby="letter-help" required maxLength={1} value={letter} onChange={(e) => setLetter(e.target.value)} /></div>
          <div><label className="form-label" htmlFor="create-word">Solución</label><input id="create-word" className="form-input" required maxLength={255} value={word} onChange={(e) => setWord(e.target.value)} /></div>
          <div><label className="form-label" htmlFor="create-alternatives">Respuestas alternativas (opcional, una por línea; máximo 30, de 255 caracteres)</label><textarea id="create-alternatives" className="form-input" value={alternatives} onChange={(e) => setAlternatives(e.target.value)} /></div>
        </>}
        <button className="button-primary" type="submit" disabled={topicState !== "ready" || !topics.length}>{busy ? "Guardando…" : question ? "Guardar cambios" : "Guardar pregunta"}</button>
      </fieldset>
      {error && <p role="alert" className="notice-error">{error}</p>}
      {error && <button type="button" className="button-secondary" onClick={onRefresh}>Actualizar listado</button>}
      {created && <div ref={confirmation} tabIndex={-1} role="status" className="rounded-xl bg-green-50 p-4"><p>Pregunta {question ? "guardada" : "creada"} · ID {created.id} · {created.question_type === "TRIVIAL" ? "Trivial" : "Pasapalabra"} · {created.topic.name}</p><p>{excluded ? "Los filtros actuales excluyen esta pregunta. Se conservan; puedes cambiarlos en el listado." : "Actualiza el listado para consultarla. Puede estar en una página posterior porque se ordena por ID."}</p>
        {question ? <button type="button" className="button-secondary mt-3" onClick={() => onClose?.(true)}>Volver al listado</button>
          : <div className="mt-3 flex flex-wrap gap-3"><button type="button" className="button-secondary" onClick={onRefresh}>Actualizar listado</button><button type="button" className="button-secondary" onClick={() => { setCreated(null); setText(""); setOptions(["", "", "", ""]); setCorrect(""); setWord(""); setLetter(""); setAlternatives(""); }}>Crear otra pregunta</button></div>}</div>}
      {question && !created && <button type="button" disabled={busy || cancelPending} className="button-secondary" onClick={() => setCancelPending(true)}>Cancelar</button>}
      {cancelPending && <div role="alert" className="notice-warning"><p>{saveUncertain ? "¿Cerrar el borrador? El último envío no pudo confirmarse y podría haberse guardado. Se actualizará el listado para comprobar el banco." : "¿Descartar los cambios y volver al listado? No se guardarán."}</p><div className="mt-3 flex flex-wrap gap-3"><button autoFocus type="button" className="button-secondary" onClick={() => onClose?.(false, saveUncertain)}>Descartar cambios</button><button type="button" className="button-secondary" onClick={() => { setCancelPending(false); requestAnimationFrame(() => document.getElementById("create-text")?.focus()); }}>Seguir editando</button></div></div>}
    </form>
  </>;
  return question ? <section aria-label={`Editar pregunta ${question.id}`} className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 sm:p-7"><h2 className="mb-4 text-xl font-bold text-blue-950">Editar pregunta · ID {question.id}</h2>{content}</section>
    : <CreateContentPanel id="create-question" label="Crear pregunta" busy={busy}>{content}</CreateContentPanel>;
}
