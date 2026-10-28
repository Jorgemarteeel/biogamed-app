"use client";

import Link from "next/link";
import { useRef, useState, type FormEvent } from "react";
import { isAxiosError } from "axios";
import { registerUser } from "@/services/api";

const inputClassName = "form-input pl-11";

export default function RegistroPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [isRegistered, setIsRegistered] = useState(false);
  const submitting = useRef(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (submitting.current || isRegistered) return;
    const form = e.currentTarget;
    const data = new FormData(form);
    const name = String(data.get("name") ?? "").trim();
    const email = String(data.get("email") ?? "").trim();
    const password = String(data.get("password") ?? "");
    setError("");
    if (!name) {
      setError("Introduce tu nombre y apellidos.");
      return;
    }
    submitting.current = true;
    setIsLoading(true);
    try {
      await registerUser({ name, email, password });
      form.reset();
      setIsRegistered(true);
    } catch (err: unknown) {
      if (isAxiosError(err)) {
        const status = err.response?.status;
        setError(
          status === 400 || status === 409
            ? "Este correo electrónico ya está registrado. Inicia sesión o utiliza otro correo."
            : status === 422
              ? "Revisa los datos: introduce un correo válido y una contraseña de al menos 8 caracteres."
              : !err.response
                ? "No se pudo conectar con el servidor. Inténtalo de nuevo."
                : "No se pudo crear la cuenta. Inténtalo de nuevo.",
        );
      } else {
        setError("No se pudo crear la cuenta. Inténtalo de nuevo.");
      }
    } finally {
      submitting.current = false;
      setIsLoading(false);
    }
  };

  return (
    <div>
      <div className="mb-8">
        <p className="text-xs font-bold uppercase tracking-widest text-orange-700">Empieza a aprender</p>
        <h1 className="mt-3 text-3xl font-black tracking-tight text-blue-950 sm:text-4xl">Crea tu cuenta</h1>
        <p className="mt-3 leading-7 text-slate-600">Configura tu perfil y comienza tu primera sesión de estudio.</p>
      </div>

      {isRegistered ? (
        <div className="space-y-4">
          <p role="status" className="notice-success">Cuenta creada correctamente. Ya puedes iniciar sesión.</p>
          <Link href="/login" className="button-primary w-full">Ir a iniciar sesión</Link>
        </div>
      ) : (
      <form onSubmit={handleSubmit} aria-busy={isLoading}>
        <fieldset disabled={isLoading} className="space-y-5 disabled:opacity-70">
        <legend className="sr-only">Datos de registro</legend>
        <div>
          <label htmlFor="name" className="form-label">Nombre y apellidos</label>
          <div className="relative">
            <svg className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15.75 7.5a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.5 20.1a7.5 7.5 0 0 1 15 0 17.9 17.9 0 0 1-15 0Z" /></svg>
            <input id="name" name="name" type="text" autoComplete="name" maxLength={255} required className={inputClassName} placeholder="Ej. María García" />
          </div>
        </div>

        <div>
          <label htmlFor="email" className="form-label">Correo electrónico</label>
          <div className="relative">
            <svg className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 8l7.89 5.26a2 2 0 0 0 2.22 0L21 8m-16 11h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2Z" /></svg>
            <input id="email" name="email" type="email" autoComplete="email" required className={inputClassName} placeholder="alumno@correo.ulpgc.es" />
          </div>
        </div>

        <div>
          <label htmlFor="password" className="form-label">Contraseña</label>
          <div className="relative">
            <svg className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M6 10V8a6 6 0 0 1 12 0v2m-13 0h14a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1Z" /></svg>
            <input id="password" name="password" type="password" autoComplete="new-password" minLength={8} maxLength={255} required aria-describedby="password-help" className={inputClassName} placeholder="Mínimo 8 caracteres" />
          </div>
          <p id="password-help" className="mt-2 text-sm text-slate-600">Usa al menos 8 caracteres para proteger tu cuenta.</p>
        </div>

        <button type="submit" className="button-primary w-full">
          {isLoading ? "Creando cuenta…" : "Crear mi cuenta"}
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m13 7 5 5m0 0-5 5m5-5H6" /></svg>
        </button>
        </fieldset>
        {error && <p role="alert" className="notice-error mt-4">{error}</p>}
      </form>
      )}

      <div className="mt-8 border-t border-slate-200 pt-7 text-center">
        <p className="text-sm text-slate-600">
          ¿Ya tienes una cuenta?{" "}
          <Link href="/login" className="text-link">Inicia sesión</Link>
        </p>
      </div>
    </div>
  );
}
