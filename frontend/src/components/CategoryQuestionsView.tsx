"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { isAxiosError } from "axios";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Brand from "@/components/Brand";
import ProfileMenu from "@/components/ProfileMenu";
import ContentBreadcrumbs from "@/components/ContentBreadcrumbs";
import MonitoringGameSelect from "@/components/MonitoringGameSelect";
import CreateQuestionForm from "@/components/CreateQuestionForm";
import { canManageSubjects, SUBJECTS_PAGE_SIZE } from "@/lib/subjects";
import { getCategoryDetail, getCategoryQuestions, getCurrentUser, setCategoryQuestionState,
  type CategoryDetail, type CategoryQuestion, type CategoryQuestionFilters,
  type GameMode, type QuestionStateFilter } from "@/services/api";

type ViewState = "loading" | "ready" | "error" | "forbidden" | "missing" | "invalid";

export default function CategoryQuestionsView({ subjectId, blockId, categoryId, page, mode, level, questionState = "all",
  invalidFilters, adjusted = false }: { subjectId: number; blockId: number; categoryId: number; page: number;
  mode: GameMode | ""; level: string; questionState?: QuestionStateFilter; invalidFilters: boolean; adjusted?: boolean }) {
  const router = useRouter();
  const [state, setState] = useState<ViewState>("loading");
  const [category, setCategory] = useState<CategoryDetail | null>(null);
  const [questions, setQuestions] = useState<CategoryQuestion[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [selectedMode, setSelectedMode] = useState(mode);
  const [selectedLevel, setSelectedLevel] = useState(level);
  const [selectedState, setSelectedState] = useState(questionState);
  const [pendingRetirement, setPendingRetirement] = useState<CategoryQuestion | null>(null);
  const [changingId, setChangingId] = useState<number | null>(null);
  const [actionError, setActionError] = useState("");
  const sendingState = useRef(false);
  const [editing, setEditing] = useState<CategoryQuestion | null>(null);
  const [notice, setNotice] = useState("");
  const adjustPage = useRef(false);
  const returnFocusId = useRef<number | null>(null);
  const base = `/gestion/asignaturas/${subjectId}/bloques/${blockId}/categorias/${categoryId}`;

  const urlFor = useCallback((nextPage: number, nextMode = mode, nextLevel = level, nextState = questionState) => {
    const query = new URLSearchParams();
    query.set("state", nextState);
    if (nextMode) query.set("mode", nextMode);
    if (nextLevel) query.set("level", nextLevel);
    if (nextPage > 1) query.set("page", String(nextPage));
    return `${base}${query.size ? `?${query}` : ""}`;
  }, [base, mode, level, questionState]);

  useEffect(() => {
    if (!window.localStorage.getItem("token")) { router.replace("/login"); return; }
    let active = true;
    async function load() {
      try {
        const user = await getCurrentUser();
        if (!active || !window.localStorage.getItem("token")) return;
        if (!canManageSubjects(user.role)) { setState("forbidden"); return; }
        if (![subjectId, blockId, categoryId].every((id) => Number.isSafeInteger(id) && id > 0)) {
          setState("missing"); return;
        }
        if (invalidFilters) { setState("invalid"); return; }
        const filters: CategoryQuestionFilters = { state: questionState };
        if (mode) filters.mode = mode;
        if (level === "unknown") filters.difficulty_unknown = true;
        else if (level) filters.difficulty = Number(level);
        const [detail, received] = await Promise.all([
          getCategoryDetail(subjectId, blockId, categoryId),
          getCategoryQuestions(subjectId, blockId, categoryId,
            (page - 1) * SUBJECTS_PAGE_SIZE, SUBJECTS_PAGE_SIZE + 1, filters),
        ]);
        if (!active || !window.localStorage.getItem("token")) return;
        if (received.length === 0 && page > 1 && adjustPage.current) {
          router.replace(`${urlFor(1)}&adjusted=1`);
          return;
        }
        setCategory(detail);
        setQuestions(received.slice(0, SUBJECTS_PAGE_SIZE));
        setHasMore(received.length > SUBJECTS_PAGE_SIZE);
        setState("ready");
        if (returnFocusId.current !== null) {
          const id = returnFocusId.current;
          returnFocusId.current = null;
          requestAnimationFrame(() => (document.getElementById(`edit-${id}`) ?? document.getElementById("question-list-heading"))?.focus());
        }
      } catch (error) {
        if (!active) return;
        const status = isAxiosError(error) ? error.response?.status : undefined;
        if (status === 401) return;
        if (status === 403 || status === 404) {
          setCategory(null); setQuestions([]);
          setState(status === 403 ? "forbidden" : "missing");
        } else if (status === 422) setState("invalid");
        else setState("error");
      }
    }
    void load();
    return () => { active = false; };
  }, [attempt, blockId, categoryId, invalidFilters, level, mode, page, questionState, router, subjectId, urlFor]);

  function retry() { setState("loading"); setAttempt((value) => value + 1); }
  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    router.push(urlFor(1, selectedMode, selectedLevel, selectedState));
  }
  function logout() {
    window.localStorage.removeItem("token");
    setCategory(null); setQuestions([]); setState("loading");
    router.replace("/login");
  }

  async function changeState(question: CategoryQuestion, isActive: boolean) {
    if (sendingState.current) return;
    sendingState.current = true;
    setChangingId(question.id); setActionError(""); setNotice("");
    try {
      const saved = await setCategoryQuestionState(subjectId, blockId, categoryId, question.id, isActive);
      const excluded = questionState !== "all" && (questionState === "active") !== saved.is_active;
      setNotice(`Pregunta ${question.id} ${saved.is_active ? "reactivada" : "retirada"}.${excluded ? " Deja de coincidir con el filtro actual; se ha ajustado el listado y la paginación." : " Listado actualizado."}`);
      setPendingRetirement(null);
      adjustPage.current = true;
      returnFocusId.current = question.id;
      setAttempt((value) => value + 1);
    } catch (error) {
      if (isAxiosError(error) && error.response?.status === 401) return;
      setActionError("No se pudo confirmar el estado. Puedes repetir la misma acción de forma segura o actualizar el listado para comprobarlo.");
    } finally { sendingState.current = false; setChangingId(null); }
  }
  function cancelRetirement() {
    const id = pendingRetirement?.id;
    setPendingRetirement(null); setActionError("");
    requestAnimationFrame(() => document.getElementById(`state-${id}`)?.focus());
  }

  function closeEditor(saved: boolean, uncertain = false) {
    const id = editing?.id;
    setEditing(null);
    setNotice(saved ? `Pregunta ${id} guardada. Se conservan los filtros y la página seleccionados.` : uncertain ? "Edición cerrada. El último envío no pudo confirmarse; comprueba el banco en el listado." : "Edición cancelada. No se guardaron cambios.");
    if (saved || uncertain) { returnFocusId.current = id ?? null; setAttempt((value) => value + 1); }
    else requestAnimationFrame(() => (document.getElementById(`edit-${id}`) ?? document.getElementById("question-list-heading"))?.focus());
  }

  return <div className="min-h-screen bg-background text-slate-900">
    <header className="site-header"><nav aria-label="Gestión de contenidos" className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-5 py-5 sm:px-8"><Brand /><div className="flex flex-wrap items-center gap-2"><ProfileMenu /><button className="button-primary" onClick={logout}>Cerrar sesión</button></div></nav></header>
    <main className="mx-auto max-w-5xl px-5 py-8 sm:px-8 sm:py-12" aria-busy={state === "loading"}>
      <ContentBreadcrumbs subject={category?.block.subject} block={category?.block} category={category} />
      <p className="mt-5 text-xs font-bold uppercase tracking-widest text-orange-700">Gestión de contenidos</p>
      <h1 className="mt-2 break-words text-3xl font-black text-blue-950">{category?.name ?? "Preguntas de la categoría"}</h1>
      {category?.description && <p className="mt-2 break-words text-slate-600">{category.description}</p>}
      {actionError && <p role="alert" className="notice-error mt-4">{actionError}<button type="button" disabled={changingId !== null} className="button-secondary ml-3" onClick={retry}>Actualizar listado</button></p>}
      {adjusted && !notice && <p role="status" className="notice-success mt-4">Estado actualizado. La pregunta deja de coincidir con el filtro actual; se muestra la primera página disponible con los mismos filtros.</p>}
      {notice && <p role="status" className="notice-success mt-4">{notice}</p>}
      {category && (state === "ready" || state === "error") && <CreateQuestionForm
        key={`${subjectId}-${blockId}-${categoryId}-${editing?.id ?? "new"}`} subjectId={subjectId} blockId={blockId}
        categoryId={categoryId} questionState={questionState} disabled={changingId !== null || pendingRetirement !== null} mode={mode} level={level} question={editing ?? undefined} onClose={closeEditor}
        onRefresh={() => setAttempt((value) => value + 1)} />}
      {state === "loading" && <p role="status" className="mt-6 rounded-2xl bg-white p-6">Cargando preguntas…</p>}
      {state === "forbidden" && <p role="alert" className="notice-warning mt-6">Acceso no permitido. La consulta de preguntas está disponible para profesores y administradores.</p>}
      {state === "missing" && <p role="alert" className="notice-warning mt-6">La asignatura, el bloque o la categoría no existe en esta ruta.</p>}
      {state === "invalid" && <div className="mt-6"><p role="alert" className="notice-warning">Los filtros de la URL no son válidos.</p><Link href={base} className="text-link mt-3 inline-flex min-h-11 items-center">Ver todas las preguntas</Link></div>}
      {state === "error" && <div className="mt-6"><p role="alert" className="notice-error">No se pudieron consultar las preguntas. Comprueba la conexión e inténtalo de nuevo.</p><button type="button" className="button-secondary mt-4" onClick={retry}>Reintentar</button></div>}
      {state === "ready" && !editing && <>
        <p className="mt-4 text-sm text-slate-600">La categoría organiza el contenido académico; la temática agrupa las preguntas para jugar.</p>
        <form onSubmit={applyFilters} className="mt-7 grid items-start gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_auto]" aria-label="Filtrar preguntas">
          <MonitoringGameSelect id="question-mode" name="mode" label="Modalidad" value={selectedMode || "ALL"}
            onValueChange={(value) => setSelectedMode(value === "ALL" ? "" : value as GameMode)}
            options={[{value: "ALL", label: "Ambas modalidades"}, {value: "TRIVIAL", label: "Trivial"}, {value: "PASAPALABRA", label: "Pasapalabra"}]} />
          <div className="min-w-0"><MonitoringGameSelect id="question-level" name="level" label="Dificultad" value={selectedLevel || "ALL"}
            onValueChange={(value) => setSelectedLevel(value === "ALL" ? "" : value)}
            options={[{value: "ALL", label: "Todas las dificultades"}, ...[1, 2, 3, 4].map((value) => ({value: String(value), label: `Nivel ${value}`})), {value: "unknown", label: "Solo sin clasificar"}]} />
            {selectedLevel === "" && <p className="mt-2 text-xs leading-5 text-slate-600">Incluye preguntas sin dificultad asignada.</p>}</div>
          <MonitoringGameSelect id="question-state" name="state" label="Estado" value={selectedState}
            onValueChange={(value) => setSelectedState(value as QuestionStateFilter)}
            options={[{value: "all", label: "Todas"}, {value: "active", label: "Activas"}, {value: "retired", label: "Retiradas"}]} />
          <button type="submit" disabled={changingId !== null} className="button-secondary lg:mt-7">Aplicar filtros</button>
        </form>
        <section aria-labelledby="question-list-heading" className="mt-8">
          <h2 id="question-list-heading" tabIndex={-1} className="text-xl font-bold text-blue-950">Preguntas</h2>
          {questions.length === 0 ? <p className="mt-4 rounded-2xl border border-slate-200 bg-white p-6 text-slate-600">{page > 1 ? "No hay preguntas en esta página." : mode || level || questionState !== "all" ? "No hay preguntas que coincidan con estos filtros." : "Todavía no hay preguntas en esta categoría."}</p>
            : <ol className="mt-4 space-y-4">{questions.map((question) => <li key={question.id} className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <p className="break-words text-sm font-semibold text-sky-800">{question.question_type === "TRIVIAL" ? "Trivial" : "Pasapalabra"} · {question.difficulty === null ? "Dificultad sin clasificar" : `Nivel ${question.difficulty}`} · ID {question.id} · {question.is_active ? "Activa" : "Retirada"}</p>
              <h3 className="mt-2 break-words text-lg font-bold text-blue-950">{question.text}</h3>
              <button id={`edit-${question.id}`} type="button" className="button-secondary mt-3" disabled={changingId !== null || pendingRetirement !== null} aria-label={`Editar pregunta ${question.id}`} onClick={() => { setNotice(""); setEditing(question); }}>Editar</button>
              <button id={`state-${question.id}`} type="button" className="button-secondary mt-3 ml-3" disabled={changingId !== null || pendingRetirement !== null}
                aria-label={`${question.is_active ? "Retirar" : "Reactivar"} pregunta ${question.id}`}
                onClick={() => { setActionError(""); if (question.is_active) { setPendingRetirement(question); requestAnimationFrame(() => document.getElementById("cancel-retirement")?.focus()); } else void changeState(question, true); }}>
                {changingId === question.id ? "Guardando…" : question.is_active ? "Retirar" : "Reactivar"}</button>
              {pendingRetirement?.id === question.id && <div role="group" aria-labelledby="retirement-warning" className="notice-warning mt-4" onKeyDown={(event) => { if (event.key === "Escape" && changingId === null) cancelRetirement(); }}>
                <p id="retirement-warning">Retirar la pregunta {question.id}: dejará de aparecer en partidas nuevas. Las partidas anteriores, sus correcciones y el historial se conservarán.</p>
                <div className="mt-3 flex flex-wrap gap-3"><button type="button" className="button-primary" disabled={changingId !== null} onClick={() => void changeState(question, false)}>Confirmar retirada</button>
                <button id="cancel-retirement" type="button" className="button-secondary" disabled={changingId !== null} onClick={cancelRetirement}>Cancelar</button></div>
              </div>}
              <p className="mt-2 break-words text-sm text-slate-600">Temática de juego: {question.topic.name} · ID {question.topic_id}</p>
              {question.question_type === "TRIVIAL" ? <div className="mt-4"><p className="font-semibold text-blue-950">Opciones</p>{question.options ? <ol className="mt-2 space-y-1 list-inside list-[upper-alpha]">{question.options.map((option, index) => <li key={index} className="break-words">{option}{index === question.correct_option_index && <strong className="ml-2 text-green-800">Correcta</strong>}</li>)}</ol> : <p className="text-sm text-slate-600">No constan opciones.</p>}{question.options && question.correct_option_index === null && <p className="mt-2 text-sm text-slate-600">No consta la opción correcta.</p>}</div>
                : <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2"><div><dt className="font-semibold">Letra</dt><dd>{question.letter ?? "No consta"}</dd></div><div><dt className="font-semibold">Solución</dt><dd className="break-words">{question.exact_word ?? "No consta"}</dd></div><div className="sm:col-span-2"><dt className="font-semibold">Respuestas alternativas</dt><dd className="break-words">{question.accepted_answers === null ? "No constan datos" : question.accepted_answers.length ? question.accepted_answers.join(", ") : "Ninguna registrada"}</dd></div></dl>}
            </li>)}</ol>}
          <nav aria-label="Páginas de preguntas" className="mt-6 flex flex-wrap items-center justify-between gap-4">
            {page > 1 ? <Link href={urlFor(page - 1)} className="button-secondary">Anterior</Link> : <span />}
            <span className="text-sm font-semibold text-slate-600">Página {page}</span>
            {hasMore && <Link href={urlFor(page + 1)} className="button-secondary">Siguiente</Link>}
          </nav>
        </section>
      </>}
    </main>
  </div>;
}
