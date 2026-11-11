"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { isAxiosError } from "axios";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Brand from "@/components/Brand";
import ProfileMenu from "@/components/ProfileMenu";
import ContentBreadcrumbs from "@/components/ContentBreadcrumbs";
import EditContentFields from "@/components/EditContentFields";
import CreateContentPanel from "@/components/CreateContentPanel";
import { canManageSubjects, SUBJECTS_PAGE_SIZE, visibleSubjectsPage } from "@/lib/subjects";
import { editSubject, createSubject, getCurrentUser, getSubjects, type Subject } from "@/services/api";

type ViewState = "loading" | "ready" | "error" | "forbidden";

export default function SubjectsView({ page }: { page: number }) {
  const router = useRouter();
  const [state, setState] = useState<ViewState>("loading");
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [created, setCreated] = useState<Subject | null>(null);
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
        if (!canManageSubjects(user.role)) {
          setSubjects([]);
          setCreated(null);
          setState("forbidden");
          return;
        }
        const received = await getSubjects((page - 1) * SUBJECTS_PAGE_SIZE, SUBJECTS_PAGE_SIZE + 1);
        if (!active || !window.localStorage.getItem("token")) return;
        const visible = visibleSubjectsPage(received);
        setSubjects(visible.items);
        setHasMore(visible.hasMore);
        setState("ready");
      } catch (error) {
        if (!active) return;
        const status = isAxiosError(error) ? error.response?.status : undefined;
        if (status === 401) return; // The shared client redirects on expired credentials.
        if (status === 403) {
          setSubjects([]);
          setCreated(null);
          setState("forbidden");
        } else {
          setState("error");
        }
      }
    }
    void load();
    return () => { active = false; mountedRef.current = false; };
  }, [attempt, page, router]);

  function retry() {
    setState("loading");
    setAttempt((value) => value + 1);
  }

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
      const result = await createSubject({ name: cleanedName, description: description || null });
      if (!mountedRef.current || !window.localStorage.getItem("token")) return;
      setCreated(result);
      setName("");
      setDescription("");
    } catch (error) {
      if (!mountedRef.current) return;
      const status = isAxiosError(error) ? error.response?.status : undefined;
      if (status === 401) return;
      if (status === 403) {
        setSubjects([]);
        setCreated(null);
        setState("forbidden");
      } else if (status === 422) {
        setSubmitError("Revisa el nombre y la descripción. No se creó la asignatura.");
      } else {
        setSubmitError("No se pudo crear la asignatura. Conservamos los campos para que puedas reintentar.");
      }
    } finally {
      submittingRef.current = false;
      if (mountedRef.current) setSubmitting(false);
    }
  }

  function logout() {
    window.localStorage.removeItem("token");
    setSubjects([]);
    setCreated(null);
    setState("loading");
    router.replace("/login");
  }

  return <div className="min-h-screen bg-background text-slate-900">
    <header className="site-header"><nav aria-label="Gestión de contenidos" className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-5 py-5 sm:px-8"><Brand /><div className="flex flex-wrap items-center gap-2"><ProfileMenu /><button className="button-primary" onClick={logout}>Cerrar sesión</button></div></nav></header>
    <main className="mx-auto max-w-5xl px-5 py-8 sm:px-8 sm:py-12" aria-busy={state === "loading"}>
      <ContentBreadcrumbs />
      <p className="mt-5 text-xs font-bold uppercase tracking-widest text-orange-700">Gestión de contenidos</p>
      <h1 className="mt-2 text-3xl font-black text-blue-950">Asignaturas</h1>
      <p className="mt-2 max-w-2xl text-slate-600">Consulta, crea y edita asignaturas para organizar el contenido académico.</p>

      {state === "loading" && <p role="status" className="mt-6 rounded-2xl bg-white p-6">Cargando asignaturas…</p>}
      {state === "forbidden" && <p role="alert" className="notice-warning mt-6">Acceso no permitido. La gestión de contenidos está disponible para profesores y administradores.</p>}
      {state === "error" && <div className="mt-6"><p role="alert" className="notice-error">No se pudieron consultar las asignaturas. Comprueba la conexión e inténtalo de nuevo.</p><button type="button" className="button-secondary mt-4" onClick={retry}>Reintentar</button></div>}
      {state === "ready" && <>
        <section aria-labelledby="subject-list-heading" className="mt-8">
          <h2 id="subject-list-heading" className="text-xl font-bold text-blue-950">Asignaturas registradas</h2>
          {subjects.length === 0 ? <p className="mt-4 rounded-2xl border border-slate-200 bg-white p-6 text-slate-600">{created ? "El listado se cargó antes de crear la asignatura. Puedes actualizarlo para consultar su ubicación." : page === 1 ? "Todavía no hay asignaturas registradas." : "No hay asignaturas en esta página."}</p>
            : <ol className="mt-4 grid items-start gap-4 sm:grid-cols-2">{subjects.map((subject) => <li key={subject.id} className="min-w-0 rounded-2xl border border-sky-200 bg-white p-5 shadow-sm"><h3 className="break-words text-lg font-bold text-blue-950">{subject.name}</h3>{subject.description && <p className="mt-2 break-words text-sm leading-6 text-slate-600">{subject.description}</p>}<EditContentFields navigation={<Link href={`/gestion/asignaturas/${subject.id}`} className="text-link inline-flex min-h-11 items-center">Ver bloques →</Link>} item={subject} save={(payload) => editSubject(subject.id, payload)} onSaved={(saved) => setSubjects((current) => current.map((entry) => entry.id === saved.id ? saved : entry))} onForbidden={() => setState("forbidden")} /></li>)}</ol>}
          <nav aria-label="Páginas de asignaturas" className="mt-6 flex flex-wrap items-center justify-between gap-4">
            {page > 1 ? <Link href={page === 2 ? "/gestion/asignaturas" : `/gestion/asignaturas?page=${page - 1}`} className="button-secondary">Anterior</Link> : <span />}
            <span className="text-sm font-semibold text-slate-600">Página {page}</span>
            {hasMore && <Link href={`/gestion/asignaturas?page=${page + 1}`} className="button-secondary">Siguiente</Link>}
          </nav>
        </section>

        <CreateContentPanel id="create-subject" label="Crear asignatura" busy={submitting}>
          <form onSubmit={submit} className="space-y-5">
            <div><label htmlFor="subject-name" className="form-label">Nombre</label><input id="subject-name" name="name" type="text" required maxLength={255} value={name} onChange={(event) => setName(event.target.value)} disabled={submitting} className="form-input" /></div>
            <div><label htmlFor="subject-description" className="form-label">Descripción (opcional)</label><textarea id="subject-description" name="description" rows={3} value={description} onChange={(event) => setDescription(event.target.value)} disabled={submitting} className="form-input resize-y" /></div>
            {submitError && <p role="alert" className="notice-error">{submitError}</p>}
            <button type="submit" disabled={submitting} className="button-primary">{submitting ? "Creando…" : "Crear asignatura"}</button>
          </form>
        </CreateContentPanel>
        {created && <div role="status" className="notice-success mt-4"><p className="font-bold">Asignatura creada</p><p className="mt-1 break-words">{created.name}</p>{created.description && <p className="mt-1 break-words">{created.description}</p>}<p className="mt-2 text-xs">ID {created.id}. El listado conserva su página actual.</p><div className="mt-2 flex flex-wrap gap-4"><Link href={`/gestion/asignaturas/${created.id}`} className="text-link inline-flex min-h-11 items-center">Ver bloques →</Link><button type="button" className="text-link min-h-11" onClick={retry}>Actualizar listado</button></div></div>}
      </>}
    </main>
  </div>;
}
