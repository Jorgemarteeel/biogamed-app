"use client";

import { useRef, useState, type ReactNode } from "react";

export default function CreateContentPanel({ id, label, busy = false, children }: { id: string; label: string; busy?: boolean; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  function toggle() {
    if (open) { setOpen(false); requestAnimationFrame(() => button.current?.focus()); }
    else { setOpen(true); requestAnimationFrame(() => panel.current?.querySelector<HTMLElement>("input, textarea")?.focus()); }
  }
  return <section aria-labelledby={`${id}-heading`} className="mt-9 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
    <h2 id={`${id}-heading`} className="text-xl font-bold text-blue-950">{label}</h2>
    <button ref={button} type="button" aria-expanded={open} aria-controls={`${id}-panel`} disabled={busy} onClick={toggle} className="button-secondary mt-4">{open ? "Cerrar formulario" : label}</button>
    {open && <div id={`${id}-panel`} ref={panel} className="mt-5">{children}</div>}
  </section>;
}
