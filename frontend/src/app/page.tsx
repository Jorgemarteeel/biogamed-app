import Link from "next/link";

const CheckIcon = ({ className = "h-5 w-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m5 13 4 4L19 7" />
  </svg>
);

const ArrowIcon = ({ className = "h-5 w-5" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0-5 5m5-5H6" />
  </svg>
);

const features = [
  {
    number: "01",
    title: "Modo Trivial",
    description:
      "Responde preguntas de opción múltiple y consolida los conceptos esenciales de cada bloque temático.",
    detail: "Feedback inmediato",
    icon: (
      <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8.228 9a4 4 0 0 1 7.545 1.87c0 2.5-3.773 2.13-3.773 4.13m0 3h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
      </svg>
    ),
  },
  {
    number: "02",
    title: "El Pasapalabra",
    description:
      "Domina el vocabulario científico mediante definiciones y retos terminológicos organizados por materia.",
    detail: "Memoria activa",
    icon: (
      <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 6h16M4 12h10M4 18h7M17 14l3 4m0-4-3 4" />
      </svg>
    ),
  },
  {
    number: "03",
    title: "Repaso Inteligente",
    description:
      "El sistema identifica tus errores y los recupera en el momento adecuado para reforzar el aprendizaje.",
    detail: "Práctica personalizada",
    icon: (
      <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 12a8 8 0 0 1 14.93-4M20 4v5h-5m5 3a8 8 0 0 1-14.93 4M4 20v-5h5" />
      </svg>
    ),
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-white font-sans text-slate-900 selection:bg-orange-200 selection:text-blue-950">
      <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex h-18 max-w-7xl items-center justify-between px-5 sm:px-8 lg:px-12">
          <Link href="/" className="group flex items-center gap-3" aria-label="BioGaMed, página de inicio">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-800 text-white shadow-sm transition-transform group-hover:scale-105">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v18M3 12h18M7 7l10 10m0-10L7 17" />
              </svg>
            </span>
            <span className="text-xl font-black tracking-tight text-blue-950">BioGaMed</span>
          </Link>

          <nav className="flex items-center gap-1 sm:gap-3" aria-label="Navegación principal">
            <Link href="/login" className="rounded-lg px-3 py-2 text-sm font-bold text-slate-600 transition-colors hover:bg-slate-100 hover:text-sky-800 sm:px-4 sm:text-base">
              Iniciar sesión
            </Link>
            <Link href="/registro" className="rounded-lg bg-blue-900 px-4 py-2.5 text-sm font-bold text-white shadow-sm transition-all hover:-translate-y-0.5 hover:bg-sky-800 hover:shadow-md sm:px-5 sm:text-base">
              Registrarse
            </Link>
          </nav>
        </div>
      </header>

      <main>
        <section className="relative isolate border-b border-slate-200 bg-slate-50">
          <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_20%_15%,rgba(14,116,144,0.12),transparent_32%),radial-gradient(circle_at_85%_80%,rgba(249,115,22,0.10),transparent_28%)]" />
          <div className="pointer-events-none absolute inset-0 -z-10 bg-[linear-gradient(to_right,#cbd5e130_1px,transparent_1px),linear-gradient(to_bottom,#cbd5e130_1px,transparent_1px)] bg-[size:32px_32px]" />

          <div className="mx-auto grid max-w-7xl items-center gap-14 px-5 py-16 sm:px-8 sm:py-20 lg:grid-cols-[1.02fr_0.98fr] lg:px-12 lg:py-24 xl:gap-20">
            <div className="text-center lg:text-left">
              <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-sky-200 bg-white px-4 py-2 text-xs font-extrabold uppercase tracking-[0.14em] text-sky-800 shadow-sm sm:text-sm">
                <span className="h-2 w-2 rounded-full bg-orange-500" />
                Innovación educativa ULPGC
              </div>

              <h1 className="text-balance text-5xl font-black leading-[1.03] tracking-[-0.04em] text-blue-950 sm:text-6xl lg:text-7xl">
                Aprende ciencias de la salud
                <span className="mt-2 block text-sky-800">jugando en serio.</span>
              </h1>

              <p className="mx-auto mt-7 max-w-2xl text-lg leading-8 text-slate-600 lg:mx-0 lg:max-w-xl">
                Convierte Fisiología e Inmunología en sesiones de estudio activas, medibles y personalizadas. Practica, detecta tus puntos débiles y llega mejor preparado al examen.
              </p>

              <div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row lg:justify-start">
                <Link href="/registro" className="group inline-flex items-center justify-center gap-2 rounded-xl bg-orange-500 px-7 py-4 text-base font-extrabold text-white shadow-lg shadow-orange-500/20 transition-all hover:-translate-y-1 hover:bg-orange-600 hover:shadow-xl">
                  Comenzar gratis
                  <ArrowIcon className="h-5 w-5 transition-transform group-hover:translate-x-1" />
                </Link>
                <Link href="#caracteristicas" className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-7 py-4 text-base font-extrabold text-blue-950 shadow-sm transition-all hover:-translate-y-0.5 hover:border-sky-300 hover:bg-sky-50">
                  Explorar la plataforma
                </Link>
              </div>

              <div className="mt-8 flex flex-wrap justify-center gap-x-6 gap-y-3 text-sm font-semibold text-slate-600 lg:justify-start">
                <span className="inline-flex items-center gap-2"><CheckIcon className="h-4 w-4 text-orange-500" />Acceso sencillo</span>
                <span className="inline-flex items-center gap-2"><CheckIcon className="h-4 w-4 text-orange-500" />Progreso medible</span>
                <span className="inline-flex items-center gap-2"><CheckIcon className="h-4 w-4 text-orange-500" />Contenido universitario</span>
              </div>
            </div>

            <div className="w-full min-w-0">
              <div className="mx-auto w-full max-w-xl rounded-[2rem] border border-slate-200 bg-white p-3 shadow-[0_30px_80px_-32px_rgba(15,23,42,0.38)] sm:p-4">
                <div className="rounded-[1.5rem] bg-blue-950 p-5 text-white sm:p-7">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-[0.16em] text-sky-300">Panel del estudiante</p>
                      <h2 className="mt-1 text-xl font-extrabold">Tu progreso, de un vistazo</h2>
                    </div>
                    <div className="flex items-center gap-2 rounded-full bg-white/10 px-3 py-2 text-xs font-bold text-sky-100 ring-1 ring-white/10">
                      <span className="h-2 w-2 rounded-full bg-orange-400" />
                      Semana activa
                    </div>
                  </div>

                  <div className="mt-7 rounded-2xl bg-white p-5 text-slate-900 shadow-lg sm:p-6">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-bold text-slate-500">Objetivo semanal</p>
                        <p className="mt-1 text-3xl font-black tracking-tight text-blue-950">8 de 10</p>
                        <p className="mt-1 text-sm text-slate-500">sesiones completadas</p>
                      </div>
                      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-orange-50 text-lg font-black text-orange-600 ring-1 ring-orange-100">80%</div>
                    </div>
                    <div className="mt-5 h-2.5 rounded-full bg-slate-100" role="progressbar" aria-label="Objetivo semanal completado" aria-valuenow={80} aria-valuemin={0} aria-valuemax={100}>
                      <div className="h-full w-4/5 rounded-full bg-gradient-to-r from-orange-500 to-amber-400" />
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                    <div className="rounded-2xl bg-white/10 p-4 ring-1 ring-white/10">
                      <svg className="mb-3 h-6 w-6 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m9 12 2 2 4-4m6 2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                      <p className="text-2xl font-black">84%</p>
                      <p className="mt-1 text-xs font-semibold text-slate-300">Precisión media</p>
                    </div>
                    <div className="rounded-2xl bg-white/10 p-4 ring-1 ring-white/10">
                      <svg className="mb-3 h-6 w-6 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 2m6-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                      <p className="text-2xl font-black">42 min</p>
                      <p className="mt-1 text-xs font-semibold text-slate-300">Estudio efectivo</p>
                    </div>
                    <div className="col-span-2 rounded-2xl bg-orange-500 p-4 text-white shadow-lg shadow-orange-950/20 sm:col-span-1">
                      <svg className="mb-3 h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7Z" /></svg>
                      <p className="text-2xl font-black">5 días</p>
                      <p className="mt-1 text-xs font-bold text-orange-50">Racha de estudio</p>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center gap-4 rounded-2xl border border-white/10 bg-white/5 p-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-sky-800 text-sky-100">
                      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6l4 2m5-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-bold uppercase tracking-wider text-sky-300">Siguiente repaso</p>
                      <p className="mt-1 truncate text-sm font-bold">Sistema inmunitario · 10 preguntas</p>
                    </div>
                    <ArrowIcon className="h-5 w-5 shrink-0 text-orange-400" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="caracteristicas" className="scroll-mt-24 bg-white px-5 py-20 sm:px-8 sm:py-24 lg:px-12">
          <div className="mx-auto max-w-7xl">
            <div className="mx-auto max-w-3xl text-center">
              <p className="text-sm font-extrabold uppercase tracking-[0.18em] text-orange-600">Aprender haciendo</p>
              <h2 className="mt-4 text-4xl font-black tracking-tight text-blue-950 sm:text-5xl">Tres formas de convertir el estudio en progreso</h2>
              <p className="mt-5 text-lg leading-8 text-slate-600">Mecánicas diseñadas para practicar, recordar y detectar dónde necesitas reforzar tus conocimientos.</p>
            </div>

            <div className="mt-14 grid gap-6 md:grid-cols-3">
              {features.map((feature) => (
                <article key={feature.title} className="group relative flex h-full flex-col rounded-3xl border border-slate-200 bg-slate-50 p-7 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-sky-200 hover:bg-white hover:shadow-lg sm:p-8">
                  <span className="absolute right-7 top-7 text-sm font-black tracking-widest text-slate-300">{feature.number}</span>
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-orange-50 text-orange-600 ring-1 ring-orange-100 transition-colors group-hover:bg-orange-500 group-hover:text-white">
                    {feature.icon}
                  </div>
                  <h3 className="mt-7 text-2xl font-black text-blue-950">{feature.title}</h3>
                  <p className="mt-3 flex-1 leading-7 text-slate-600">{feature.description}</p>
                  <div className="mt-7 flex items-center gap-2 border-t border-slate-200 pt-5 text-sm font-extrabold text-sky-800">
                    <CheckIcon className="h-4 w-4 text-orange-500" />
                    {feature.detail}
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="bg-blue-950 px-5 py-20 text-white sm:px-8 sm:py-24 lg:px-12">
          <div className="mx-auto grid max-w-6xl items-center gap-10 lg:grid-cols-[0.7fr_1.3fr] lg:gap-16">
            <div>
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-orange-500 text-white shadow-lg shadow-black/20">
                <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 21h18M5 21V8l7-5 7 5v13M9 21v-7h6v7M9 9h.01M15 9h.01" /></svg>
              </div>
              <p className="mt-6 text-sm font-extrabold uppercase tracking-[0.18em] text-orange-400">Marco institucional</p>
              <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">Tecnología con propósito educativo</h2>
            </div>

            <div className="rounded-3xl border border-white/15 bg-white/10 p-7 shadow-lg backdrop-blur-sm sm:p-9">
              <p className="text-xl font-bold leading-8 text-white sm:text-2xl">
                BioGaMed forma parte del Proyecto de Innovación Educativa
                <span className="text-orange-400"> ULPGC / PIE 2026-06</span>.
              </p>
              <p className="mt-5 leading-7 text-sky-100">
                Una iniciativa orientada a integrar la gamificación y el análisis del aprendizaje en la docencia universitaria, mejorando la motivación, la autonomía y el rendimiento académico del alumnado de Ciencias de la Salud.
              </p>
              <div className="mt-7 flex items-center gap-3 border-t border-white/15 pt-6 text-sm font-bold text-sky-100">
                <span className="h-2.5 w-2.5 rounded-full bg-orange-400" />
                Universidad de Las Palmas de Gran Canaria
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-800 bg-slate-950 px-5 py-8 text-slate-400 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-5 text-center text-sm sm:flex-row sm:text-left">
          <div className="flex items-center gap-2 font-black text-white">
            <span className="h-2.5 w-2.5 rounded-sm bg-orange-500" />
            BioGaMed
          </div>
          <p>© {new Date().getFullYear()} BioGaMed · Proyecto PIE 2026-06 ULPGC</p>
          <p>Facultad de Ciencias de la Salud</p>
        </div>
      </footer>
    </div>
  );
}
