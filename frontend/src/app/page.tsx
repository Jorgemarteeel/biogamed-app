import Link from "next/link";
import Brand from "@/components/Brand";
import GameIllustration from "@/components/GameIllustration";

const games = [
  { mode: "TRIVIAL" as const, name: "Trivial", description: "Practica de forma individual: lee cada pregunta y elige una respuesta entre varias opciones." },
  { mode: "PASAPALABRA" as const, name: "Pasapalabra", description: "Dos jugadores resuelven pistas por turnos, cada uno con su rosco numerado. Juega en un dispositivo con un invitado o en línea con otra cuenta." },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      <a href="#contenido" className="sr-only bg-white p-3 focus:not-sr-only">Saltar al contenido</a>
      <header className="site-header">
        <nav aria-label="Principal" className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-5 px-5 py-5 sm:px-8 lg:px-12">
          <Brand />
          <div className="flex w-full items-center justify-between gap-3 text-sm font-bold sm:w-auto">
            <Link href="/login" className="rounded-xl px-3 py-3 text-white transition-colors hover:bg-white/10">Iniciar sesión</Link>
            <Link href="/registro" className="button-primary">Crear cuenta</Link>
          </div>
        </nav>
      </header>
      <main id="contenido" className="bg-background">
        <section className="mx-auto grid max-w-7xl items-center gap-10 overflow-hidden px-5 py-12 sm:px-8 lg:px-12 sm:py-16 lg:grid-cols-[1.1fr_0.9fr] lg:gap-16">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-800">Ciencias de la Salud · ULPGC</p>
            <h1 className="mt-6 text-4xl font-black leading-[1.08] tracking-tight text-blue-950 sm:text-6xl">Comprender es el principio.<br /><span className="text-orange-700">Practicar es avanzar.</span></h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">Un espacio para repasar los contenidos de tus asignaturas con preguntas y retos de vocabulario científico.</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/practicar" className="button-primary">Elegir qué practicar →</Link>
              <Link href="#modalidades" className="button-secondary">Conocer los juegos</Link>
            </div>
            <p className="mt-5 text-sm text-slate-600">Para jugar, <Link href="/login" className="text-link">inicia sesión</Link> o <Link href="/registro" className="text-link">crea tu cuenta</Link>.</p>
          </div>
          <div className="relative isolate rounded-2xl bg-blue-950 p-8 text-white shadow-lg shadow-blue-950/10 before:pointer-events-none before:absolute before:-inset-8 before:-z-10 before:rounded-full before:bg-[radial-gradient(ellipse,rgba(14,116,144,0.18),transparent_70%)] sm:p-10">
            <p className="text-xs font-bold uppercase tracking-widest text-orange-300">Aprender haciendo</p>
            <p className="mt-7 text-3xl font-bold leading-tight">Una pregunta.<br />Una idea más clara.<br />Un paso adelante.</p>
            <div className="my-8 h-px bg-white/15" />
            <p className="text-sm leading-7 text-sky-100">Reconocer una respuesta y recordar una palabra son dos formas de poner en práctica lo que estudias.</p>
            <div className="mt-7 flex flex-wrap gap-2 text-sm font-semibold"><span className="rounded-full bg-white/10 px-4 py-2">Fisiología</span><span className="rounded-full bg-white/10 px-4 py-2">Inmunología</span></div>
          </div>
        </section>
        <section id="modalidades" aria-labelledby="games-title" className="scroll-mt-24 border-y border-slate-200 bg-white px-5 py-12 sm:px-8 lg:px-12">
          <div className="mx-auto max-w-7xl">
            <h2 id="games-title" className="text-3xl font-black text-blue-950">Dos juegos para practicar</h2>
            <p className="mt-4 max-w-2xl leading-7 text-slate-600">Elige los contenidos de tu asignatura y practica con Trivial o Pasapalabra. Consulta después tus resultados</p>
            <div className="mt-8 grid gap-6 md:grid-cols-2">
              {games.map((game) => <article key={game.name} className={`flex min-w-0 flex-col rounded-2xl border p-5 sm:p-6 ${game.name === "Trivial" ? "border-sky-200 bg-sky-50/40" : "border-teal-200 bg-teal-50/40"}`}>
                <div className="mx-auto w-full max-w-sm"><GameIllustration mode={game.mode} /></div>
                <h3 className="mt-4 text-2xl font-black text-blue-950">{game.name}</h3>
                <p className="mt-3 leading-7 text-slate-600">{game.description}</p>
                <div className="mt-auto pt-5">
                  <div className="rounded-xl border border-slate-200 bg-white p-4">
                    <p className={`text-xs font-bold uppercase tracking-wider ${game.name === "Trivial" ? "text-sky-800" : "text-teal-800"}`}>Ejemplo ilustrativo · No es una partida</p>
                    {game.mode === "TRIVIAL" ? <>
                      <p className="mt-2 font-semibold leading-6 text-blue-950">¿Qué células producen anticuerpos?</p>
                      <ul aria-label="Opciones del ejemplo de Trivial" className="mt-3 flex flex-wrap gap-2 text-sm text-slate-700">
                        {["Plasmocitos", "Eritrocitos", "Plaquetas"].map(option => <li key={option} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1">{option}</li>)}
                      </ul>
                    </> : <div className="mt-3 flex items-start gap-3">
                      <span aria-hidden="true" className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-blue-950 text-lg font-bold text-white">7</span>
                      <div><p className="text-xs font-bold text-teal-800">Casilla 7</p><p className="mt-1 font-semibold leading-6 text-blue-950">Pista: Unidad básica de los seres vivos.</p></div>
                    </div>}
                  </div>
                </div>
              </article>)}
            </div>
          </div>
        </section>
        <section className="bg-sky-50/70" aria-labelledby="steps-title"><div className="mx-auto max-w-7xl px-5 py-12 sm:px-8 lg:px-12">
          <h2 id="steps-title" className="text-3xl font-black text-blue-950">Un recorrido sencillo.</h2>
          <ol className="mt-8 grid gap-8 md:grid-cols-3">{[
            ["01", "Elige qué practicar", "Selecciona tu asignatura, bloque y categoría."],
            ["02", "Prepara tu partida", "Elige juego y dificultad; en Pasapalabra, modo local o en línea."],
            ["03", "Consulta tus resultados", "Revisa puntuación, respuestas y evolución de partidas comparables."],
          ].map(([number, title, text]) => <li key={number}><span className="flex h-12 w-12 items-center justify-center rounded-full bg-white text-sm font-black text-sky-800 ring-1 ring-sky-200">{number}</span><h3 className="mt-3 text-lg font-bold text-blue-950">{title}</h3><p className="mt-2 leading-7 text-slate-600">{text}</p></li>)}</ol></div>
        </section>
        <section className="bg-blue-950 px-5 py-14 text-white sm:px-8 sm:py-16 lg:px-12">
          <div className="mx-auto grid max-w-6xl items-center gap-10 lg:grid-cols-[0.7fr_1.3fr] lg:gap-16">
            <div>
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-orange-500 text-white shadow-lg shadow-black/20">
                <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 21h18M5 21V8l7-5 7 5v13M9 21v-7h6v7M9 9h.01M15 9h.01" /></svg>
              </div>
              <p className="mt-6 text-sm font-extrabold uppercase tracking-[0.18em] text-orange-400">Marco institucional</p>
              <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">Tecnología con propósito educativo</h2>
            </div>

            <div className="rounded-2xl border border-white/15 bg-white/10 p-7 sm:p-9">
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
          <Brand />
          <p>© {new Date().getFullYear()} BioGaMed · Proyecto PIE 2026-06 ULPGC</p>
          <p>Facultad de Ciencias de la Salud</p>
        </div>
      </footer>
    </div>
  );
}
