import ActivationForm from "@/components/ActivationForm";

export default function ActivationPage() {
  return (
    <div>
      <h1 className="mb-4 text-3xl font-black text-blue-950">Activa tu cuenta</h1>
      <p className="mb-6 text-slate-600">Elige la contraseña que usarás con tu DNI para entrar en BioGaMed.</p>
      <ActivationForm />
    </div>
  );
}
