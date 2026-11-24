"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import Brand from "@/components/Brand";
import ProfileMenu from "@/components/ProfileMenu";
import api, { getCurrentUser } from "@/services/api";

type Target = "alumnado" | "profesorado";
type ImportIssue = { row: number; field: string; message: string };
const studentActions = {
  new_account: "Nueva matrícula",
  new_enrollment: "Nueva matrícula",
  existing_enrollment: "Matrícula existente · se conserva",
};
type Preview = {
  total: number;
  valid: number;
  errors: ImportIssue[];
  has_changes?: boolean;
  summary?: { new_accounts: number; new_enrollments: number; year_changes: number };
  preview: {
    row: number; dni: string; name: string; email: string;
    subject_code?: string; subject_name?: string; academic_year?: string; action?: keyof typeof studentActions;
    edition_id?: number; previous_edition_id?: number | null; account_row?: number | null;
    previous_year?: string | null; enabled_year?: string | null;
  }[];
  proof: string | null;
};
type Pending = { id: string; name: string; email: string; sent: boolean };
type PendingPage = { total: number; items: Pending[] };
type Receipt = { count: number; sent: number | null; replayed: boolean; enrolled?: number; already_enrolled?: number };

function affectedEditions(rows: Preview["preview"]) {
  const editions = new Map<number, string>();
  for (const row of rows) {
    if (row.edition_id) editions.set(row.edition_id, row.subject_name + " · " + course(row.academic_year));
    if (row.previous_edition_id && row.previous_year !== row.enabled_year) {
      editions.set(row.previous_edition_id, row.subject_name + " · " + course(row.previous_year));
    }
  }
  return Array.from(editions);
}

function course(year?: string | null) { return year?.replace("-", "–") ?? ""; }
const fieldLabels: Record<string, string> = {
  anio_academico: "Curso académico", codigo_asignatura: "Código de asignatura",
  "codigo_asignatura / anio_academico": "Código de asignatura / Curso académico",
  dni: "DNI", nombre: "Nombre", correo: "Correo",
};
const PAGE_SIZE = 25;

function errorMessage(error: unknown) {
  const detail = isAxiosError(error) ? error.response?.data?.detail : undefined;
  return typeof detail === "string" ? detail : "No se pudo completar la solicitud. Inténtalo de nuevo.";
}

