import type { ReviewItem } from "@/lib/game-review";

export default function GameReview({ items }: { items: ReviewItem[] }) {
  if (items.length === 0) return null;

  return <>
    <nav aria-label="Resultados por pregunta" className="my-3">
      <ol className="flex flex-wrap gap-2">
        {items.map((item) => {
          const status = item.isCorrect === null ? "sin corrección" : item.isCorrect ? "correcta" : "incorrecta";
          const number = item.position ?? `ID ${item.questionId}`;
          const appearance = item.isCorrect === null ? "border-slate-300 bg-white text-slate-700"
            : item.isCorrect ? "border-emerald-300 bg-emerald-50 text-emerald-900" : "border-red-300 bg-red-50 text-red-900";
          return <li key={item.questionId}>
            <a href={`#correction-${item.questionId}`} aria-label={`Pregunta ${number}: ${status}. Ver corrección`}
              className={`flex min-h-11 min-w-11 flex-col items-center justify-center rounded-lg border px-2 py-1 text-center transition-colors hover:border-sky-700 ${appearance}`}>
              <span aria-hidden="true" className="text-base font-bold leading-5">{number}</span>
              <span aria-hidden="true" className="text-xs font-bold leading-4">{item.isCorrect === null ? "?" : item.isCorrect ? "✓" : "×"}</span>
            </a>
          </li>;
        })}
      </ol>
      <p className="mt-2 flex flex-wrap gap-x-3 text-xs leading-5 text-slate-600">
        <span>✓ Correcta</span><span>× Incorrecta</span><span>? Sin corrección</span>
      </p>
    </nav>
    <ol className="mt-8 space-y-5" aria-label="Corrección de respuestas">
      {items.map((item) => <li key={item.questionId} className="rounded-xl border border-slate-200 p-5">
        <p className={`text-sm font-bold ${item.isCorrect === null ? "text-slate-700" : item.isCorrect ? "text-emerald-800" : "text-red-800"}`}>
          {item.position ?? `Pregunta ID ${item.questionId}`}. {item.isCorrect === null ? "Corrección no disponible" : item.isCorrect ? "Correcta" : "Incorrecta"}
        </p>
        <h3 id={`correction-${item.questionId}`} tabIndex={-1} className="mt-2 scroll-mt-6 break-words font-bold leading-7 text-blue-950 focus:outline-2 focus:outline-offset-4 focus:outline-sky-700">{item.text}</h3>
        {item.isCorrect !== null && <dl className="mt-4 space-y-3 text-sm leading-6">
          <div><dt className="font-semibold text-slate-600">Tu respuesta</dt><dd className="break-words text-slate-900">{item.selectedAnswer ?? "No consta en el historial"}</dd></div>
          <div><dt className="font-semibold text-emerald-800">Respuesta correcta</dt><dd className="break-words text-slate-900">{item.correctAnswer ?? "No consta en el historial"}</dd></div>
          {item.acceptedAnswers && item.acceptedAnswers.length > 0 && <div><dt className="font-semibold text-slate-600">Otras respuestas aceptadas</dt><dd className="break-words text-slate-900">{item.acceptedAnswers.join(", ")}</dd></div>}
        </dl>}
      </li>)}
    </ol>
  </>;
}
