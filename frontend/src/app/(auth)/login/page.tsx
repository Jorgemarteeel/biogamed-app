"use client";

import Link from "next/link";

const inputClassName =
  "block w-full rounded-xl border border-slate-300 bg-white py-3.5 pl-11 pr-4 text-slate-900 shadow-sm outline-none transition placeholder:text-slate-400 hover:border-slate-400 focus:border-sky-700 focus:ring-4 focus:ring-sky-800/10";

export default function LoginPage() {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    console.log("Intentando iniciar sesión...");
  };

  return (
    <div>
      <div className="mb-8">
        <p className="text-sm font-extrabold uppercase tracking-[0.16em] text-orange-600">Acceso a la plataforma</p>
        <h2 className="mt-3 text-4xl font-black tracking-[-0.03em] text-blue-950">Bienvenido de nuevo</h2>
        <p className="mt-3 leading-7 text-slate-600">
          Continúa tu progreso y retoma tu próxima sesión de estudio.
        </p>
      </div>

      <form className="space-y-5" onSubmit={handleSubmit}>
        <div>
          <label htmlFor="email" className="mb-2 block text-sm font-bold text-slate-700">Correo electrónico</label>
          <div className="relative">
            <svg className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 8l7.89 5.26a2 2 0 0 0 2.22 0L21 8m-16 11h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2Z" /></svg>
            <input id="email" name="email" type="email" autoComplete="email" required className={inputClassName} placeholder="alumno@correo.ulpgc.es" />
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between gap-4">
            <label htmlFor="password" className="block text-sm font-bold text-slate-700">Contraseña</label>
            <span className="text-xs font-semibold text-slate-400">Mínimo 8 caracteres</span>
          </div>
          <div className="relative">
            <svg className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M6 10V8a6 6 0 0 1 12 0v2m-13 0h14a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1Z" /></svg>
            <input id="password" name="password" type="password" autoComplete="current-password" minLength={8} required className={inputClassName} placeholder="Introduce tu contraseña" />
          </div>
        </div>

        <label className="flex w-fit cursor-pointer items-center gap-3 text-sm font-semibold text-slate-600">
          <input type="checkbox" name="remember" className="h-4 w-4 rounded border-slate-300 accent-sky-800" />
          Mantener la sesión iniciada
        </label>

        <button type="submit" className="group flex w-full items-center justify-center gap-2 rounded-xl bg-orange-500 px-5 py-3.5 font-extrabold text-white shadow-lg shadow-orange-500/20 transition-all hover:-translate-y-0.5 hover:bg-orange-600 hover:shadow-xl focus:outline-none focus:ring-4 focus:ring-orange-500/20">
          Entrar en BioGaMed
          <svg className="h-5 w-5 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m13 7 5 5m0 0-5 5m5-5H6" /></svg>
        </button>
      </form>

      <div className="mt-8 border-t border-slate-200 pt-7 text-center">
        <p className="text-sm text-slate-600">
          ¿Todavía no tienes cuenta?{" "}
          <Link href="/registro" className="font-extrabold text-sky-800 transition-colors hover:text-orange-600">Crea una gratis</Link>
        </p>
      </div>
    </div>
  );
}
