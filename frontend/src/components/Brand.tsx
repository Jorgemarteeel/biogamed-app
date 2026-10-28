import Link from "next/link";

export default function Brand() {
  return (
    <Link href="/" aria-label="BioGaMed, página de inicio" className="inline-block w-fit rounded-xl bg-white px-3 py-2 text-2xl font-black tracking-tight text-blue-950">
      Bio<span className="text-orange-700">Ga</span>Med
    </Link>
  );
}
