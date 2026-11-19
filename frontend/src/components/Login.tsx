"use client";

import {academicReturn} from "@/lib/academic";
import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import { loginUser, SESSION_REJECTION_NOTICE_KEY } from "@/services/api";

export default function Login({ sessionExpired = false, passwordChanged = false }: { sessionExpired?: boolean; passwordChanged?: boolean }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showSessionNotice, setShowSessionNotice] = useState(false);

  useEffect(() => {
    if (!sessionExpired) return;

    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      try {
        const storage = window.sessionStorage;
        if (storage.getItem(SESSION_REJECTION_NOTICE_KEY) === "1") {
          storage.removeItem(SESSION_REJECTION_NOTICE_KEY);
          setShowSessionNotice(true);
        }
      } catch { /* sign-in remains available without tab storage */ }
    });
    return () => { active = false; };
  }, [sessionExpired]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isLoading) return;

    setIsLoading(true);
    setShowSessionNotice(false);
    setError("");
    setSuccess("");

    try {
      const { access_token } = await loginUser(email, password);
      localStorage.setItem("token", access_token);
      setPassword("");
      setSuccess("Sesión iniciada correctamente.");
      setTimeout(() => {
        let destination = "/dashboard";
          try { const saved = sessionStorage.getItem("pasapalabra-return"); sessionStorage.removeItem("pasapalabra-return"); if (saved && (/^\/pasapalabra(?:\/rooms)?(?:\/[1-9]\d*)?$/.test(saved) || academicReturn(saved) || /^\/trivial\/[1-9]\d*$/.test(saved) || saved === "/dashboard?join=1")) destination = saved; } catch { /* use dashboard when storage is unavailable */ }
          router.push(destination);
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

  return (
    <form method="post" onSubmit={handleSubmit} aria-busy={isLoading} className="space-y-5">
      {passwordChanged && <p role="status" className="notice-success">Contraseña cambiada. Todas las sesiones anteriores están cerradas. Inicia sesión de nuevo.</p>}
      {sessionExpired && showSessionNotice && (
        <p role="status" className="notice-warning">
          Tu sesión ha caducado o ya no es válida. Vuelve a iniciar sesión.
        </p>
      )}
      <div>
        <label htmlFor="login-email" className="form-label">
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
          className="form-input"
        />
      </div>
      <div>
        <label htmlFor="login-password" className="form-label">
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
          className="form-input"
        />
      </div>
      {error && <p role="alert" className="notice-error">{error}</p>}
      {success && <p role="status" className="notice-success">{success}</p>}
      <button
        type="submit"
        disabled={isLoading}
        className="button-primary w-full"
      >
        {isLoading ? "Iniciando sesión…" : "Entrar en BioGaMed"}
      </button>
    </form>
  );
}
