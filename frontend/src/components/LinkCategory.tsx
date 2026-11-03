"use client";

import { useEffect, useRef, useState } from "react";
import { isAxiosError } from "axios";
import { SUBJECTS_PAGE_SIZE, visibleUnassignedPage } from "@/lib/subjects";
import { getUnassignedCategories, linkCategory, type ContentBlockDetail, type UnassignedCategory } from "@/services/api";

export default function LinkCategory({ block, onLinked }: { block: ContentBlockDetail; onLinked: () => void }) {
  const [open, setOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<UnassignedCategory[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [state, setState] = useState<"loading" | "ready" | "error" | "forbidden">("loading");
  const [retry, setRetry] = useState(0);
  const [selected, setSelected] = useState<UnassignedCategory | null>(null);
  const [linked, setLinked] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submittingRef = useRef(false);

  useEffect(() => {
    if (!open) return;
    let active = true;
    async function load() {
      try {
        const received = await getUnassignedCategories((page - 1) * SUBJECTS_PAGE_SIZE, SUBJECTS_PAGE_SIZE + 1);
        if (!active || !window.localStorage.getItem("token")) return;
        const visible = visibleUnassignedPage(received);
        setItems(visible.items);
        setHasMore(visible.hasMore);
        setState("ready");
      } catch (cause) {
        if (!active) return;
        const status = isAxiosError(cause) ? cause.response?.status : undefined;
        if (status === 403) setState("forbidden");
        else if (status !== 401) setState("error");
      }
    }
    void load();
    return () => { active = false; };
  }, [open, page, retry]);

  function refresh() { setState("loading"); setRetry((value) => value + 1); }

  async function confirm() {
    if (!selected || submittingRef.current) return;
    submittingRef.current = true;
    setSubmitting(true);
    setError("");
    try {
      const result = await linkCategory(block.subject_id, block.id, selected.id);
      if (!window.localStorage.getItem("token")) return;
      setLinked(`${result.name} (ID ${result.id})`);
      setSelected(null);
      refresh();
      onLinked();
    } catch (cause) {
      const status = isAxiosError(cause) ? cause.response?.status : undefined;
      if (status === 409) { setError("Otra operación ya vinculó esta categoría a otro bloque. Actualiza la lista y elige otra."); setSelected(null); refresh(); }
      else if (status === 404) { setError("La categoría o el bloque ya no está disponible. Actualiza la lista."); setSelected(null); refresh(); }
      else if (status === 403) setState("forbidden");
      else if (status !== 401) setError("No se pudo vincular la categoría. Puedes reintentar sin perder la selección.");
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  return <section aria-labelledby="link-category-heading" className="mt-9 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
    <h2 id="link-category-heading" className="text-xl font-bold text-blue-950">Vincular categoría existente</h2>
    <p className="mt-2 text-sm text-slate-600">Elige una categoría que todavía no pertenece a ningún bloque.</p>
    <button type="button" className="button-secondary mt-4" aria-expanded={open} aria-controls="unassigned-categories" onClick={() => setOpen((value) => !value)}>{open ? "Ocultar categorías" : "Mostrar categorías sin bloque"}</button>
    {linked && <p role="status" className="notice-success mt-4">Categoría vinculada: {linked}. Ya aparece en este bloque.</p>}
    {open && <div id="unassigned-categories" className="mt-5">
      {state === "loading" && <p role="status">Cargando categorías sin bloque…</p>}
      {state === "forbidden" && <p role="alert" className="notice-warning">Acceso no permitido. Vuelve a iniciar sesión con un rol docente.</p>}
      {state === "error" && <div><p role="alert" className="notice-error">No se pudieron consultar las categorías sin bloque.</p><button type="button" className="button-secondary mt-3" onClick={refresh}>Reintentar</button></div>}
      {state === "ready" && <>
        {items.length === 0 ? <p className="text-slate-600">No hay categorías sin bloque en esta página.</p> : <fieldset><legend className="mb-3 font-semibold text-blue-950">Categorías disponibles</legend><div className="grid gap-3 sm:grid-cols-2">{items.map((item) => <label key={item.id} className="flex cursor-pointer gap-3 rounded-xl border border-sky-200 p-4 focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-blue-800"><input type="radio" name="unassigned-category" checked={selected?.id === item.id} onChange={() => { setSelected(item); setError(""); }} className="mt-1" /><span className="min-w-0"><strong className="block break-words">{item.name}</strong>{item.description && <span className="mt-1 block break-words text-sm text-slate-600">{item.description}</span>}<span className="block text-xs text-slate-500">ID {item.id}</span></span></label>)}</div></fieldset>}
        <nav aria-label="Páginas de categorías sin bloque" className="mt-4 flex items-center justify-between gap-3"><button type="button" className="button-secondary" disabled={page === 1} onClick={() => { setSelected(null); setPage((value) => value - 1); setState("loading"); }}>Anterior</button><span>Página {page}</span><button type="button" className="button-secondary" disabled={!hasMore} onClick={() => { setSelected(null); setPage((value) => value + 1); setState("loading"); }}>Siguiente</button></nav>
        {selected && <div className="mt-5 rounded-xl bg-sky-50 p-4"><p>Vincular <strong>{selected.name} (ID {selected.id})</strong> a <strong>{block.subject.name} → {block.name}</strong>.</p><button type="button" disabled={submitting} className="button-primary mt-3" onClick={confirm}>{submitting ? "Vinculando…" : "Confirmar vinculación"}</button></div>}
      </>}
      {error && <p role="alert" className="notice-error mt-4">{error}</p>}
    </div>}
  </section>;
}
