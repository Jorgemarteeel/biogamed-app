import Login from "@/components/Login";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ session?: string | string[]; password?: string | string[]; activated?: string | string[] }>;
}) {
  const params = await searchParams;
  return (
    <div>
      <div className="mb-8">
        <p className="text-xs font-bold uppercase tracking-widest text-orange-700">Acceso a la plataforma</p>
        <h1 className="mt-3 text-3xl font-black tracking-tight text-blue-950 sm:text-4xl">Bienvenido de nuevo</h1>
        <p className="mt-3 leading-7 text-slate-600">
          Continúa tu progreso y retoma tu próxima sesión de estudio.
        </p>
      </div>

      <Login passwordChanged={params.password === "changed"} sessionExpired={params.session === "expired"} activated={params.activated === "1"} />
    </div>
  );
}
