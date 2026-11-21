"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import Brand from "@/components/Brand";
import ProfileMenu from "@/components/ProfileMenu";
import api, { getCurrentUser } from "@/services/api";

type Target = "alumnado" | "profesorado";
type ImportIssue = { row: number; field: string; message: string };
type Preview = {
  total: number;
  valid: number;
  errors: ImportIssue[];
  preview: { row: number; dni: string; name: string; email: string }[];
  proof: string | null;
};
type Pending = { id: string; name: string; email: string; sent: boolean };
type PendingPage = { total: number; items: Pending[] };
const PAGE_SIZE = 25;

function errorMessage(error: unknown) {
  const detail = isAxiosError(error) ? error.response?.data?.detail : undefined;
  return typeof detail === "string" ? detail : "No se pudo completar la solicitud. Inténtalo de nuevo.";
}

export default function UserImportView({ target }: { target: Target }) {
  const router = useRouter();
  const base = "/user-imports/" + target;
  const [allowed, setAllowed] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
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
        const { data } = await api.post<Preview>(base + "/validate", form);
        setPreview(data);
        return;
      }
      form.append("proof", preview!.proof!);
      const { data } = await api.post<{ count: number; sent: number | null; replayed: boolean }>(base + "/confirm", form);
      setNotice(data.replayed
        ? "Este lote ya se confirmó. Consulta abajo las cuentas pendientes."
        : `Cuentas creadas: ${data.count}. Invitaciones aceptadas por el correo: ${data.sent}. Puedes reenviar las pendientes.`);
      setPreview(null);
      setSkip(0);
      setRefresh(n => n + 1);
    } catch (err) {
      const detail = isAxiosError(err) ? err.response?.data?.detail : undefined;
      if (confirm && detail && Array.isArray(detail.errors)) {
        setPreview({ ...detail, proof: null });
        setError("Hay conflictos nuevos. Corrige el CSV antes de confirmar.");
      } else {
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
            <h2 className="text-xl font-bold">Alta por CSV</h2>
            <p className="text-sm text-slate-600">Incluye DNI, nombre y correo. Usa UTF-8 y separador de punto y coma. Máximo 100 filas y 256 KiB.</p>
            <div className="flex flex-wrap items-center gap-3">
              <button className="button-secondary" type="button" onClick={() => void downloadTemplate()}>Descargar plantilla</button>
              <label className="form-label" htmlFor="user-csv">Archivo CSV</label>
              <input id="user-csv" type="file" accept=".csv,text/csv" disabled={busy} className="max-w-full"
                onChange={event => { setFile(event.target.files?.[0] ?? null); setPreview(null); setError(""); setNotice(""); }} />
            </div>
            <button type="button" className="button-primary" disabled={!file || busy} onClick={() => void submit(false)}>
              Validar sin guardar
            </button>
            {preview && <div className="space-y-3">
              <p role="status">{preview.total} filas · {preview.valid} válidas · {preview.errors.length} errores</p>
              {preview.errors.length > 0 && <ul className="list-disc space-y-1 pl-5">
                {preview.errors.map((issue, index) => <li key={index}>Fila {issue.row} · {issue.field} · {issue.message}</li>)}
              </ul>}
              {preview.preview.length > 0 && <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead><tr>{["Fila", "DNI", "Nombre", "Correo"].map(label => <th key={label} className="p-2" scope="col">{label}</th>)}</tr></thead>
                  <tbody>{preview.preview.map(row => <tr key={row.row} className="border-t border-slate-200">
                    <td className="p-2">{row.row}</td><td className="p-2">{row.dni}</td><td className="p-2">{row.name}</td><td className="p-2">{row.email}</td>
                  </tr>)}</tbody>
                </table>
              </div>}
              {preview.proof && <button type="button" className="button-primary" disabled={busy} onClick={() => void submit(true)}>
                Confirmar altas y enviar invitaciones
              </button>}
            </div>}
          </section>
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
