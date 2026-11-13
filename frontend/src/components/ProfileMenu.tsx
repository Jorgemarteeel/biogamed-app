"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getCurrentUser } from "@/services/api";
import { canManageSubjects } from "@/lib/subjects";
import type { UserResponse } from "@/services/api";

export default function ProfileMenu({ name, role }: { name?: string | null; role?: UserResponse["role"] }) {
  const [sessionName, setSessionName] = useState<string | null>(null);
  const [sessionRole, setSessionRole] = useState<UserResponse["role"] | null>(null);
  useEffect(() => {
    let active = true;
    const refresh=()=>{void getCurrentUser().then(user=>{if(active){setSessionName(user.name);setSessionRole(user.role);}}).catch(()=>{});};
    refresh();window.addEventListener('focus',refresh);window.addEventListener('biogamed:role-refresh',refresh);
    return ()=>{active=false;window.removeEventListener('focus',refresh);window.removeEventListener('biogamed:role-refresh',refresh);};
  }, [name, role]);
  const label = (sessionName ?? name)?.trim() || "Mi cuenta";
  const canManage = canManageSubjects(sessionRole ?? role ?? "student");
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    void getCurrentUser().then(user=>{setSessionName(user.name);setSessionRole(user.role);}).catch(()=>{});
    function closeOutside(event: PointerEvent) {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    }
    function closeEscape(event: KeyboardEvent) {
      if (event.key === "Escape") { setOpen(false); button.current?.focus(); }
    }
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeEscape);
    return () => { document.removeEventListener("pointerdown", closeOutside); document.removeEventListener("keydown", closeEscape); };
  }, [open]);
  return <div ref={root} className="min-w-0 max-w-full flex-1 sm:relative sm:flex-none">
    <button ref={button} type="button" aria-expanded={open} aria-controls="profile-navigation" onClick={() => setOpen((value) => !value)} className="inline-flex min-h-11 w-full min-w-0 items-center gap-2 rounded-xl border border-white/40 px-3 text-sm font-bold text-white hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">
      <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 shrink-0 fill-none stroke-current stroke-2"><circle cx="12" cy="8" r="3"/><path d="M5 20c0-4 2.5-6 7-6s7 2 7 6"/></svg>
      <span className="min-w-0 max-w-28 flex-1 truncate sm:max-w-48" aria-hidden="true">{label}</span><span className="sr-only">{label}</span><span className="shrink-0" aria-hidden="true">⌄</span>
    </button>
    {open && <nav id="profile-navigation" aria-label="Navegación personal" className="profile-navigation absolute right-5 top-full z-50 mt-2 w-56 max-w-[calc(100vw-2.5rem)] rounded-xl sm:right-0 border border-slate-200 bg-white p-2 text-blue-950 shadow-xl">
      <Link href="/cuenta" onClick={() => setOpen(false)} className="block rounded-lg px-3 py-3 hover:bg-sky-50 focus-visible:outline-2 focus-visible:outline-sky-700">Mi cuenta</Link>
      <Link href="/historial" onClick={() => setOpen(false)} className="block rounded-lg px-3 py-3 hover:bg-sky-50 focus-visible:outline-2 focus-visible:outline-sky-700">Mi historial</Link>
      <Link href="/progreso" onClick={() => setOpen(false)} className="block rounded-lg px-3 py-3 hover:bg-sky-50 focus-visible:outline-2 focus-visible:outline-sky-700">Mi progreso</Link>
      {(sessionRole ?? role)==='admin'&&<Link href="/administracion/usuarios" onClick={()=>setOpen(false)} className="block rounded-lg px-3 py-3 font-semibold hover:bg-sky-50 focus-visible:outline-2 focus-visible:outline-sky-700">Administración de usuarios</Link>}
      {canManage && <div className="mt-2 border-t border-slate-200 pt-2"><Link href="/gestion/asignaturas" onClick={() => setOpen(false)} className="block rounded-lg px-3 py-3 font-semibold hover:bg-sky-50 focus-visible:outline-2 focus-visible:outline-sky-700">Gestión de contenidos</Link><Link href="/seguimiento" onClick={() => setOpen(false)} className="block rounded-lg px-3 py-3 font-semibold hover:bg-sky-50">Participación y resultados</Link></div>}
    </nav>}
  </div>;
}
