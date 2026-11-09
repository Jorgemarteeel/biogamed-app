import type { GameMode } from "@/services/api";
import {gameAvailabilityLabel} from "@/lib/academic";
import GameIllustration from "@/components/GameIllustration";

export const GAME_CHOICES = [
  { id: "TRIVIAL" as const, name: "Trivial", description: "Responde preguntas y descubre cuánto sabes." },
  { id: "PASAPALABRA" as const, name: "Pasapalabra", description: "Dos jugadores y dos roscos numerados de vocabulario científico." },
];

export default function GameChoiceCards({onSelect, selected, disabled=false, buttonRef, availability, compact=false}: {
  compact?: boolean;
  onSelect: (mode: GameMode) => void;
  selected?: GameMode;
  disabled?: boolean;
  availability?: Partial<Record<GameMode,number>>;
  buttonRef?: (mode: GameMode, node: HTMLButtonElement | null) => void;
}) {
  return (<div className="grid gap-5 sm:grid-cols-2">
        {GAME_CHOICES.map(item => {
          const count=availability?.[item.id];
          const unavailable=count!==undefined&&count<(item.id==="PASAPALABRA"?40:1);
          const locked=disabled||unavailable;
          return <button key={item.id} ref={node=>buttonRef?.(item.id,node)} type="button"
            aria-label={`Elegir ${item.name}`} disabled={locked}
            aria-describedby={count!==undefined?`game-availability-${item.id}`:undefined}
            aria-pressed={selected===undefined?undefined:selected===item.id}
            onClick={()=>{if(!locked)onSelect(item.id);}}
            className={`group flex min-w-0 flex-col rounded-2xl border border-sky-200 bg-white p-5 text-left shadow-sm transition motion-reduce:transition-none motion-reduce:transform-none enabled:hover:-translate-y-1 enabled:hover:border-sky-600 enabled:hover:shadow-lg focus-visible:border-sky-700 disabled:cursor-not-allowed disabled:hover:translate-y-0 ${compact?"!p-4":"sm:p-6"} ${selected===item.id?"border-sky-700 bg-sky-50 ring-2 ring-sky-700":""}`}>
            <span className={compact?"block w-full [&_svg]:h-28 sm:[&_svg]:h-32":"block w-full"}><GameIllustration mode={item.id}/></span>
            <span className={`${compact?"mt-3 text-xl":"mt-5 text-2xl"} font-black text-blue-950`}>{selected===item.id?"✓ ":""}{item.name}</span>
            <span className="mt-2 text-sm leading-6 text-slate-600">{item.description}</span>
            {count!==undefined&&<span id={`game-availability-${item.id}`} className="mt-3 text-sm font-semibold text-sky-900">{gameAvailabilityLabel(item.id,count)}</span>}
            <span className={`mt-3 font-bold ${unavailable?"text-slate-600":"text-sky-800 group-hover:underline"}`}>{unavailable?"No disponible":<>Elegir juego <span aria-hidden="true">→</span></>}</span>
          </button>;
        })}
      </div>);
}
