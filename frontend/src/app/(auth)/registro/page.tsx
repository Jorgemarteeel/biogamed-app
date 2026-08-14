"use client";

import Link from "next/link";

const inputClassName =
  "block w-full rounded-xl border border-slate-300 bg-white py-3.5 pl-11 pr-4 text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 hover:border-slate-400 focus:border-sky-700 focus:ring-4 focus:ring-sky-800/10";

export default function RegistroPage() {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    console.log("Intentando registrar...");
  };

  return (
    <div>
      <div className="mb-7">
        <p className="text-sm font-extrabold uppercase tracking-[0.16em] text-orange-600">Empieza a aprender</p>
        <h2 className="mt-3 text-4xl font-black tracking-[-0.03em] text-blue-950">Crea tu cuenta</h2>
        <p className="mt-3 leading-7 text-slate-600">Configura tu perfil y comienza tu primera sesión de estudio.</p>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label htmlFor="name" className="mb-2 block text-sm font-bold text-slate-700">Nombre y apellidos</label>
          <div className="relative">
            <svg className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15.75 7.5a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.5 20.1a7.5 7.5 0 0 1 15 0 17.9 17.9 0 0 1-15 0Z" /></svg>
            <input id="name" name="name" type="text" autoComplete="name" required className={inputClassName} placeholder="Ej. María García" />
          </div>
        </div>

        <div>
          <label htmlFor="email" className="mb-2 block text-sm font-bold text-slate-700">Correo electrónico</label>
          <div className="relative">
            <svg className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 8l7.89 5.26a2 2 0 0 0 2.22 0L21 8m-16 11h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2Z" /></svg>
            <input id="email" name="email" type="email" autoComplete="email" required className={inputClassName} placeholder="alumno@correo.ulpgc.es" />
          </div>
        </div>

        <div>
          <label htmlFor="password" className="mb-2 block text-sm font-bold text-slate-700">Contraseña</label>
          <div className="relative">
            <svg className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M6 10V8a6 6 0 0 1 12 0v2m-13 0h14a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1Z" /></svg>
            <input id="password" name="password" type="password" autoComplete="new-password" minLength={8} required className={inputClassName} placeholder="Mínimo 8 caracteres" />
          </div>
          <p className="mt-2 text-xs text-slate-500">Usa al menos 8 caracteres para proteger tu cuenta.</p>
        </div>

        <label className="flex cursor-pointer items-start gap-3 pt-1 text-xs leading-5 text-slate-600">
          <input type="checkbox" name="terms" required className="mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300 accent-sky-800" />
          <span>Acepto las condiciones de uso y el tratamiento académico de mis datos de progreso.</span>
        </label>

        <button type="submit" className="group flex w-full items-center justify-center gap-2 rounded-xl bg-orange-500 px-5 py-3.5 font-extrabold text-white shadow-lg shadow-orange-500/20 transition-all hover:-translate-y-0.5 hover:bg-orange-600 hover:shadow-xl focus:outline-none focus:ring-4 focus:ring-orange-500/20">
          Crear mi cuenta
          <svg className="h-5 w-5 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m13 7 5 5m0 0-5 5m5-5H6" /></svg>
        </button>
      </form>

      <div className="mt-7 border-t border-slate-200 pt-6 text-center">
        <p className="text-sm text-slate-600">
          ¿Ya tienes una cuenta?{" "}
          <Link href="/login" className="font-extrabold text-sky-800 transition-colors hover:text-orange-600">Inicia sesión</Link>
        </p>
      </div>
    </div>
  );
}