export default function UserImportView({ target }: { target: Target }) {
  const router = useRouter();
  const base = "/user-imports/" + target;
  const isStudentImport = target === "alumnado";
  const [allowed, setAllowed] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [saved, setSaved] = useState<{ receipt: Receipt; editions: [number, string][]; changes: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [skip, setSkip] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [pending, setPending] = useState<PendingPage>();
  const [pendingError, setPendingError] = useState("");
  const [resending, setResending] = useState<string>();

  useEffect(() => {
    if (!window.localStorage.getItem("token")) {
      router.replace("/login");
      return;
    }
    let active = true;
    getCurrentUser().then(user => {
      if (!active) return;
      if (user.role !== (target === "alumnado" ? "teacher" : "admin")) {
        setError("Tu rol no permite gestionar estas altas.");
        return;
      }
      setAllowed(true);
    }).catch(err => { if (active) setError(errorMessage(err)); });
    return () => { active = false; };
  }, [router, target]);

  useEffect(() => {
    if (!allowed) return;
    let active = true;
    api.get<PendingPage>(base + "/pending", { params: { skip, limit: PAGE_SIZE } }).then(({ data }) => {
      if (!active) return;
      setPending(data);
      setPendingError("");
    }).catch(err => { if (active) setPendingError(errorMessage(err)); });
    return () => { active = false; };
  }, [allowed, base, skip, refresh]);

  async function downloadTemplate() {
    try {
      const { data } = await api.get<Blob>(base + "/template", { responseType: "blob" });
      const address = URL.createObjectURL(data);
      const link = document.createElement("a");
      link.href = address;
      link.download = target + ".csv";
      link.click();
      setTimeout(() => URL.revokeObjectURL(address), 1000);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function submit(confirm: boolean) {
    if (!file || busy || (confirm && !preview?.proof)) return;
    const form = new FormData();
    form.append("file", file);
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (!confirm) {
        setPreview(null);
        setSaved(null);
        const { data } = await api.post<Preview>(base + "/validate", form);
        setPreview(data);
        return;
      }
      form.append("proof", preview!.proof!);
      const { data } = await api.post<Receipt>(base + "/confirm", form);
      if (isStudentImport) {
        setSaved({ receipt: data, editions: affectedEditions(preview!.preview), changes: preview!.summary!.year_changes });
      } else {
        setNotice(data.replayed ? "Este lote ya se confirmó. Consulta abajo las cuentas pendientes."
          : `Cuentas creadas: ${data.count}. Invitaciones aceptadas por el correo: ${data.sent}. Puedes reenviar las pendientes.`);
      }
      setPreview(null);
      setSkip(0);
      setRefresh(n => n + 1);
    } catch (err) {
      const detail = isAxiosError(err) ? err.response?.data?.detail : undefined;
      if (confirm && detail && Array.isArray(detail.errors)) {
        setPreview({ ...detail, proof: null });
        setError("Hay conflictos nuevos. Corrige el CSV antes de confirmar.");
      } else {
        if (confirm && isAxiosError(err) && err.response?.status === 409) setPreview(null);
        setError(errorMessage(err));
      }
    } finally {
      setBusy(false);
    }
  }

  async function resend(id: string) {
    setResending(id);
    setPendingError("");
    setNotice("");
    try {
      const { data } = await api.post<{ sent: boolean }>(base + "/pending/" + id + "/resend");
      setNotice(data.sent ? "Invitación reenviada." : "El correo no aceptó la invitación. La cuenta sigue pendiente.");
      setRefresh(n => n + 1);
    } catch (err) {
      setPendingError(errorMessage(err));
    } finally {
      setResending(undefined);
    }
  }

  const previewContent = preview && <div className="space-y-3">
    <p className="break-all font-semibold">{file?.name}</p>
    <p role="status">{preview.total} {preview.total === 1 ? "fila" : "filas"} · {preview.valid} {preview.valid === 1 ? "válida" : "válidas"} · {preview.errors.length} {preview.errors.length === 1 ? "error" : "errores"}</p>
    {preview.summary && preview.errors.length === 0 && <dl className="grid gap-3 sm:grid-cols-3">
      {([["Cuentas nuevas", preview.summary.new_accounts], ["Matrículas nuevas", preview.summary.new_enrollments],
        ["Cambios de curso habilitado", preview.summary.year_changes]] as const).map(([label, value]) =>
        <div key={label} className="rounded-xl bg-slate-50 p-3"><dt className="text-sm">{label}</dt><dd className="text-2xl font-bold">{value}</dd></div>)}
    </dl>}
    {isStudentImport && preview.errors.length > 0 && <p className="notice-error" role="alert">El lote está bloqueado. Corrige las filas indicadas y vuelve a validar el archivo.</p>}
    {preview.errors.length > 0 && <ul className="list-disc space-y-1 pl-5">
      {preview.errors.map((issue, index) => <li key={index}>Fila {issue.row} · {fieldLabels[issue.field] ?? issue.field} · {issue.message}</li>)}
    </ul>}
    {preview.preview.length > 0 && <div className="overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead><tr>{["Fila", "DNI", "Nombre", "Correo", ...(isStudentImport ? ["Cuenta", "Edición", "Matrícula", "Curso habilitado para jugar"] : [])]
          .map(label => <th key={label} className="p-2" scope="col">{label}</th>)}</tr></thead>
        <tbody>{preview.preview.map(row => <tr key={row.row} className="border-t border-slate-200">
          <td className="p-2">{row.row}</td><td className="p-2">{row.dni}</td><td className="p-2">{row.name}</td><td className="p-2">{row.email}</td>
          {isStudentImport && <>
            <td className="p-2">{row.account_row && row.account_row !== row.row ? "Misma cuenta que la fila " + row.account_row
              : row.action === "new_account" ? "Se creará una cuenta" : "Se reutiliza la cuenta"}</td>
            <td className="p-2">{row.subject_name} · {course(row.academic_year)}</td>
            <td className="p-2">{row.action && studentActions[row.action]}</td>
            <td className="p-2">
              {row.previous_year && row.previous_year !== row.enabled_year
                ? <><span className="block">{row.subject_name}</span><strong className="whitespace-nowrap">{course(row.previous_year)} → {course(row.enabled_year)}</strong></>
                : row.enabled_year
                  ? course(row.enabled_year) + (row.previous_year ? " · se mantiene" : " · se habilitará")
                  : "Ninguno · se mantiene"}
            </td>
          </>}
        </tr>)}</tbody>
      </table>
    </div>}
    {!isStudentImport && preview.proof && <button type="button" className="button-primary" disabled={busy} onClick={() => void submit(true)}>
      Confirmar altas y enviar invitaciones
    </button>}
  </div>;

  return (
    <div className="min-h-screen bg-background text-slate-900">
      <header className="site-header">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-5 py-3"><Brand /><ProfileMenu /></div>
      </header>
      <main className="mx-auto max-w-5xl space-y-5 px-5 py-6">
        <Link href="/dashboard" className="text-link">← Volver al panel</Link>
        <h1 className="text-3xl font-black text-blue-950">Importar {target}</h1>
        {error && <p role="alert" className="notice-error">{error}</p>}
        {notice && <p role="status" className="notice-success">{notice}</p>}
        {!allowed && !error && <p role="status">Comprobando permisos…</p>}
        {allowed && <>
          <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5" aria-busy={busy}>
            <h2 className="text-xl font-bold">{isStudentImport ? "1. Subir CSV" : "Alta por CSV"}</h2>
            <p>{isStudentImport
              ? "Se matricula al alumnado en el curso indicado para cada asignatura. Si la persona ya tiene cuenta, se reutiliza. Si tenía otro curso habilitado, su matrícula anterior se conserva."
              : "Incluye DNI, nombre y correo."}</p>
            {isStudentImport && <>
              <p className="text-sm">Columnas obligatorias: DNI, nombre, correo, código de asignatura y curso académico.</p>
              <p className="text-sm">Consulta el código y los cursos disponibles en <Link href="/altas/ediciones" target="_blank" rel="noopener" className="text-link">Ediciones y matrículas (otra pestaña)</Link>.</p>
            </>}
            <details className="text-sm text-slate-600">
              <summary className="cursor-pointer rounded focus-visible:outline-2 focus-visible:outline-blue-800">Formato del CSV</summary>
              <p className="mt-2">UTF-8, separador de punto y coma (;). Máximo 100 filas y 256 KiB. Conserva las cabeceras de la plantilla.{isStudentImport && " Escribe el curso como 2026-2027."}</p>
            </details>
            <div className="flex flex-col items-start gap-3">
              <button className="button-secondary" type="button" onClick={() => void downloadTemplate()}>Descargar plantilla</button>
              <div className="flex w-full min-w-0 flex-wrap items-center gap-3">
                <button type="button" className="button-secondary min-h-11 shrink-0" disabled={busy}
                  onClick={() => fileInput.current?.click()} aria-describedby="selected-csv">Seleccionar archivo CSV</button>
                <input ref={fileInput} id="user-csv" type="file" accept=".csv,text/csv" disabled={busy} className="hidden"
                  aria-label="Archivo CSV" onChange={event => {
                    const chosen = event.target.files?.[0];
                    if (!chosen) return;
                    setFile(chosen); setPreview(null); setSaved(null); setError(""); setNotice("");
                  }} />
                <span id="selected-csv" role="status" className="min-w-0 max-w-full break-all text-sm">{file?.name ?? "Ningún archivo seleccionado"}</span>
              </div>
              <button type="button" className="button-primary" disabled={!file || busy} onClick={() => void submit(false)}>
                {busy ? "Procesando…" : "Validar sin guardar"}
              </button>
            </div>
            {!isStudentImport && previewContent}
          </section>
          {isStudentImport && <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="text-xl font-bold">2. Revisar cambios</h2>
            {!preview && <p>{saved ? "La revisión de este lote ha terminado." : "Selecciona un CSV y pulsa Validar sin guardar para revisar los cambios."}</p>}
            {previewContent}
            {preview?.proof && (preview.has_changes === false ? <>
              <p role="status">Este lote no requiere cambios.</p>
              <h3 className="font-bold">Ver matrículas existentes</h3>
              <ul className="space-y-2">{affectedEditions(preview.preview).map(([id, label]) =>
                <li key={id}><Link href={"/altas/ediciones?edicion=" + id} target="_blank" rel="noopener" className="text-link">{label} (otra pestaña)</Link></li>)}</ul>
            </> : <>
              <h3 className="text-xl font-bold">3. Confirmar importación</h3>
              <p className="text-sm">Al confirmar se guardarán estos cambios. Solo las cuentas nuevas recibirán invitación.</p>
              <button type="button" className="button-primary" disabled={busy} onClick={() => void submit(true)}>Confirmar importación</button>
            </>)}
          </section>}
          {isStudentImport && saved && <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="text-xl font-bold">3. Resultado</h2>
            {saved ? <>
              <div role="status" className="notice-success">
                <strong>{saved.receipt.replayed ? "Este lote ya estaba confirmado." : "Importación confirmada."}</strong>
                <p>Cuentas creadas: {saved.receipt.count}. Matrículas añadidas: {saved.receipt.enrolled}. Matrículas que ya existían: {saved.receipt.already_enrolled}. Cambios de curso habilitado: {saved.changes}.</p>
                {saved.receipt.sent != null && saved.receipt.count > 0 && <p>Invitaciones aceptadas por el correo: {saved.receipt.sent} de {saved.receipt.count}. {saved.receipt.sent < saved.receipt.count && "Puedes reenviar las pendientes más abajo."}</p>}
              </div>
              <h3 className="font-bold">Ver matrículas por edición</h3>
              <p className="text-sm text-slate-600">Cada listado se abre en otra pestaña para que puedas volver a este resumen.</p>
              <ul className="space-y-2">{saved.editions.map(([id, label]) =>
                <li key={id}><Link href={"/altas/ediciones?edicion=" + id} target="_blank" rel="noopener" className="text-link">{label}</Link></li>)}</ul>
            </> : null}
          </section>}
          <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="text-xl font-bold">Cuentas pendientes de activación</h2>
            {pendingError && <p role="alert" className="notice-error">{pendingError}</p>}
            {!pending && !pendingError && <p role="status">Cargando cuentas…</p>}
            {pending?.total === 0 && <p>Actualmente no hay cuentas pendientes.</p>}
            {pending && pending.items.length > 0 && <ul className="divide-y divide-slate-200">
              {pending.items.map(user => <li key={user.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div className="min-w-0 break-words">
                  <p className="font-semibold">{user.name}</p>
                  <p className="text-sm text-slate-600">{user.email} · {user.sent ? "Correo aceptado" : "Envío pendiente"}</p>
                </div>
                <button type="button" className="button-secondary" disabled={Boolean(resending)}
                  aria-label={`Reenviar invitación a ${user.name} (${user.email})`} onClick={() => void resend(user.id)}>
                  {resending === user.id ? "Enviando…" : "Reenviar invitación"}
                </button>
              </li>)}
            </ul>}
            {(skip > 0 || (pending && skip + PAGE_SIZE < pending.total)) && <div className="flex gap-3">
              <button className="button-secondary" disabled={!skip} onClick={() => setSkip(n => n - PAGE_SIZE)}>Anterior</button>
              <button className="button-secondary" disabled={!pending || skip + PAGE_SIZE >= pending.total} onClick={() => setSkip(n => n + PAGE_SIZE)}>Siguiente</button>
            </div>}
          </section>
        </>}
      </main>
    </div>
  );
}
