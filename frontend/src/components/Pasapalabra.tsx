"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import Brand from "@/components/Brand";
import ProfileMenu from "@/components/ProfileMenu";
import api, { type GameAvailability } from "@/services/api";
import { getMatch, sendOperation, newer, questionKey, remaining, startsCelebration, type Match, type Player, type Operation } from "@/lib/pasapalabra";
import { StateLegend, Corrections, ResultHero } from "@/components/PasapalabraPresentation";
import layout from "./PasapalabraLayout.module.css";
function message(e: unknown) { const status = isAxiosError(e) ? e.response?.status : 0; return status === 404 || status === 403 ? "Esta partida no está disponible para tu cuenta." : status === 401 ? "Tu sesión ha caducado. Inicia sesión para recuperar la partida." : status === 409 ? "La partida ha cambiado. Consulta el estado antes de continuar." : "No se pudo confirmar la operación. Comprueba tu conexión y reintenta. El reloj sigue corriendo."; }
export function PasapalabraLoginLink() {
    return <Link href="/login" className="text-link" onClick={() => {
        try { sessionStorage.setItem("pasapalabra-return", window.location.pathname); }
        catch { /* login remains available when storage is disabled */ }
    }}>Iniciar sesión</Link>;
}
export function Frame({ children, title = "Pasapalabra local", playing = false }: {
    playing?: boolean;
    title?: string;
    children: React.ReactNode;
}) {
    return <div className={`${layout.shell} ${playing ? layout.playingShell : ""}`} data-pasapalabra-shell>
    <header className="site-header">
    <nav className={layout.navigation}>
    <Brand />
    <ProfileMenu />
    </nav>
    </header>
    <main className={layout.main}>
    <div className={layout.titleRow}>
    <Link className="text-link" href="/dashboard">← Volver al panel</Link>
    <h1>{title}</h1></div><div className={layout.content}>{children}</div></main>
    </div>;
}
export function PasapalabraPrepare({ topicId, online = false }: {
    online?: boolean;
    topicId: number;
}) {
    const router = useRouter();
    const [bank, setBank] = useState<GameAvailability | null>(null);
    const [category, setCategory] = useState("");
    const [level, setLevel] = useState("");
    const [name, setName] = useState("");
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    const [count, setCount] = useState<number | null>(null);
    const [retryStart, setRetryStart] = useState(false);
    const [attempt, setAttempt] = useState(0);
    const lock = useRef(false);
    const pending = useRef<Record<string, unknown> | null>(null);
    useEffect(() => {
        let live = true;
        api.get(`/game/availability/${topicId}`, { params: { mode: "PASAPALABRA" } }).then(r => {
            if (live)
                setBank(r.data);
        }).catch(e => {
            if (live)
                setError(message(e));
        });
        return () => { live = false; };
    }, [topicId, attempt]);
    useEffect(() => {
        let live = true;
        api.post('/pasapalabra/preparations', { topic_id: topicId, ...(category ? { category_id: Number(category) } : {}), ...(level === "unknown" ? { difficulty_unknown: true } : level ? { difficulty: Number(level) } : {}) }).then(r => {
            if (live)
                setCount(r.data.available);
        }).catch(e => {
            if (live)
                setError(message(e));
        });
        return () => { live = false; };
    }, [topicId, category, level, attempt]);
    async function start() {
        if (lock.current)
            return;
        lock.current = true;
        setBusy(true);
        setRetryStart(true);
        setError("");
        pending.current ??= { operation_id: crypto.randomUUID(), topic_id: topicId, ...(online ? {} : {guest_name: name.trim()}), ...(category ? { category_id: Number(category) } : {}), ...(level === "unknown" ? { difficulty_unknown: true } : level ? { difficulty: Number(level) } : {}) };
        try {
            const r = await api.post(online ? '/pasapalabra/rooms' : '/pasapalabra/local/start', pending.current, {timeout:10000});
            router.push(online ? `/pasapalabra/rooms/${r.data.id}` : `/pasapalabra/${r.data.id}`);
        }
        catch (e) {
            setError(message(e));
            if (isAxiosError(e) && e.response && e.response.status < 500 && e.response.status !== 408) {
                pending.current = null;
                setRetryStart(false);
                if (e.response.data?.detail?.available !== undefined)
                    setCount(e.response.data.detail.available);
            }
        }
        finally {
            lock.current = false;
            setBusy(false);
        }
    }
    const categories = [...new Map(bank?.combinations.filter(c => c.category_id !== null).map(c => [c.category_id, c.category_name])).entries()];
    return <Frame title={online ? "Pasapalabra en línea" : "Pasapalabra local"}>
    <section className={layout.prepareCard}>
    <h2 className="text-xl font-bold">{online ? "Dos cuentas, dos dispositivos" : "Dos jugadores, un dispositivo"}</h2>
    <p>20 preguntas por jugador · 10 minutos individuales · 40 preguntas distintas.</p>
    {!online && <label className="block">Nombre del invitado<input className="form-input" value={name} disabled={busy || retryStart} onChange={e => setName(e.target.value)} maxLength={255}/>
    </label>}
    <div className={layout.filters}><label className="block">Categoría<select className="form-input" value={category} disabled={busy || retryStart} onChange={e => { setCategory(e.target.value); setCount(null); }}>
    <option value="">Todas, incluidas sin categoría</option>{categories.map(([id, label]) => <option key={id} value={id!}>{label}</option>)}</select>
    </label>
    <label className="block">Dificultad<select className="form-input" value={level} disabled={busy || retryStart} onChange={e => { setLevel(e.target.value); setCount(null); }}>
    <option value="">Sin filtrar</option>{[...new Set(bank?.combinations.map(c => c.difficulty))].map(v => <option key={v ?? "unknown"} value={v ?? "unknown"}>{v === null ? "Sin clasificar" : `Nivel ${v}`}</option>)}</select>
    </label></div>
    <p role="status">{count === null ? "Consultando disponibilidad…" : `${count} preguntas disponibles de las 40 necesarias.${count < 40 ? " No hay suficientes: revisa los filtros; no se cambiarán automáticamente." : ""}`}</p>{error && <p role="alert">{error}</p>}<div className={layout.actions}><button className="button-secondary" disabled={busy || retryStart} onClick={() => { setCount(null); setError(""); setAttempt(v => v + 1); }}>Volver a consultar disponibilidad</button>
    <button className="button-primary" disabled={busy || (!retryStart && (count === null || count < 40 || (!online && !name.trim())))} onClick={start}>{busy ? "Iniciando…" : retryStart ? "Reintentar el mismo inicio" : online ? "Crear sala privada" : "Comenzar partida"}</button>
    </div><details className={layout.help}><summary>Historial y reloj</summary><p>{online ? "Cada cuenta conserva exclusivamente su resultado personal." : "Solo tu resultado se guarda en tu historial personal; el invitado no tiene progreso propio."} Recargar o cerrar la pestaña durante el juego no pausa el reloj.</p></details>
    </section>
    </Frame>;
}
function timeLabel(ms: number) { const seconds = Math.ceil(ms / 1000); return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`; }
function Rosco({ p, s, elapsed, secondary = false }: {
    secondary?: boolean;
    p: Player;
    s: Match;
    elapsed: number;
}) {
    const active = s.active_participant === p.position;
    const ms = remaining(s, p, elapsed);
    const sec = Math.ceil(ms / 1000);
    const symbols: Record<string, string> = { PENDING: "·", PASSED: "↻", CORRECT: "✓", WRONG: "×" };
    const labels: Record<string, string> = { PENDING: "Pendiente", PASSED: "Pasada", CORRECT: "Acertada", WRONG: "Fallada" };
    return <section className={`${layout.roscoCard} ${active?layout.activeRosco:''} ${secondary?layout.roscoSecondary:''}`} aria-label={`Rosco de ${p.name}`} data-rosco-position={p.position}>
      <h2 className={layout.playerName} tabIndex={0}>{p.name}</h2>
      <p className={layout.playerTurn}>{p.status==='FINISHED'?(p.finish_reason==='TIMEOUT'?'Tiempo agotado':p.finish_reason==='RESOLVED'?'Preguntas resueltas':'Finalizado'):active?(s.play_mode==='ONLINE'&&p.position!==s.self_position?'Turno del rival':'Tu turno'):'En espera'}</p>
      <p className={layout.clock} aria-label="Tiempo restante">{Math.floor(sec/60)}:{String(sec%60).padStart(2,'0')}</p>
      <p className={layout.counts}><span>✓ {p.correct} aciertos</span><span>× {p.wrong} fallos</span><span>{p.pending} pendientes</span></p>
      <ol className="sr-only">{p.slots.map(slot=><li key={slot.number}>{slot.number}: {labels[slot.state]}{active&&s.active_question?.number===slot.number?', actual':''}</li>)}</ol>
      <div className={layout.roscoCanvas}><svg viewBox="0 0 400 400" role="img" aria-label={`20 posiciones numeradas de ${p.name}`}>
        <circle cx="200" cy="200" r="155" fill="none" stroke="#e2e8f0" strokeWidth="4"/>{p.slots.map((q,i)=>{
          const angle=i*Math.PI/10-Math.PI/2;const x=200+155*Math.cos(angle),y=200+155*Math.sin(angle);
          const current=active&&s.active_question?.number===q.number;
          return <g key={q.number} aria-label={`${q.number}: ${labels[q.state]}${current?', actual':''}`}><title>{`${q.number}: ${labels[q.state]}${current?', actual':''}`}</title>
            <circle cx={x} cy={y} r="21" fill={q.state==='CORRECT'?'#166534':q.state==='WRONG'?'#991b1b':q.state==='PASSED'?'#92400e':'#1e3a8a'} stroke={current?'#0284c7':'white'} strokeWidth={current?7:2}/>
            <text x={x} y={y+1} textAnchor="middle" fill="white" fontSize="17" fontWeight="bold">{q.number}</text><text x={x} y={y+15} textAnchor="middle" fill="white" fontSize="12">{symbols[q.state]}</text>
          </g>;
        })}<text x="200" y="197" textAnchor="middle" fill="#1e3a8a" fontSize="20" fontWeight="bold">{active?'Turno activo':'Pasapalabra'}</text><text x="200" y="223" textAnchor="middle" fill="#475569" fontSize="14">20 preguntas</text>
      </svg></div>
      <div className={layout.compactSlots} aria-hidden="true">{p.slots.map(slot=><span key={slot.number} data-current={active&&s.active_question?.number===slot.number} style={{background:slot.state==='CORRECT'?'#166534':slot.state==='WRONG'?'#991b1b':slot.state==='PASSED'?'#92400e':'#1e3a8a'}}>{slot.number} {symbols[slot.state]}</span>)}</div>
    </section>;
}
export function PasapalabraGame({ id }: {
    id: number;
}) {
    const [state, setState] = useState<Match | null>(null);
    const [connectionError, setConnectionError] = useState("");
    const [celebrate, setCelebrate] = useState(false);
    useEffect(() => { if (!celebrate) return; const timer = setTimeout(() => setCelebrate(false), 3000); return () => clearTimeout(timer); }, [celebrate]);
    const latest = useRef<Match | null>(null);
    const [text, setText] = useState("");
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    const [uncertain, setUncertain] = useState(false);
    const pending = useRef<Operation | null>(null);
    const lock = useRef(false);
    const [abandon, setAbandon] = useState<number | null>(null);
    const abandonDialog = useRef<HTMLDialogElement>(null);
    const abandonTrigger = useRef<HTMLButtonElement>(null);
    const questionRegion = useRef<HTMLDivElement>(null);
    const visibleQuestion = state ? questionKey(state) : "";
    useEffect(() => { if (questionRegion.current) questionRegion.current.scrollTop = 0; }, [visibleQuestion]);
    useEffect(() => {
        const dialog = abandonDialog.current;
        if (abandon !== null && dialog && !dialog.open) {
            dialog.showModal();
            dialog.querySelector<HTMLButtonElement>('[data-cancel-abandon]')?.focus();
        }
        return () => { if (dialog?.open) dialog.close(); };
    }, [abandon]);
    const [elapsed, setElapsed] = useState(0);
    const received = useRef(0);
    const mounted = useRef(false);
    const refresh = useRef<() => Promise<void>>(async () => {});
    function accept(s: Match) {
        if (!mounted.current || !newer(latest.current, s))
            return;
        if (latest.current && questionKey(latest.current) !== questionKey(s))
            setText("");
        if (startsCelebration(latest.current, s)) setCelebrate(true);
        latest.current = s;
        received.current = performance.now();
        setElapsed(0);
        setState(s);
    }
    useEffect(() => {
        mounted.current = true;
        let live = true;
        let timer: ReturnType<typeof setTimeout>;
        let fetching = false;
        async function poll() {
            if (fetching || !live)
                return;
            clearTimeout(timer);
            fetching = true;
            try {
                const response = await getMatch(id);
                if (live) { accept(response); setConnectionError(""); }
            }
            catch (e) {
                if (mounted.current)
                    setConnectionError(message(e));
            }
            finally {
                fetching = false;
                if (live && latest.current?.status !== "FINISHED")
                    timer = setTimeout(poll, 1000);
            }
        }
        refresh.current = poll;
        void poll();
        const focus = () => { clearTimeout(timer); void poll(); };
        window.addEventListener('focus', focus);
        document.addEventListener('visibilitychange', focus);
        const tick = setInterval(() => setElapsed(performance.now() - received.current), 250);
        return () => { live = false; mounted.current = false; clearTimeout(timer); clearInterval(tick); window.removeEventListener('focus', focus); document.removeEventListener('visibilitychange', focus); };
    }, [id]);
    async function act(kind: Operation['kind'], participant?: number) {
        if (lock.current || !latest.current)
            return;
        const s = latest.current;
        if (!pending.current) {
            const q = s.active_question;
            if (!q && kind !== "abandon")
                return;
            pending.current = { kind, body: { operation_id: crypto.randomUUID(), expected_version: s.version, participant: s.play_mode === "ONLINE" ? s.self_position! : participant ?? q!.participant, ...(kind === 'abandon' ? {} : { number: q!.number }), ...(kind === 'answer' ? { text_answer: text } : {}) } };
        }
        lock.current = true;
        setBusy(true);
        setError("");
        try {
            const next = await sendOperation(id, pending.current);
            pending.current = null;
            setUncertain(false);
            abandonDialog.current?.close();
            setAbandon(null);
            accept(next);
        }
        catch (e) {
            setError(message(e));
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
        }
    }
    const s = state;
    const q = s?.active_question;
    return <Frame playing={s?.status==='RUNNING'} title={s?.play_mode==='ONLINE'?'Pasapalabra en línea':s?'Pasapalabra local':'Pasapalabra'}>
      {connectionError&&<p role="alert" className="notice-warning mb-2">{connectionError} {connectionError.includes('sesión')&&<PasapalabraLoginLink/>}</p>}
      {error&&<p role="alert" className="notice-error mb-2">{error} <PasapalabraLoginLink/></p>}
      {!s?<p role="status">{error||connectionError?'No se pudo cargar la partida. Revisa el aviso anterior o vuelve al panel.':'Cargando partida…'}</p>:<>
        {s.status==='FINISHED'&&<ResultHero match={s} celebrate={celebrate}/>}
        {s.status!=='FINISHED'&&<div className={layout.gameStage} data-game-stage>
          <div className={layout.board} data-game-board>
            <div className={layout.players}><Rosco p={s.participants[0]} s={s} elapsed={elapsed}/><Rosco p={s.participants[1]} s={s} elapsed={elapsed}/></div>
            <section className={layout.questionCard} aria-label="Pregunta y controles">
              <div className={layout.mobilePlayers} aria-label="Relojes de ambos jugadores">{s.participants.map(p=><p key={p.position}><strong tabIndex={0}>{p.name}</strong>{timeLabel(remaining(s,p,elapsed))}{s.active_participant===p.position?' · Turno activo':''}<br/>✓ {p.correct} · × {p.wrong} · {p.pending} pendientes</p>)}</div>
              <div className={layout.questionHeading}><h2 className={layout.questionTitle} tabIndex={0}>{q?<>{s.play_mode==='ONLINE'?'Tu turno':`Turno de ${s.participants.find(p=>p.position===q.participant)?.name}`} · Pregunta {q.number}</>:<>Turno de {s.participants.find(p=>p.position===s.active_participant)?.name}</>}</h2>
                <details className={layout.legend} onKeyDown={e=>{if(e.key==='Escape'){e.currentTarget.open=false;e.currentTarget.querySelector('summary')?.focus();}}}><summary>Leyenda</summary><div><StateLegend/></div></details>
              </div>
              <div ref={questionRegion} className={layout.questionScroll} role="region" tabIndex={0} aria-label="Enunciado completo" aria-describedby="question-scroll-hint">
                {q?<p aria-live="polite">{q.text}</p>:<p>{s.participants.find(p=>p.position===s.self_position)?.status==='FINISHED'?'Has terminado. El rival puede continuar hasta resolver sus preguntas o agotar su tiempo.':'El reloj del rival sigue en marcha. Tu pregunta aparecerá cuando sea tu turno.'}</p>}
              </div>
              <p id="question-scroll-hint" className={layout.questionHint}>Si el enunciado es largo, desplázalo con rueda, gesto o teclado.</p>
              {q&&<form className={layout.answerForm} onSubmit={e=>{e.preventDefault();if(text.trim()&&!uncertain)void act('answer');}}>
                <label htmlFor="word">Respuesta</label><input id="word" className="form-input" autoComplete="off" value={text} onChange={e=>setText(e.target.value)} readOnly={busy||uncertain}/>
                <div className={layout.actions}><button className="button-primary" disabled={busy||uncertain||!text.trim()}>Responder</button><button type="button" className="button-secondary" disabled={busy||uncertain} onClick={()=>act('pass')}>Pasapalabra</button></div>
              </form>}
              <div className={layout.questionFooter}><span>El reloj continúa al cerrar la pestaña.</span><button ref={abandonTrigger} className="text-link" disabled={busy||uncertain} onClick={()=>setAbandon(s.play_mode==='ONLINE'?s.self_position!:q!.participant)}>Abandonar…</button></div>
              {uncertain&&<button className="button-primary" disabled={busy} onClick={()=>act(pending.current!.kind)}>Reintentar la misma acción</button>}
            </section>
          </div>
          <Corrections match={s} compact/>
        </div>}
        {s.status==='FINISHED'&&<><details className={layout.secondary}><summary>Ver los roscos finales</summary><div className={layout.secondaryBody} tabIndex={0} role="region" aria-label="Roscos finales"><div className={layout.finalRoscos}>{s.participants.map(p=><Rosco key={p.position} p={p} s={s} elapsed={elapsed} secondary/>)}</div></div></details>
          <details className={layout.secondary}><summary>Revisar respuestas resueltas</summary><div className={layout.secondaryBody} tabIndex={0} role="region" aria-label="Respuestas finales"><Corrections match={s}/></div></details></>}
        {abandon!==null&&<dialog ref={abandonDialog} className={layout.dialog} aria-label="Confirmar abandono" onClose={()=>{setAbandon(null);abandonTrigger.current?.focus();}}>
          <label>Jugador que abandona<select className="form-input" value={abandon} disabled={s.play_mode==='ONLINE'} onChange={e=>setAbandon(Number(e.target.value))}>{s.participants.map(p=><option key={p.position} value={p.position}>{p.name}</option>)}</select></label>
          <p>{s.participants.find(p=>p.position===abandon)?.name} abandona. Su rival gana por abandono.</p><div className={layout.actions}><button className="button-primary" disabled={busy} onClick={()=>act('abandon',abandon)}>Confirmar abandono</button><button className="button-secondary" data-cancel-abandon onClick={()=>abandonDialog.current?.close()}>Cancelar</button></div>
        </dialog>}
      </>}
    </Frame>;
}
