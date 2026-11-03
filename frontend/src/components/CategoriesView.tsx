"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { isAxiosError } from "axios";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Brand from "@/components/Brand";
import LinkCategory from "@/components/LinkCategory";
import { canManageSubjects, SUBJECTS_PAGE_SIZE, visibleCategoriesPage } from "@/lib/subjects";
import { createCategory, getCategories, getContentBlock, getCurrentUser,
  type Category, type ContentBlockDetail } from "@/services/api";

type ViewState = "loading" | "ready" | "error" | "forbidden" | "missing";

export default function CategoriesView({ subjectId, blockId, page }: {
  subjectId: number; blockId: number; page: number;
}) {
  const router = useRouter();
  const [state, setState] = useState<ViewState>("loading");
  const [block, setBlock] = useState<ContentBlockDetail | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [created, setCreated] = useState<Category | null>(null);
  const submittingRef = useRef(false);
  const mountedRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    if (!window.localStorage.getItem("token")) {
      router.replace("/login");
      return () => { mountedRef.current = false; };
    }
    let active = true;
    async function load() {
      try {
        const user = await getCurrentUser();
        if (!active || !window.localStorage.getItem("token")) return;
        if (!canManageSubjects(user.role)) { setState("forbidden"); return; }
        if (!Number.isSafeInteger(subjectId) || subjectId < 1 ||
            !Number.isSafeInteger(blockId) || blockId < 1) { setState("missing"); return; }
        const [detail, received] = await Promise.all([
          getContentBlock(subjectId, blockId),
          getCategories(subjectId, blockId, (page - 1) * SUBJECTS_PAGE_SIZE, SUBJECTS_PAGE_SIZE + 1),
        ]);
        if (!active || !window.localStorage.getItem("token")) return;
        const visible = visibleCategoriesPage(received);
        setBlock(detail);
        setCategories(visible.items);
        setHasMore(visible.hasMore);
        setState("ready");
      } catch (error) {
        if (!active) return;
        const status = isAxiosError(error) ? error.response?.status : undefined;
        if (status === 401) return;
        if (status === 403 || status === 404) {
          setBlock(null); setCategories([]); setCreated(null);
          setState(status === 403 ? "forbidden" : "missing");
        } else setState("error");
      }
    }
    void load();
    return () => { active = false; mountedRef.current = false; };
  }, [attempt, blockId, page, router, subjectId]);

  function retry() { setState("loading"); setAttempt((value) => value + 1); }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submittingRef.current || state !== "ready") return;
    const cleanedName = name.trim();
    if (!cleanedName || cleanedName.length > 255) {
      setSubmitError("Escribe un nombre de entre 1 y 255 caracteres.");
      return;
    }
    submittingRef.current = true;
    setSubmitting(true);
    setSubmitError("");
    setCreated(null);
    try {
      const result = await createCategory(subjectId, blockId,
        { name: cleanedName, description: description || null });
      if (!mountedRef.current || !window.localStorage.getItem("token")) return;
      setCreated(result);
      setName(""); setDescription("");
    } catch (error) {
      if (!mountedRef.current) return;
      const status = isAxiosError(error) ? error.response?.status : undefined;
      if (status === 401) return;
      if (status === 403 || status === 404) {
        setBlock(null); setCategories([]); setCreated(null);
        setState(status === 403 ? "forbidden" : "missing");
      } else if (status === 422) setSubmitError("Revisa el nombre y la descripción. No se creó la categoría.");
      else setSubmitError("No se pudo crear la categoría. Conservamos los campos para que puedas reintentar.");
    } finally {
      submittingRef.current = false;
      if (mountedRef.current) setSubmitting(false);
    }
  }

  function logout() {
    window.localStorage.removeItem("token");
    setBlock(null); setCategories([]); setCreated(null); setState("loading");
    router.replace("/login");
  }

  const base = `/gestion/asignaturas/${subjectId}/bloques/${blockId}`;
  return <div className="min-h-screen bg-background text-slate-900">
    <header className="site-header"><nav aria-label="Gestión de contenidos" className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-5 sm:px-8"><Brand /><button className="button-primary" onClick={logout}>Cerrar sesión</button></nav></header>
    <main className="mx-auto max-w-5xl px-5 py-8 sm:px-8 sm:py-12" aria-busy={state === "loading"}>
      <nav aria-label="Volver" className="flex flex-wrap gap-x-6 gap-y-1"><Link href={`/gestion/asignaturas/${subjectId}`} className="text-link inline-flex min-h-11 items-center">← Bloques</Link><Link href="/gestion/asignaturas" className="text-link inline-flex min-h-11 items-center">Asignaturas</Link><Link href="/dashboard" className="text-link inline-flex min-h-11 items-center">Volver al panel</Link></nav>
      <p className="mt-5 text-xs font-bold uppercase tracking-widest text-orange-700">Gestión de contenidos</p>
      {block && <p className="mt-2 break-words text-sm font-semibold text-sky-800">{block.subject.name}</p>}
      <h1 className="mt-2 break-words text-3xl font-black text-blue-950">{block?.name ?? "Categorías"}</h1>
      {block?.description && <p className="mt-2 break-words text-slate-600">{block.description}</p>}
      {state === "loading" && <p role="status" className="mt-6 rounded-2xl bg-white p-6">Cargando categorías…</p>}
      {state === "forbidden" && <p role="alert" className="notice-warning mt-6">Acceso no permitido. La gestión de contenidos está disponible para profesores y administradores.</p>}
      {state === "missing" && <p role="alert" className="notice-warning mt-6">El bloque no existe en esta asignatura o ya no está disponible.</p>}
      {state === "error" && <div className="mt-6"><p role="alert" className="notice-error">No se pudieron consultar las categorías. Comprueba la conexión e inténtalo de nuevo.</p><button type="button" className="button-secondary mt-4" onClick={retry}>Reintentar</button></div>}
      {state === "ready" && <>
        <section aria-labelledby="categories-heading" className="mt-8">
          <h2 id="categories-heading" className="text-xl font-bold text-blue-950">Categorías del bloque</h2>
          {categories.length === 0 ? <p className="mt-4 rounded-2xl border border-slate-200 bg-white p-6 text-slate-600">{created ? "El listado se cargó antes de crear la categoría. Puedes actualizarlo para consultar su ubicación." : page === 1 ? "Todavía no hay categorías en este bloque." : "No hay categorías en esta página."}</p>
            : <ol className="mt-4 grid gap-4 sm:grid-cols-2">{categories.map((category) => <li key={category.id} className="min-w-0 rounded-2xl border border-sky-200 bg-white p-5 shadow-sm"><h3 className="break-words text-lg font-bold text-blue-950">{category.name}</h3>{category.description && <p className="mt-2 break-words text-sm leading-6 text-slate-600">{category.description}</p>}</li>)}</ol>}
          <nav aria-label="Páginas de categorías" className="mt-6 flex flex-wrap items-center justify-between gap-4">
            {page > 1 ? <Link href={page === 2 ? base : `${base}?page=${page - 1}`} className="button-secondary">Anterior</Link> : <span />}
            <span className="text-sm font-semibold text-slate-600">Página {page}</span>
            {hasMore && <Link href={`${base}?page=${page + 1}`} className="button-secondary">Siguiente</Link>}
          </nav>
        </section>
        {block && <LinkCategory block={block} onLinked={() => setAttempt((value) => value + 1)} />}
        <section aria-labelledby="create-category-heading" className="mt-9 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
          <h2 id="create-category-heading" className="text-xl font-bold text-blue-950">Crear categoría</h2>
          <form onSubmit={submit} className="mt-5 space-y-5">
            <div><label htmlFor="category-name" className="form-label">Nombre</label><input id="category-name" type="text" required maxLength={255} value={name} onChange={(event) => setName(event.target.value)} disabled={submitting} className="form-input" /></div>
            <div><label htmlFor="category-description" className="form-label">Descripción (opcional)</label><textarea id="category-description" rows={3} value={description} onChange={(event) => setDescription(event.target.value)} disabled={submitting} className="form-input resize-y" /></div>
            {submitError && <p role="alert" className="notice-error">{submitError}</p>}
            <button type="submit" disabled={submitting} className="button-primary">{submitting ? "Creando…" : "Crear categoría"}</button>
          </form>
          {created && <div role="status" className="notice-success mt-6"><p className="font-bold">Categoría creada</p><p className="mt-1 break-words">{created.name}</p>{created.description && <p className="mt-1 break-words">{created.description}</p>}<p className="mt-2 text-xs">ID {created.id}. El listado conserva su página actual.</p><button type="button" className="text-link mt-2 min-h-11" onClick={retry}>Actualizar listado</button></div>}
        </section>
      </>}
    </main>
  </div>;
}
