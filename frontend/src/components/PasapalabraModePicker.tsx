export function PasapalabraModeIllustration({online}:{online:boolean}) {
  return <svg viewBox="0 0 240 104" aria-hidden="true" className="mx-auto h-20 w-full max-w-56" fill="none">
    <rect x="4" y="4" width="232" height="96" rx="22" fill={online?'#e0f2fe':'#ccfbf1'}/>
    {[72,168].map((x,i)=><g key={x} stroke={i?'#c2410c':'#1e3a8a'} strokeWidth="3" strokeLinecap="round">
      <circle cx={x} cy="26" r="10" fill="white"/><path d={`M${x-17} 53c0-17 34-17 34 0`} fill="white"/>
      <circle cx={x+13} cy="32" r="7" fill={i&&!online?'white':'#1e3a8a'} stroke={i&&!online?'#c2410c':'#1e3a8a'}/>
      {i&&!online?<path d={`M${x+10} 32h6m-3-3v6`} strokeWidth="2"/>:<path d={`m${x+10} 32 2 2 4-4`} stroke="white" strokeWidth="2"/>}
    </g>)}
    {online?<><path d="M100 73h40" stroke="#0369a1" strokeWidth="3" strokeDasharray="4 4"/><circle cx="120" cy="73" r="5" fill="#0d9488"/>{[48,144].map(x=><g key={x}><rect x={x} y="58" width="48" height="33" rx="5" fill="white" stroke="#1e3a8a" strokeWidth="3"/><path d={`M${x+17} 84h14`} stroke="#0369a1" strokeWidth="2"/></g>)}</>:<><path d="M72 55v17h20m76-17v17h-20" stroke="#0d9488" strokeWidth="3"/><rect x="86" y="57" width="68" height="36" rx="5" fill="white" stroke="#1e3a8a" strokeWidth="3"/><path d="M108 85h24" stroke="#0369a1" strokeWidth="2"/></>}
  </svg>;
}

export type PasapalabraPlayMode = "LOCAL" | "ONLINE";
export default function PasapalabraModePicker({selected, onSelect, disabled=false, compact=false}: {
  compact?: boolean;
  selected?: PasapalabraPlayMode;
  onSelect: (mode: PasapalabraPlayMode) => void;
  disabled?: boolean;
}) {
  return (<div className="grid grid-cols-2 gap-3 sm:gap-5" aria-label="Modalidad de Pasapalabra">
      {(['LOCAL','ONLINE'] as const).map(mode=><button key={mode} type="button" disabled={disabled}
        aria-label={mode==='LOCAL'?'En este dispositivo · Tú y un invitado':'En línea · Con un amigo · Dos cuentas'}
        aria-pressed={selected===mode} onClick={()=>onSelect(mode)}
        className={`relative min-w-0 rounded-2xl border-2 p-3 text-center focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-sky-700 ${compact?"sm:p-4":"sm:p-5"} ${selected===mode?'border-sky-700 bg-sky-50 shadow-sm':'border-slate-200 bg-white hover:border-sky-500'}`}>
        <PasapalabraModeIllustration online={mode==='ONLINE'}/><span className="mt-2 block text-base font-black text-blue-950 sm:text-lg">{mode==='LOCAL'?'En este dispositivo':'En línea'}</span>
        <span className="mt-1 block text-sm text-slate-600">{mode==='LOCAL'?'Tú y un invitado':'Con un amigo · Dos cuentas'}</span>
        {selected===mode&&<span className="mt-2 block text-xs font-bold text-sky-800">✓ Seleccionado</span>}
      </button>)}
    </div>);
}
