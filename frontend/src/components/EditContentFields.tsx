"use client";

import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from "react";
import { isAxiosError } from "axios";
import type { SubjectCreate } from "@/services/api";

type Content = { id: number; name: string; description: string | null };

export default function EditContentFields<T extends Content>({ item, save, onSaved, onForbidden, navigation }: {
  item: T; save: (payload: SubjectCreate) => Promise<T>; onSaved: (saved: T) => void;
  onForbidden: () => void; navigation?: ReactNode;
}) {
  const id = useId();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(item.name);
  const [description, setDescription] = useState(item.description ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const locked = useRef(false);
  const alive = useRef(true);
  const restoreFocus = useRef(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => {
    if (editing) input.current?.focus();
    else if (restoreFocus.current) { restoreFocus.current = false; trigger.current?.focus(); }
  }, [editing]);

  function close() {
    restoreFocus.current = true;
    setEditing(false);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked.current) return;
    if (!name.trim() || name.trim().length > 255) {
      setError("Escribe un nombre de entre 1 y 255 caracteres.");
      input.current?.focus();
      return;
    }
    locked.current = true; setBusy(true); setError(""); setNotice("");
    try {
      const saved = await save({ name: name.trim(), description: description || null });
      if (!alive.current) return;
      onSaved(saved);
      setNotice("Cambios guardados.");
      close();
    } catch (cause) {
      if (!alive.current) return;
      const status = isAxiosError(cause) ? cause.response?.status : undefined;
      if (status === 403) { onForbidden(); return; }
      if (status === 401) return; // Shared client handles expired authentication.
      setError(status === 422 ? "Revisa el nombre y la descripción."
        : status === 404 ? "El contenido ya no está disponible en esta ubicación. Actualiza el listado."
        : status === 409 ? "No se pudo guardar por un conflicto. Revisa los datos y actualiza el listado."
        : "No se pudo confirmar el guardado. Conservamos los campos; puedes reintentar o cancelar y comprobar el listado.");
    } finally {
      locked.current = false;
      if (alive.current) setBusy(false);
    }
  }

  return <div className="mt-4 border-t border-sky-100 pt-3">
    <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
    {navigation}
    <button ref={trigger} type="button" className="button-secondary" hidden={editing}
      aria-label={`Editar ${item.name}`} aria-expanded={editing} aria-controls={`${id}-form`}
      onClick={() => { setName(item.name); setDescription(item.description ?? ""); setError(""); setNotice(""); setEditing(true); }}>Editar</button>
    </div>
    {editing && <form id={`${id}-form`} aria-label={`Editar ${item.name}`} onSubmit={submit}
      aria-busy={busy} className="mt-3 space-y-3 rounded-xl border border-sky-200 bg-sky-50 p-4">
      <div><label className="form-label" htmlFor={`${id}-name`}>Nombre</label>
        <input ref={input} id={`${id}-name`} className="form-input" required maxLength={255}
          value={name} disabled={busy} onChange={(event) => setName(event.target.value)} /></div>
      <div><label className="form-label" htmlFor={`${id}-description`}>Descripción (opcional)</label>
        <textarea id={`${id}-description`} className="form-input resize-y" rows={3}
          value={description} disabled={busy} onChange={(event) => setDescription(event.target.value)} /></div>
      {error && <p role="alert" className="notice-error">{error}</p>}
      <div className="flex flex-wrap gap-3"><button type="submit" className="button-primary" disabled={busy}>{busy ? "Guardando…" : "Guardar"}</button>
        <button type="button" className="button-secondary" disabled={busy} onClick={close}>Cancelar</button></div>
    </form>}
    {notice && <p role="status" className="mt-2 text-sm font-semibold text-sky-800">{notice}</p>}
  </div>;
}
