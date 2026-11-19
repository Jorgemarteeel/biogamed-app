"use client";

import Link from "next/link";
import useSessionToken from "@/lib/session-token";

export default function Brand() {
  const signedIn = useSessionToken();
  return (
    <Link
      href={signedIn ? "/dashboard" : "/"}
      aria-label={signedIn ? "BioGaMed, volver al panel" : "BioGaMed, página de inicio"}
      className="inline-block w-fit shrink-0 rounded-xl bg-white px-3 py-2 text-2xl font-black tracking-tight text-blue-950"
    >
      Bio<span className="text-orange-700">Ga</span>Med
    </Link>
  );
}
