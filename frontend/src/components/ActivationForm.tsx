"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { isAxiosError } from "axios";
import api from "@/services/api";

export default function ActivationForm() {
  const [code, setCode] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  useEffect(() => {
    queueMicrotask(() => {
      const value = new URLSearchParams(window.location.hash.slice(1)).get("code") ?? "";
      setCode(/^[A-Za-z0-9_-]{43}$/.test(value) ? value : "");
    });
  }, []);

  async function activate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!code || busy) return;
    if (password !== confirmation) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.post("/auth/activate", { code, password });
      setPassword("");
      setConfirmation("");
      router.replace("/login?activated=1");
    } catch (err) {
      setError(isAxiosError(err) && typeof err.response?.data?.detail === "string"
        ? err.response.data.detail : "No se pudo activar la cuenta. Inténtalo de nuevo.");
      setBusy(false);
    }
  }

  if (code === null) return <p role="status">Cargando invitación…</p>;
  if (!code) return <p role="alert">Abre el enlace de activación recibido en tu correo.</p>;

  return (
    <form method="post" onSubmit={activate} aria-busy={busy} className="space-y-5">
      <div>
        <label htmlFor="activation-password" className="form-label">Contraseña nueva</label>
        <input id="activation-password" type="password" className="form-input" autoComplete="new-password"
          minLength={8} maxLength={255} required disabled={busy} value={password}
          onChange={event => setPassword(event.target.value)} />
        <p className="mt-2 text-sm text-slate-600">Usa entre 8 y 255 caracteres.</p>
      </div>
      <div>
        <label htmlFor="confirm-activation-password" className="form-label">Confirma la contraseña</label>
        <input id="confirm-activation-password" type="password" className="form-input" autoComplete="new-password"
          minLength={8} maxLength={255} required disabled={busy} value={confirmation}
          onChange={event => setConfirmation(event.target.value)} />
      </div>
      {error && <p role="alert" className="notice-error">{error}</p>}
      <button className="button-primary w-full" disabled={busy}>
        {busy ? "Activando…" : "Activar cuenta"}
      </button>
      <Link href="/login" className="text-link">Ir a Iniciar sesión</Link>
    </form>
  );
}
