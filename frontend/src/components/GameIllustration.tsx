import type { GameMode } from "@/services/api";

export default function GameIllustration({ mode }: { mode: GameMode }) {
  return <svg viewBox="0 0 320 190" role="img" aria-label={mode === "TRIVIAL" ? "Rueda de cuatro categorías con tarjetas de preguntas" : "Rosco numerado"} className="h-40 w-full sm:h-44">
    <rect width="320" height="190" rx="22" fill={mode === "TRIVIAL" ? "#e0f2fe" : "#ccfbf1"} />
    <circle cx="160" cy="94" r="68" fill="white" opacity=".75" />
    {mode === "TRIVIAL" ? <>
      <path d="M160 94V35a59 59 0 0 1 59 59Z" fill="#0369a1" /><path d="M160 94h59a59 59 0 0 1-59 59Z" fill="#f97316" /><path d="M160 94v59a59 59 0 0 1-59-59Z" fill="#0d9488" /><path d="M160 94h-59a59 59 0 0 1 59-59Z" fill="#1e3a8a" />
      <circle cx="160" cy="94" r="23" fill="white" /><text x="160" y="104" textAnchor="middle" fontSize="30" fontWeight="800" fill="#1e3a8a">?</text>
      <g transform="rotate(-12 55 105)"><rect x="25" y="77" width="65" height="54" rx="9" fill="white" stroke="#94a3b8" strokeWidth="2" /><path d="M37 92h37M37 102h28M37 112h33" stroke="#0369a1" strokeWidth="3" strokeLinecap="round" /></g>
      <g transform="rotate(12 265 105)"><rect x="230" y="77" width="65" height="54" rx="9" fill="white" stroke="#94a3b8" strokeWidth="2" /><path d="M242 92h37M242 102h28M242 112h33" stroke="#f97316" strokeWidth="3" strokeLinecap="round" /></g>
    </> : <>
      {Array.from({ length: 20 }, (_, index) => {
        const angle = (index * Math.PI * 2) / 20 - Math.PI / 2;
        const x = 160 + Math.cos(angle) * 61;
        const y = 94 + Math.sin(angle) * 61;
        return <g key={index}><circle cx={x} cy={y} r="10" fill={index % 4 === 0 ? "#0d9488" : "#1e3a8a"} /><text x={x} y={y + 5} textAnchor="middle" fontSize="10" fontWeight="700" fill="white">{index + 1}</text></g>;
      })}
      <circle cx="160" cy="94" r="37" fill="white" /><path d="M143 91h34M149 102h22" stroke="#0d9488" strokeWidth="5" strokeLinecap="round" />
    </>}
  </svg>;
}
