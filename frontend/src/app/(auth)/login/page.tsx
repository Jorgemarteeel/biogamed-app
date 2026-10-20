"use client";

import Link from "next/link";
import Login from "@/components/Login";

export default function LoginPage() {
  return (
    <div>
      <div className="mb-8">
        <p className="text-sm font-extrabold uppercase tracking-[0.16em] text-orange-600">Acceso a la plataforma</p>
        <h2 className="mt-3 text-4xl font-black tracking-[-0.03em] text-blue-950">Bienvenido de nuevo</h2>
        <p className="mt-3 leading-7 text-slate-600">
          Continúa tu progreso y retoma tu próxima sesión de estudio.
        </p>
      </div>

      <Login />

      <div className="mt-8 border-t border-slate-200 pt-7 text-center">
        <p className="text-sm text-slate-600">
          ¿Todavía no tienes cuenta?{" "}
          <Link href="/registro" className="font-extrabold text-sky-800 transition-colors hover:text-orange-600">Crea una gratis</Link>
        </p>
      </div>
    </div>
  );
}
