"use client";

import { useEffect, useState, type FormEvent } from "react";
import { isAxiosError } from "axios";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Brand from "@/components/Brand";
import ProfileMenu from "@/components/ProfileMenu";
import ContentBreadcrumbs from "@/components/ContentBreadcrumbs";
import CreateQuestionForm from "@/components/CreateQuestionForm";
import { canManageSubjects, SUBJECTS_PAGE_SIZE } from "@/lib/subjects";
import { getCategoryDetail, getCategoryQuestions, getCurrentUser,
  type CategoryDetail, type CategoryQuestion, type CategoryQuestionFilters,
  type GameMode } from "@/services/api";

type ViewState = "loading" | "ready" | "error" | "forbidden" | "missing" | "invalid";

export default function CategoryQuestionsView({ subjectId, blockId, categoryId, page, mode, level,
  invalidFilters }: { subjectId: number; blockId: number; categoryId: number; page: number;
  mode: GameMode | ""; level: string; invalidFilters: boolean }) {
  const router = useRouter();
  const [state, setState] = useState<ViewState>("loading");
  const [category, setCategory] = useState<CategoryDetail | null>(null);
  const [questions, setQuestions] = useState<CategoryQuestion[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [selectedMode, setSelectedMode] = useState(mode);
  const [selectedLevel, setSelectedLevel] = useState(level);
  const base = `/gestion/asignaturas/${subjectId}/bloques/${blockId}/categorias/${categoryId}`;

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
        const filters: CategoryQuestionFilters = {};
        if (mode) filters.mode = mode;
        if (level === "unknown") filters.difficulty_unknown = true;
        else if (level) filters.difficulty = Number(level);
        const [detail, received] = await Promise.all([
          getCategoryDetail(subjectId, blockId, categoryId),
          getCategoryQuestions(subjectId, blockId, categoryId,
            (page - 1) * SUBJECTS_PAGE_SIZE, SUBJECTS_PAGE_SIZE + 1, filters),
        ]);
        if (!active || !window.localStorage.getItem("token")) return;
        setCategory(detail);
        setQuestions(received.slice(0, SUBJECTS_PAGE_SIZE));
        setHasMore(received.length > SUBJECTS_PAGE_SIZE);
        setState("ready");
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
  }, [attempt, blockId, categoryId, invalidFilters, level, mode, page, router, subjectId]);

  function retry() { setState("loading"); setAttempt((value) => value + 1); }
  function urlFor(nextPage: number, nextMode = mode, nextLevel = level) {
    const query = new URLSearchParams();
    if (nextMode) query.set("mode", nextMode);
    if (nextLevel) query.set("level", nextLevel);
    if (nextPage > 1) query.set("page", String(nextPage));
    return `${base}${query.size ? `?${query}` : ""}`;
  }
  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    router.push(urlFor(1, selectedMode, selectedLevel));
  }
  function logout() {
    window.localStorage.removeItem("token");
    setCategory(null); setQuestions([]); setState("loading");
    router.replace("/login");
  }

  return <div className="min-h-screen bg-background text-slate-900">
    <header className="site-header"><nav aria-label="Gestión de contenidos" className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-5 py-5 sm:px-8"><Brand /><div className="flex flex-wrap items-center gap-2"><ProfileMenu /><button className="button-primary" onClick={logout}>Cerrar sesión</button></div></nav></header>
    <main className="mx-auto max-w-5xl px-5 py-8 sm:px-8 sm:py-12" aria-busy={state === "loading"}>
      <ContentBreadcrumbs subject={category?.block.subject} block={category?.block} category={category} />
      <p className="mt-5 text-xs font-bold uppercase tracking-widest text-orange-700">Gestión de contenidos</p>
      <h1 className="mt-2 break-words text-3xl font-black text-blue-950">{category?.name ?? "Preguntas de la categoría"}</h1>
      {category?.description && <p className="mt-2 break-words text-slate-600">{category.description}</p>}
      {category && (state === "ready" || state === "error") && <CreateQuestionForm
        key={`${subjectId}-${blockId}-${categoryId}`} subjectId={subjectId} blockId={blockId}
        categoryId={categoryId} mode={mode} level={level} onRefresh={() => setAttempt((value) => value + 1)} />}
      {state === "loading" && <p role="status" className="mt-6 rounded-2xl bg-white p-6">Cargando preguntas…</p>}
      {state === "forbidden" && <p role="alert" className="notice-warning mt-6">Acceso no permitido. La consulta de preguntas está disponible para profesores y administradores.</p>}
      {state === "missing" && <p role="alert" className="notice-warning mt-6">La asignatura, el bloque o la categoría no existe en esta ruta.</p>}
      {state === "invalid" && <div className="mt-6"><p role="alert" className="notice-warning">Los filtros de la URL no son válidos.</p><Link href={base} className="text-link mt-3 inline-flex min-h-11 items-center">Ver todas las preguntas</Link></div>}
      {state === "error" && <div className="mt-6"><p role="alert" className="notice-error">No se pudieron consultar las preguntas. Comprueba la conexión e inténtalo de nuevo.</p><button type="button" className="button-secondary mt-4" onClick={retry}>Reintentar</button></div>}
      {state === "ready" && <>
        <p className="mt-4 text-sm text-slate-600">La categoría organiza contenidos académicos. La temática de juego que aparece en cada pregunta pertenece a la agrupación heredada Topic.</p>
        <form onSubmit={applyFilters} className="mt-7 flex flex-wrap items-end gap-4 rounded-2xl border border-slate-200 bg-white p-5" aria-label="Filtrar preguntas">
          <div className="min-w-44 flex-1"><label htmlFor="question-mode" className="form-label">Modalidad</label><select id="question-mode" value={selectedMode} onChange={(event) => setSelectedMode(event.target.value as GameMode | "")} className="form-input"><option value="">Ambas modalidades</option><option value="TRIVIAL">Trivial</option><option value="PASAPALABRA">Pasapalabra</option></select></div>
          <div className="min-w-44 flex-1"><label htmlFor="question-level" className="form-label">Dificultad</label><select id="question-level" value={selectedLevel} onChange={(event) => setSelectedLevel(event.target.value)} className="form-input"><option value="">Sin filtrar (incluye sin clasificar)</option>{[1, 2, 3, 4].map((value) => <option key={value} value={value}>Nivel {value}</option>)}<option value="unknown">Solo sin clasificar</option></select></div>
          <button type="submit" className="button-secondary">Aplicar filtros</button>
        </form>
        <section aria-labelledby="question-list-heading" className="mt-8">
          <h2 id="question-list-heading" className="text-xl font-bold text-blue-950">Preguntas</h2>
          {questions.length === 0 ? <p className="mt-4 rounded-2xl border border-slate-200 bg-white p-6 text-slate-600">{page > 1 ? "No hay preguntas en esta página." : mode || level ? "No hay preguntas que coincidan con estos filtros." : "Todavía no hay preguntas en esta categoría."}</p>
            : <ol className="mt-4 space-y-4">{questions.map((question) => <li key={question.id} className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <p className="break-words text-sm font-semibold text-sky-800">{question.question_type === "TRIVIAL" ? "Trivial" : "Pasapalabra"} · {question.difficulty === null ? "Dificultad sin clasificar" : `Nivel ${question.difficulty}`} · ID {question.id}</p>
              <h3 className="mt-2 break-words text-lg font-bold text-blue-950">{question.text}</h3>
              <p className="mt-2 break-words text-sm text-slate-600">Temática de juego (Topic): {question.topic.name} · ID {question.topic_id}</p>
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
