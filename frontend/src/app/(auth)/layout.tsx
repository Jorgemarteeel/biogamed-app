import Brand from "@/components/Brand";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-background font-sans text-slate-900 lg:grid lg:grid-cols-2">
      <aside className="hidden flex-col justify-between bg-blue-950 p-12 text-white lg:flex xl:p-16">
        <Brand />
        <div className="max-w-lg py-8">
          <p className="text-xs font-bold uppercase tracking-widest text-orange-300">Tu espacio de aprendizaje</p>
          <h2 className="mt-6 text-4xl font-black leading-tight tracking-tight xl:text-5xl">Cada pregunta es una oportunidad para comprender mejor.</h2>
          <p className="mt-6 text-lg leading-8 text-sky-100">Practica los contenidos de tu asignatura a tu ritmo con Trivial y Pasapalabra.</p>
          <p className="mt-6 border-t border-white/15 pt-5 text-sm leading-7 text-sky-100">Elige qué practicar.<br />Prepara tu juego.<br />Revisa tus resultados.</p>
        </div>
        <p className="text-xs leading-6 text-sky-200">Proyecto de Innovación Educativa<br />ULPGC · PIE 2026-06</p>
      </aside>
      <header className="site-header px-5 py-5 sm:px-10 lg:hidden"><Brand /></header>
      <main className="flex flex-1 flex-col px-5 py-8 sm:px-10 lg:min-h-screen lg:px-12">
        <div className="my-auto w-full max-w-md self-center py-6">{children}</div>
        <p className="mt-8 text-center text-xs text-slate-500">BioGaMed · Aprendizaje en Ciencias de la Salud</p>
      </main>
    </div>
  );
}
