"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import Brand from "@/components/Brand";
import ProfileMenu from "@/components/ProfileMenu";
import api, { getCurrentUser } from "@/services/api";

type Subject = { id: number; name: string; code: string | null };
type Edition = { id: number; subject_name: string; subject_code: string; academic_year: string };
type Enrollment = {
  id: string; name: string; email: string; play_enabled: boolean;
  enabled_edition_id: number | null; enabled_year: string | null;
};
type Page<T> = { items: T[]; has_more: boolean };

const base = "/academic-editions";
const pageSize = 25;

function failure(error: unknown) {
  const detail = isAxiosError(error) ? error.response?.data?.detail : undefined;
  if (typeof detail === "string") return detail;
  return Array.isArray(detail) && typeof detail[0]?.msg === "string"
    ? detail[0].msg.replace(/^Value error, /, "")
    : "No se pudo completar la solicitud. Inténtalo de nuevo.";
}

function PageControls({ skip, setSkip, hasMore }: { skip: number; setSkip: (value: number) => void; hasMore?: boolean }) {
  if (skip === 0 && !hasMore) return null;
  return (
    <div className="flex flex-wrap gap-2">
      <button type="button" className="button-secondary" disabled={!skip} onClick={() => setSkip(skip - pageSize)}>Anterior</button>
      <button type="button" className="button-secondary" disabled={!hasMore} onClick={() => setSkip(skip + pageSize)}>Siguiente</button>
    </div>
  );
}

