import Link from "next/link";
import Brand from "@/components/Brand";

const games = [
  { name: "Trivial", description: "Practica conceptos eligiendo la opción correcta entre varias respuestas.", example: "¿Qué células producen anticuerpos?" },
  { name: "Pasapalabra", description: "Recupera vocabulario científico con una definición y una letra como pista.", example: "Empieza por L: célula que participa en la defensa del organismo." },
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
        <section className="mx-auto grid max-w-7xl items-center gap-12 overflow-hidden px-5 py-16 sm:px-8 lg:px-12 sm:py-24 lg:grid-cols-[1.1fr_0.9fr] lg:gap-20">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-800">Ciencias de la Salud · ULPGC</p>
            <h1 className="mt-6 text-4xl font-black leading-[1.08] tracking-tight text-blue-950 sm:text-6xl">Comprender es el principio.<br /><span className="text-orange-700">Practicar es avanzar.</span></h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">Un espacio para practicar Fisiología e Inmunología mediante preguntas y retos de vocabulario científico.</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/registro" className="button-primary">Crear mi cuenta →</Link>
              <Link href="#modalidades" className="button-secondary">Conocer los juegos</Link>
            </div>
            <p className="mt-5 text-sm text-slate-600">¿Ya tienes cuenta? <Link href="/login" className="text-link">Entra en tu espacio</Link></p>
          </div>
          <div className="relative isolate rounded-2xl bg-blue-950 p-8 text-white shadow-lg shadow-blue-950/10 before:pointer-events-none before:absolute before:-inset-8 before:-z-10 before:rounded-full before:bg-[radial-gradient(ellipse,rgba(14,116,144,0.18),transparent_70%)] sm:p-10">
            <p className="text-xs font-bold uppercase tracking-widest text-orange-300">Aprender haciendo</p>
            <p className="mt-7 text-3xl font-bold leading-tight">Una pregunta.<br />Una idea más clara.<br />Un paso adelante.</p>
            <div className="my-8 h-px bg-white/15" />
            <p className="text-sm leading-7 text-sky-100">Reconocer una respuesta y recordar una palabra son dos formas de poner en práctica lo que estudias.</p>
            <div className="mt-7 flex flex-wrap gap-2 text-sm font-semibold"><span className="rounded-full bg-white/10 px-4 py-2">Fisiología</span><span className="rounded-full bg-white/10 px-4 py-2">Inmunología</span></div>
          </div>
        </section>
        <section id="modalidades" aria-labelledby="games-title" className="scroll-mt-24 border-y border-slate-200 bg-white px-5 py-16 sm:px-8 lg:px-12">
          <div className="mx-auto max-w-7xl">
            <p className="text-xs font-bold uppercase tracking-widest text-orange-700">Dos formas de practicar</p>
            <h2 id="games-title" className="mt-3 text-3xl font-black text-blue-950">Elige cómo poner a prueba lo que sabes.</h2>
            <p className="mt-4 max-w-2xl leading-7 text-slate-600">Las pantallas de juego están en preparación. Ya puedes crear tu cuenta y explorar el panel de selección.</p>
            <div className="mt-8 grid gap-6 md:grid-cols-2">
              {games.map((game) => <article key={game.name} className={`rounded-2xl border p-6 sm:p-8 ${game.name === "Trivial" ? "border-sky-200 bg-sky-50/40" : "border-teal-200 bg-teal-50/40"}`}>
                <div className="flex items-center justify-between"><span aria-hidden="true" className={`flex h-12 w-12 items-center justify-center rounded-xl text-xl font-black ${game.name === "Trivial" ? "bg-sky-100 text-sky-800" : "bg-teal-100 text-teal-800"}`}>{game.name === "Trivial" ? "✓" : "Aa"}</span><span className="rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-600">En preparación</span></div>
                <h3 className="mt-5 text-2xl font-black text-blue-950">{game.name}</h3>
                <p className="mt-3 leading-7 text-slate-600">{game.description}</p>
                <div className="mt-6 rounded-xl border border-slate-200 bg-white p-5"><p className={`text-xs font-bold uppercase tracking-wider ${game.name === "Trivial" ? "text-sky-800" : "text-teal-800"}`}>Ejemplo ilustrativo</p><p className="mt-3 font-semibold leading-7 text-blue-950">{game.example}</p></div>
              </article>)}
            </div>
          </div>
        </section>
        <section className="bg-sky-50/70" aria-labelledby="steps-title"><div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:px-12">
          <h2 id="steps-title" className="text-3xl font-black text-blue-950">Un recorrido sencillo.</h2>
          <ol className="mt-8 grid gap-8 md:grid-cols-3">{[
            ["01", "Elige el juego", "Decide cómo quieres practicar: opciones de respuesta o vocabulario."],
            ["02", "Selecciona el tema", "Encuentra los contenidos disponibles para la modalidad elegida."],
            ["03", "Aprende del resultado", "El recorrido previsto termina con la puntuación y la corrección de tus respuestas."],
          ].map(([number, title, text]) => <li key={number}><span className="flex h-12 w-12 items-center justify-center rounded-full bg-white text-sm font-black text-sky-800 ring-1 ring-sky-200">{number}</span><h3 className="mt-3 text-lg font-bold text-blue-950">{title}</h3><p className="mt-2 leading-7 text-slate-600">{text}</p></li>)}</ol></div>
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
