"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import { loginUser } from "@/services/api";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isLoading) return;

    setIsLoading(true);
    setError("");
    setSuccess("");

    try {
      const { access_token } = await loginUser(email, password);
      localStorage.setItem("token", access_token);
      setPassword("");
      setSuccess("Sesión iniciada correctamente.");
      setTimeout(() => {
        router.push("/dashboard");
      }, 1000);
    } catch (err: unknown) {
      if (isAxiosError(err)) {
        setError(
          err.response?.status === 401
            ? "Credenciales incorrectas. Revisa tu correo y contraseña."
            : !err.response
              ? "No se pudo conectar con el servidor. Inténtalo de nuevo."
              : "No se pudo iniciar sesión. Inténtalo de nuevo.",
        );
      } else {
        setError("No se pudo completar el inicio de sesión. Inténtalo de nuevo.");
      }
    } finally {
      setIsLoading(false);
    }
  }

  const inputClassName =
    "block w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-700";

  return (
    <form onSubmit={handleSubmit} aria-busy={isLoading} className="space-y-5">
      <div>
        <label htmlFor="login-email" className="mb-2 block font-semibold">
          Correo electrónico
        </label>
        <input
          id="login-email"
          name="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          disabled={isLoading}
          required
          className={inputClassName}
        />
      </div>
      <div>
        <label htmlFor="login-password" className="mb-2 block font-semibold">
          Contraseña
        </label>
        <input
          id="login-password"
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={isLoading}
          required
          className={inputClassName}
        />
      </div>
      {error && <p role="alert" className="text-red-700">{error}</p>}
      {success && <p role="status" className="text-green-700">{success}</p>}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full rounded-xl bg-orange-500 px-5 py-3 font-bold text-white hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isLoading ? "Iniciando sesión…" : "Entrar en BioGaMed"}
      </button>
    </form>
  );
}