export default function AcademicEditionsView({ editionId }: { editionId?: number }) {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [subjects, setSubjects] = useState<Page<Subject>>();
  const [editions, setEditions] = useState<Page<Edition>>();
  const [roster, setRoster] = useState<Page<Enrollment> & { edition: Edition }>();
  const [selectedId, setSelectedId] = useState(editionId);
  const selected = roster?.edition;
  const [pick, setPick] = useState<Enrollment>();
  const [subjectPage, setSubjectPage] = useState(0);
  const [editionPage, setEditionPage] = useState(0);
  const [rosterPage, setRosterPage] = useState(0);
  const [subjectId, setSubjectId] = useState("");
  const [code, setCode] = useState("");
  const [year, setYear] = useState("");
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const subject = subjects?.items.find(item => String(item.id) === subjectId);

  useEffect(() => {
    if (!window.localStorage.getItem("token")) {
      router.replace("/login");
      return;
    }
    let active = true;
    getCurrentUser().then(user => {
      if (!active) return;
      if (user.role === "teacher") setAllowed(true);
      else setError("Esta gestión está reservada al profesorado.");
    }).catch(err => { if (active) setError(failure(err)); });
    return () => { active = false; };
  }, [router]);

  useEffect(() => {
    if (!allowed || editionId) return;
    let active = true;
    api.get<Page<Subject>>(base + "/subjects", { params: { skip: subjectPage, limit: pageSize } })
      .then(({ data }) => { if (active) setSubjects(data); })
      .catch(err => { if (active) setError(failure(err)); });
    return () => { active = false; };
  }, [allowed, editionId, subjectPage, revision]);

  useEffect(() => {
    if (!allowed || editionId) return;
    let active = true;
    api.get<Page<Edition>>(base, { params: { skip: editionPage, limit: pageSize } })
      .then(({ data }) => { if (active) setEditions(data); })
      .catch(err => { if (active) setError(failure(err)); });
    return () => { active = false; };
  }, [allowed, editionId, editionPage, revision]);

  useEffect(() => {
    if (!allowed || !selectedId) return;
    let active = true;
    api.get<Page<Enrollment> & { edition: Edition }>(base + "/" + selectedId + "/enrollments", { params: { skip: rosterPage, limit: pageSize } })
      .then(({ data }) => { if (active) setRoster(data); })
      .catch(err => { if (active) setError(failure(err)); });
    return () => { active = false; };
  }, [allowed, selectedId, rosterPage, revision]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!subject || busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const { data } = await api.post<Edition>(base, {
        subject_id: subject.id, subject_code: subject.code ?? code.trim(), academic_year: year.trim(),
      });
      setNotice("Edición creada. Usa " + data.subject_code + " y " + data.academic_year + " en el CSV.");
      setYear("");
      setCode("");
      setSubjectId("");
      setEditionPage(0);
      setRevision(value => value + 1);
    } catch (err) {
      setError(failure(err));
    } finally {
      setBusy(false);
    }
  }

  async function enable() {
    if (!selected || !pick || busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api.put(base + "/" + selected.id + "/enrollments/" + pick.id + "/play", {
        expected_edition_id: pick.enabled_edition_id,
      });
      setNotice("Edición habilitada para " + pick.name + ". Se conservan sus otras matrículas.");
      setPick(undefined);
      setRevision(value => value + 1);
    } catch (err) {
      setError(failure(err));
      setPick(undefined);
      setRevision(value => value + 1);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-background text-slate-900">
      <header className="site-header">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-5 py-3"><Brand /><ProfileMenu /></div>
      </header>
      <main className="mx-auto max-w-5xl space-y-5 px-5 py-6">
        <Link href="/altas/alumnado" className="text-link">← Volver a Importar alumnado</Link>
        <h1 className="text-3xl font-black text-blue-950">Ediciones académicas</h1>
        {error && <p role="alert" className="notice-error">{error}</p>}
        {notice && <p role="status" className="notice-success">{notice}</p>}
        {!allowed && !error && <p role="status">Comprobando permisos…</p>}
        {allowed && <>
          {!editionId && <>
          <form className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5" onSubmit={create}>
            <h2 className="text-xl font-bold">Crear edición</h2>
            <p>Selecciona una asignatura existente y el año. El código de asignatura se utiliza en el CSV y se asigna al crear su primera edición.</p>
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label htmlFor="edition-subject" className="form-label">Asignatura</label>
                <select id="edition-subject" className="form-input" value={subjectId} required disabled={busy}
                  onChange={event => { setSubjectId(event.target.value); setCode(""); }}>
                  <option value="">Selecciona una asignatura</option>
                  {subjects?.items.map(item => <option key={item.id} value={item.id}>{item.name}{item.code ? " · " + item.code : " · " + item.id}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="edition-code" className="form-label">Código de asignatura</label>
                <input id="edition-code" className="form-input" value={subject?.code ?? code} maxLength={32}
                  required readOnly={Boolean(subject?.code)} disabled={busy || !subject}
                  onChange={event => setCode(event.target.value)} />
              </div>
              <div>
                <label htmlFor="edition-year" className="form-label">Año académico</label>
                <input id="edition-year" className="form-input" value={year} placeholder="2026-2027" maxLength={9}
                  required disabled={busy} onChange={event => setYear(event.target.value)} />
              </div>
            </div>
            {subjects?.items.length === 0 && <p>Primero crea una asignatura en Gestión de contenidos.</p>}
            <PageControls skip={subjectPage} hasMore={subjects?.has_more} setSkip={value => {
              setSubjectPage(value); setSubjectId(""); setSubjects(undefined); setCode("");
            }} />
            <button type="submit" className="button-primary" disabled={!subject || busy}>Crear edición</button>
          </form>

          <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="text-xl font-bold">Ediciones disponibles</h2>
            {editions?.items.length === 0 && <p>Todavía no hay ediciones académicas.</p>}
            <ul className="divide-y divide-slate-200">
              {editions?.items.map(edition => <li key={edition.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <p className="min-w-0 break-words">{edition.subject_name} · {edition.subject_code} · {edition.academic_year}</p>
                <button type="button" className="button-secondary" aria-pressed={selectedId === edition.id}
                  disabled={busy} onClick={() => {
                    if (selectedId === edition.id) return;
                    setSelectedId(edition.id); setPick(undefined); setRoster(undefined); setRosterPage(0);
                  }}>Ver matrículas</button>
              </li>)}
            </ul>
            <PageControls skip={editionPage} hasMore={editions?.has_more} setSkip={value => {
              setEditionPage(value); setEditions(undefined);
            }} />
          </section>

          </>}
          {editionId && <Link href="/altas/ediciones" className="text-link">Ver todas las ediciones</Link>}
          {selectedId && !roster && !error && <p role="status">Cargando matrículas…</p>}
          {selected && <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="text-xl font-bold">Matrículas de {selected.subject_name} · {selected.academic_year}</h2>
            <p>Solo puede quedar habilitado un año por alumno y asignatura. El cambio conserva todas sus matrículas.</p>
            {pick && <div className="space-y-2 rounded-xl border border-orange-300 bg-orange-50 p-4">
              <p>Habilitar {selected.academic_year} para <strong>{pick.name}</strong> ({pick.email}).
                {pick.enabled_year && " El año " + pick.enabled_year + " dejará de estar habilitado."}</p>
              <div className="flex flex-wrap gap-2">
                <button type="button" className="button-primary" disabled={busy} onClick={() => void enable()}>Confirmar cambio</button>
                <button type="button" className="button-secondary" disabled={busy} onClick={() => setPick(undefined)}>Cancelar</button>
              </div>
            </div>}
            {roster?.items.length === 0 && <p>Esta edición todavía no tiene matrículas.</p>}
            <ul className="divide-y divide-slate-200">
              {roster?.items.map(item => <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div className="min-w-0 break-words">
                  <p className="font-semibold">{item.name}</p>
                  <p className="text-sm text-slate-600">{item.email} · {item.play_enabled ? "Habilitada para jugar"
                    : item.enabled_year ? "Año habilitado: " + item.enabled_year : "Sin año habilitado"}</p>
                </div>
                {!item.play_enabled && <button type="button" className="button-secondary" disabled={busy}
                  aria-label={"Habilitar esta edición para " + item.name} onClick={() => setPick(item)}>Habilitar esta edición</button>}
              </li>)}
            </ul>
            <PageControls skip={rosterPage} hasMore={roster?.has_more} setSkip={value => {
              setRosterPage(value); setPick(undefined); setRoster(undefined);
            }} />
          </section>}
        </>}
      </main>
    </div>
  );
}
