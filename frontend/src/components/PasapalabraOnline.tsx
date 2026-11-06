"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import api from "@/services/api";
import { Frame, PasapalabraLoginLink } from "@/components/Pasapalabra";
import { TopicPicker } from "@/components/GamePicker";
import { saveJoinDraft, readJoinDraft, clearJoinDraft } from "@/lib/pasapalabra-join";
import layout from "./PasapalabraLayout.module.css";
interface Room {
  id: number; version: number; status: string; self_position: number;
  code: string | null; expires_at: string; server_now: string; match_id: number | null;
  configuration: { topic: string; category: string; difficulty: number | null; difficulty_unknown: boolean };
  participants: { position: number; name: string; ready: boolean }[];
}
export function roomErrorMessage(error: unknown) {
  if (!isAxiosError(error) || !error.response)
    return "No se pudo conectar con la sala. Comprueba tu conexión y reintenta la misma operación. Si la partida empezó, el reloj sigue corriendo.";
  const {status, data} = error.response;
  if (status === 401) return data?.detail === "Not authenticated"
    ? "No has iniciado sesión en este navegador. Inicia sesión para continuar."
    : "Tu sesión no es válida o ha caducado. Inicia sesión para continuar.";
  const labels: Record<string, string> = {
    DISTINCT_ACCOUNT_REQUIRED: "Esta sala la has creado tú. Únete con otra cuenta desde el navegador de tu rival.",
    ROOM_FULL: "La sala ya tiene dos jugadores. Pide al creador otro código de sala.",
    ROOM_UNAVAILABLE: "El código no es válido o la sala ya no admite jugadores.",
    ROOM_CANCELLED: "El creador ha cancelado esta sala. Pídele un nuevo código.",
    ROOM_EXPIRED: "La sala ha caducado. Pide al creador que prepare otra.",
    JOIN_RATE_LIMIT: "Demasiados intentos. Espera diez minutos antes de volver a unirte.",
    BOTH_READY_REQUIRED: "Ambos jugadores deben confirmar que están preparados.",
    TWO_PLAYERS_REQUIRED: "Falta el segundo jugador para poder confirmar e iniciar.",
    STALE_VERSION: "La sala ha cambiado. Revisa el estado actualizado y vuelve a confirmar.",
    INSUFFICIENT_QUESTIONS: `Hay ${data?.detail?.available ?? 0} de las 40 preguntas necesarias. No se han cambiado los filtros.`,
    ROOM_NOT_WAITING: "La sala ya no admite cambios.",
  };
  return labels[data?.detail?.code] ?? (status === 404 ? "Esta sala no está disponible para tu cuenta." : "No se pudo realizar la operación. Revisa la sala.");
}
const failure = roomErrorMessage;
function ModeIllustration({online}:{online:boolean}) {
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
export function PasapalabraEntry() {
  const router = useRouter();
  const [choice, setChoice] = useState<"LOCAL"|"ONLINE"|null>(null);
  const [action, setAction] = useState<"CREATE"|"JOIN"|null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [restored, setRestored] = useState(false);
  const lock = useRef(false);
  const codeField = useRef<HTMLInputElement>(null);
  const pending = useRef<{operation_id:string;code:string}|null>(null);
  useEffect(()=>{let live=true;void Promise.resolve().then(()=>{const saved=readJoinDraft();if(live&&saved){setCode(saved);setChoice('ONLINE');setAction('JOIN');setRestored(true);}});return()=>{live=false;};},[]);
  useEffect(()=>{if(action==='JOIN')codeField.current?.focus();},[action]);
  async function join() {
    if(lock.current||!code.trim())return;
    lock.current=true;setBusy(true);setError("");
    saveJoinDraft(code); // Before the request: a 401 interceptor may navigate immediately.
    pending.current??={operation_id:crypto.randomUUID(),code:code.trim().toUpperCase()};
    try {
      const {data}=await api.post<Room>('/pasapalabra/rooms/join',pending.current,{timeout:10000});
      clearJoinDraft();pending.current=null;router.push(`/pasapalabra/rooms/${data.id}`);
    } catch(e) {
      setError(failure(e));
      if(process.env.NODE_ENV==='development'&&isAxiosError(e)){
        // Diagnostic for real join failures. Never log token, invitation or request payload.
        const detail=e.response?.data?.detail;
        console.info('[Pasapalabra:join]',JSON.stringify({status:e.response?.status??'NETWORK',authenticatedRequest:!!e.config?.headers?.Authorization,
          detail:detail==='Not authenticated'||detail==='No se pudieron validar las credenciales.'?detail:typeof detail?.code==='string'?detail.code:'UNKNOWN'}));
      }
      if(isAxiosError(e)&&e.response&&e.response.status<500&&e.response.status!==408){pending.current=null;setUncertain(false);}
      else setUncertain(true);
    } finally {lock.current=false;setBusy(false);}
  }
  return <Frame title="Pasapalabra"><div className="mx-auto max-w-3xl space-y-5">
    <p className="text-sm text-slate-600">20 preguntas por jugador · 10 minutos individuales</p>
    <div className="grid grid-cols-2 gap-3 sm:gap-5" aria-label="Modalidad de Pasapalabra">
      {(['LOCAL','ONLINE'] as const).map(mode=><button key={mode} type="button" disabled={busy||uncertain}
        aria-label={mode==='LOCAL'?'En este dispositivo · Tú y un invitado':'En línea · Con un amigo · Dos cuentas'}
        aria-pressed={choice===mode} onClick={()=>{setChoice(mode);setAction(null);setError("");}}
        className={`relative min-w-0 rounded-2xl border-2 p-3 text-center focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-sky-700 sm:p-5 ${choice===mode?'border-sky-700 bg-sky-50 shadow-sm':'border-slate-200 bg-white hover:border-sky-500'}`}>
        <ModeIllustration online={mode==='ONLINE'}/><span className="mt-2 block text-base font-black text-blue-950 sm:text-lg">{mode==='LOCAL'?'En este dispositivo':'En línea'}</span>
        <span className="mt-1 block text-sm text-slate-600">{mode==='LOCAL'?'Tú y un invitado':'Con un amigo · Dos cuentas'}</span>
        {choice===mode&&<span className="mt-2 block text-xs font-bold text-sky-800">✓ Seleccionado</span>}
      </button>)}
    </div>
    {choice==='ONLINE'&&<div className="flex flex-wrap gap-3" aria-label="Acciones en línea">
      <button className={action==='CREATE'?'button-primary':'button-secondary'} aria-pressed={action==='CREATE'} disabled={busy||uncertain} onClick={()=>{setAction('CREATE');setError("");}}>Crear sala</button>
      <button className={action==='JOIN'?'button-primary':'button-secondary'} aria-pressed={action==='JOIN'} disabled={busy||uncertain} onClick={()=>{setAction('JOIN');setError("");}}>Unirme con código</button>
    </div>}
    {(choice==='LOCAL'||choice==='ONLINE'&&action==='CREATE')&&<section className="rounded-2xl border border-slate-200 bg-white p-5">
      <h2 className="mb-5 text-xl font-black text-blue-950">{choice==='LOCAL'?'Preparar partida local':'Crear sala'}</h2>
      <TopicPicker mode="PASAPALABRA" online={choice==='ONLINE'} onBack={()=>choice==='LOCAL'?setChoice(null):setAction(null)}/>
    </section>}
    {choice==='ONLINE'&&action==='JOIN'&&<section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5">
      <h2 className="text-xl font-black text-blue-950">Unirme con código</h2>
      <p className="text-sm text-slate-600">Usa tu propia cuenta y el código que te ha dado el creador.</p>
      {restored&&<p role="status" className="notice-warning">Hemos conservado tu código. Revísalo y pulsa «Unirme» cuando quieras continuar.</p>}
      <form onSubmit={e=>{e.preventDefault();void join();}}>
        <label htmlFor="room-code" className="form-label">Código privado</label>
        <input ref={codeField} id="room-code" className="form-input uppercase" maxLength={12} autoComplete="off" autoCapitalize="characters" spellCheck={false}
          value={code} disabled={busy||uncertain} onChange={e=>{setCode(e.target.value);saveJoinDraft(e.target.value);setRestored(false);}}/>
        <button className="button-primary mt-4" disabled={busy||!code.trim()}>{busy?'Uniéndome…':uncertain?'Reintentar la misma unión':'Unirme'}</button>
      </form>
      {error&&<div role="alert" className="notice-warning">{error} {error.includes('sesión')&&<><p className="my-2">Conservamos el código para volver aquí después de identificarte. La unión necesitará tu confirmación.</p><PasapalabraLoginLink/></>}</div>}
    </section>}
  </div></Frame>;
}
export function PasapalabraRoom({ id }: {
    id: number;
}) {
    const router = useRouter();
    const [room, setRoom] = useState<Room | null>(null);
    const latest = useRef<Room | null>(null);
    const [error, setError] = useState("");
    const [connectionError, setConnectionError] = useState("");
    const [busy, setBusy] = useState(false);
    const [uncertain, setUncertain] = useState(false);
    const [copied, setCopied] = useState(false);
    const lock = useRef(false);
    const pending = useRef<{
        kind: string;
        body: {
            operation_id: string;
            expected_version: number;
        };
    } | null>(null);
    const mounted = useRef(false);
    const refresh = useRef<() => Promise<void>>(async () => {});
    const accept = useCallback((r: Room) => { if (!mounted.current || latest.current && (r.version < latest.current.version || r.version === latest.current.version && Date.parse(r.server_now) < Date.parse(latest.current.server_now)))
        return; latest.current = r; setRoom(r); if (r.status === 'STARTED' && r.match_id)
        router.replace(`/pasapalabra/${r.match_id}`); }, [router]);
    useEffect(() => { mounted.current = true; let live = true; let fetching = false; let timer: ReturnType<typeof setTimeout>; async function poll() { if (!live || fetching)
        return; clearTimeout(timer); fetching = true; try {
        const { data } = await api.get<Room>(`/pasapalabra/rooms/${id}`, { timeout: 10000 });
        if (live) {
            accept(data);
            setConnectionError("");
        }
    }
    catch (e) {
        if (live)
            setConnectionError(failure(e));
    }
    finally {
        fetching = false;
        if (live && (!latest.current || latest.current.status === 'WAITING'))
            timer = setTimeout(poll, 1500);
    } } refresh.current = poll; void poll(); const focus = () => { clearTimeout(timer); void poll(); }; window.addEventListener('focus', focus); document.addEventListener('visibilitychange', focus); return () => { live = false; mounted.current = false; clearTimeout(timer); window.removeEventListener('focus', focus); document.removeEventListener('visibilitychange', focus); }; }, [id, accept]);
    async function act(kind: string) { if (lock.current || !latest.current)
        return; lock.current = true; setBusy(true); setError(""); pending.current ??= { kind, body: { operation_id: crypto.randomUUID(), expected_version: latest.current.version } }; try {
        const { data } = await api.post<Room>(`/pasapalabra/rooms/${id}/${pending.current.kind}`, pending.current.body, { timeout: 10000 });
        pending.current = null;
        setUncertain(false);
        if (data.status === 'LEFT')
            router.push('/pasapalabra');
        else
            accept(data);
    }
    catch (e) {
        setError(failure(e));
        if (isAxiosError(e) && e.response && e.response.status < 500 && e.response.status !== 408) {
            pending.current = null;
            setUncertain(false);
            await refresh.current();
        }
        else
            setUncertain(true);
    }
    finally {
        lock.current = false;
        if (mounted.current)
            setBusy(false);
    } }
    const canStart=room?.participants.length===2&&room.participants.every(p=>p.ready);
    return <Frame title="Pasapalabra en línea">
      {connectionError&&<p role="alert" className="notice-warning mb-2">{connectionError} {connectionError.includes('sesión')&&<PasapalabraLoginLink/>}</p>}
      {error&&<p role="alert" className="notice-error mb-2">{error} {error.includes('sesión')&&<PasapalabraLoginLink/>}</p>}
      {!room?<p role="status">{connectionError?'No se pudo cargar la sala. Revisa el aviso anterior.':'Cargando sala…'}</p>:<section className={layout.lobbyCard}>
        <h2>Sala privada</h2>
        <div className={layout.lobbyOverview}>
          <div className={layout.lobbyInfo}>
            {room.code&&<div className={layout.inviteBox}><div className="min-w-0"><p className="text-sm font-semibold text-sky-900">Código de invitación</p><p className="font-mono font-black text-blue-950" aria-label="Código de invitación">{room.code}</p></div>
              <button className="button-secondary" onClick={async()=>{try{await navigator.clipboard.writeText(room.code!);setCopied(true);}catch{setError('No se pudo copiar. Selecciona el código y cópialo manualmente.');}}}>Copiar código</button>{copied&&<p role="status" className="w-full text-sm font-bold text-sky-800">Código copiado</p>}</div>}
            <div className={layout.lobbyConfig}><h3>Reto elegido</h3><p tabIndex={0}>{room.configuration.topic}</p><p tabIndex={0}>{room.configuration.category} · {room.configuration.difficulty_unknown?'Sin clasificar':room.configuration.difficulty?`Nivel ${room.configuration.difficulty}`:'Dificultad sin filtrar'}</p><p>20 preguntas por jugador · 10 minutos individuales</p></div>
            <p className={layout.lobbyExpiry}>Caduca el {new Intl.DateTimeFormat('es-ES',{dateStyle:'short',timeStyle:'short',timeZone:'Atlantic/Canary'}).format(new Date(room.expires_at))} (hora canaria).</p>
          </div>
          <section aria-label="Jugadores de la sala"><h3 className="font-black text-blue-950" aria-live="polite">Jugadores · {room.participants.length}/2</h3>
            <ul className={layout.lobbyRoster}>{[1,2].map(position=>{const p=room.participants.find(player=>player.position===position);return <li key={position}>
              {p?<><div className="flex items-start gap-3"><span aria-hidden="true" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-950 font-black text-white">{p.name.trim().slice(0,1)}</span><div className="min-w-0"><p tabIndex={0} className="break-words font-bold text-blue-950">{p.name}</p><div className="flex flex-wrap gap-2 text-xs font-bold text-sky-800">{position===1&&<span>Creador</span>}{position===room.self_position&&<span>Tú</span>}</div></div></div><p className={`text-sm font-bold ${p.ready?'text-green-800':'text-slate-600'}`}>{p.ready?'✓ Preparado':'○ Sin confirmar'}</p></>:<><p className="font-semibold text-slate-600">{room.status==='WAITING'?'Esperando a otro jugador':'Plaza libre'}</p><p className="text-sm text-slate-500">{room.status==='WAITING'?'Comparte el código para completar la sala.':'La sala está cerrada.'}</p></>}
            </li>})}</ul>
          </section>
        </div>
        {room.status==='WAITING'?<>
          <p role="status" className="text-sm font-semibold text-blue-950">{room.participants.length<2?'Falta el segundo jugador. Comparte el código para que se una.':!canStart?'Antes de iniciar, ambos debéis pulsar «Estoy preparado».':room.self_position===1?'Todo preparado. Ya puedes iniciar la partida.':'Todo preparado. El creador puede iniciar la partida.'}</p>
          <div className={layout.actions}><button className="button-primary" disabled={busy||uncertain||room.participants.length!==2||room.participants.find(p=>p.position===room.self_position)?.ready} onClick={()=>act('ready')}>Estoy preparado</button>
            {room.self_position===1&&<button className="button-primary" disabled={busy||uncertain||!canStart} onClick={()=>act('start')}>Iniciar partida</button>}<button className="button-secondary" disabled={busy||uncertain} onClick={()=>act(room.self_position===1?'cancel':'leave')}>{room.self_position===1?'Cancelar sala':'Salir de la sala'}</button></div>
        </>:<p role="status" className="font-bold text-blue-950">{room.status==='CANCELLED'?'Sala cancelada.':room.status==='EXPIRED'?'Sala caducada.':'Abriendo partida…'}</p>}
        {uncertain&&<button className="button-primary" disabled={busy} onClick={()=>act(pending.current!.kind)}>Reintentar la misma operación</button>}
        <details className={layout.help}><summary>Cómo funciona la sala</summary><p>Dispones de 30 minutos desde su creación para iniciar. Si el segundo jugador sale, ambos tendréis que confirmar de nuevo. La lista muestra pertenencia a la sala, no presencia en línea.</p></details>
        <Link className="text-link inline-flex min-h-8 items-center text-sm" href="/pasapalabra">Volver a elegir modalidad</Link>
      </section>}
    </Frame>;
}
