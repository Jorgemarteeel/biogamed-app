import Link from "next/link";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="grid min-h-screen bg-slate-50 lg:grid-cols-[minmax(0,1.05fr)_minmax(520px,0.95fr)]">
      <section className="relative hidden min-h-screen flex-col justify-between bg-blue-950 p-10 text-white lg:flex xl:p-14">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_15%,rgba(14,116,144,0.5),transparent_32%),radial-gradient(circle_at_85%_85%,rgba(249,115,22,0.2),transparent_30%)]" />
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[size:40px_40px]" />

        <Link href="/" className="relative z-10 flex w-fit items-center gap-3" aria-label="BioGaMed, volver al inicio">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-500 shadow-lg shadow-black/20">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v18M3 12h18M7 7l10 10m0-10L7 17" />
            </svg>
          </span>
          <span className="text-2xl font-black tracking-tight">BioGaMed</span>
        </Link>

        <div className="relative z-10 max-w-xl py-14">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs font-extrabold uppercase tracking-[0.16em] text-sky-100 backdrop-blur-sm">
            <span className="h-2 w-2 rounded-full bg-orange-400" />
            Aprendizaje gamificado
          </div>
          <h1 className="mt-7 text-5xl font-black leading-[1.05] tracking-[-0.04em] xl:text-6xl">
            Convierte cada reto en conocimiento.
          </h1>
          <p className="mt-6 max-w-lg text-lg leading-8 text-sky-100">
            Practica Fisiología e Inmunología, refuerza tus errores y visualiza tu evolución desde un único espacio de aprendizaje.
          </p>

          <div className="mt-10 grid max-w-lg grid-cols-3 gap-3">
            <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
              <p className="text-2xl font-black text-orange-400">3</p>
              <p className="mt-1 text-xs font-bold leading-5 text-sky-100">Modos de estudio</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
              <p className="text-2xl font-black text-orange-400">100%</p>
              <p className="mt-1 text-xs font-bold leading-5 text-sky-100">Progreso medible</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur-sm">
              <svg className="h-7 w-7 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6-2a9 9 0 11-18 0 9 9 0 0118 0Z" /></svg>
              <p className="mt-1 text-xs font-bold leading-5 text-sky-100">Contenido académico</p>
            </div>
          </div>
        </div>

        <div className="relative z-10 flex items-center gap-3 border-t border-white/10 pt-7 text-sm text-sky-100">
          <svg className="h-5 w-5 shrink-0 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 21h18M5 21V8l7-5 7 5v13M9 21v-7h6v7" /></svg>
          Proyecto de Innovación Educativa ULPGC · PIE 2026-06
        </div>
      </section>

      <section className="relative flex min-h-screen items-center justify-center px-5 py-10 sm:px-10 lg:px-14 xl:px-20">
        <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-sky-800 via-blue-900 to-orange-500 lg:hidden" />
        <div className="w-full max-w-md">
          <Link href="/" className="mb-10 flex w-fit items-center gap-3 lg:hidden" aria-label="BioGaMed, volver al inicio">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-800 text-white shadow-sm">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v18M3 12h18M7 7l10 10m0-10L7 17" /></svg>
            </span>
            <span className="text-xl font-black tracking-tight text-blue-950">BioGaMed</span>
          </Link>
          {children}
          <p className="mt-10 text-center text-xs leading-5 text-slate-500">
            Plataforma académica del Proyecto PIE 2026-06 · ULPGC
          </p>
        </div>
      </section>
    </main>
  );
}
