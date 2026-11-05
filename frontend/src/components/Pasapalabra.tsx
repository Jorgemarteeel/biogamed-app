"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import Brand from "@/components/Brand";
import ProfileMenu from "@/components/ProfileMenu";
import api, { type GameAvailability } from "@/services/api";
import { getMatch, sendOperation, newer, questionKey, remaining, type Match, type Player, type Operation } from "@/lib/pasapalabra";
function message(e: unknown) { const status = isAxiosError(e) ? e.response?.status : 0; return status === 404 || status === 403 ? "Esta partida no está disponible para tu cuenta." : status === 401 ? "Tu sesión ha caducado. Inicia sesión para recuperar la partida." : status === 409 ? "La partida ha cambiado. Consulta el estado antes de continuar." : "No se pudo confirmar la operación. Comprueba tu conexión y reintenta."; }
function Frame({ children }: {
    children: React.ReactNode;
}) {
    return <div className="min-h-screen bg-background text-slate-900">
    <header className="site-header">
    <nav className="mx-auto flex max-w-7xl items-center justify-between gap-3 p-5">
    <Brand />
    <ProfileMenu />
    </nav>
    </header>
    <main className="mx-auto max-w-7xl px-4 py-6">
    <Link className="text-link" href="/dashboard">← Volver al panel</Link>
    <h1 className="my-5 text-3xl font-black text-blue-950">Pasapalabra local</h1>{children}</main>
    </div>;
}
export function PasapalabraPrepare({ topicId }: {
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
        pending.current ??= { operation_id: crypto.randomUUID(), topic_id: topicId, guest_name: name.trim(), ...(category ? { category_id: Number(category) } : {}), ...(level === "unknown" ? { difficulty_unknown: true } : level ? { difficulty: Number(level) } : {}) };
        try {
            const r = await api.post('/pasapalabra/local/start', pending.current);
            router.push(`/pasapalabra/${r.data.id}`);
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
    return <Frame>
    <section className="mx-auto max-w-2xl space-y-5 rounded-2xl bg-white p-6">
    <h2 className="text-xl font-bold">Dos jugadores, un dispositivo</h2>
    <p>20 preguntas por jugador · 10 minutos individuales. Se necesitan 40 preguntas distintas. Solo tu resultado se guarda en tu historial personal; el invitado no tiene progreso propio.</p>
    <label className="block">Nombre del invitado<input className="form-input" value={name} disabled={busy || retryStart} onChange={e => setName(e.target.value)} maxLength={255}/>
    </label>
    <label className="block">Categoría<select className="form-input" value={category} disabled={busy || retryStart} onChange={e => { setCategory(e.target.value); setCount(null); }}>
    <option value="">Todas, incluidas sin categoría</option>{categories.map(([id, label]) => <option key={id} value={id!}>{label}</option>)}</select>
    </label>
    <label className="block">Dificultad<select className="form-input" value={level} disabled={busy || retryStart} onChange={e => { setLevel(e.target.value); setCount(null); }}>
    <option value="">Sin filtrar</option>{[...new Set(bank?.combinations.map(c => c.difficulty))].map(v => <option key={v ?? "unknown"} value={v ?? "unknown"}>{v === null ? "Sin clasificar" : `Nivel ${v}`}</option>)}</select>
    </label>
    <p role="status">{count === null ? "Consultando disponibilidad…" : `${count} preguntas disponibles de las 40 necesarias.${count < 40 ? " No hay suficientes: revisa los filtros; no se cambiarán automáticamente." : ""}`}</p>{error && <p role="alert">{error}</p>}<button className="button-secondary" disabled={busy || retryStart} onClick={() => { setCount(null); setError(""); setAttempt(v => v + 1); }}>Volver a consultar disponibilidad</button>
    <button className="button-primary" disabled={busy || (!retryStart && (count === null || count < 40 || !name.trim()))} onClick={start}>{busy ? "Iniciando…" : retryStart ? "Reintentar el mismo inicio" : "Comenzar partida"}</button>
    <p>Recargar o cerrar la pestaña durante el juego no pausa el reloj.</p>
    </section>
    </Frame>;
}
function timeLabel(ms: number) { const seconds = Math.ceil(ms / 1000); return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`; }
function Rosco({ p, s, elapsed }: {
    p: Player;
    s: Match;
    elapsed: number;
}) {
    const active = s.active_participant === p.position;
    const ms = remaining(s, p, elapsed);
    const sec = Math.ceil(ms / 1000);
    const symbols: Record<string, string> = { PENDING: "·", PASSED: "↻", CORRECT: "✓", WRONG: "×" };
    const labels: Record<string, string> = { PENDING: "Pendiente", PASSED: "Pasada", CORRECT: "Acertada", WRONG: "Fallada" };
    return <section className={`min-w-0 rounded-2xl border-2 bg-white p-3 lg:row-start-1 ${p.position === 1 ? "lg:col-start-1" : "lg:col-start-3"} ${active ? "border-sky-700" : "border-slate-200"}`} aria-label={`Rosco de ${p.name}`}>
    <h2 className="break-words text-xl font-bold">{p.name} {active && "· Tu turno"}</h2>
    <p className="text-2xl font-black tabular-nums" aria-label="Tiempo restante">{Math.floor(sec / 60)}:{String(sec % 60).padStart(2, '0')}</p>
    <p>✓ {p.correct} aciertos · × {p.wrong} fallos · {p.pending} pendientes</p>{p.status === "FINISHED" && <p>Finalizado: {p.finish_reason === "TIMEOUT" ? "tiempo agotado" : p.finish_reason === "RESOLVED" ? "preguntas resueltas" : "abandono"}</p>}<ol className="sr-only">{p.slots.map(slot => <li key={slot.number}>{slot.number}: {labels[slot.state]}{active && s.active_question?.number === slot.number ? ", actual" : ""}</li>)}</ol>
    <svg viewBox="0 0 400 400" className="mx-auto w-full max-w-sm" role="img" aria-label={`20 posiciones numeradas de ${p.name}`}>
    <circle cx="200" cy="200" r="155" fill="none" stroke="#e2e8f0" strokeWidth="4"/>{p.slots.map((q, i) => {
            const angle = i * Math.PI / 10 - Math.PI / 2;
            const x = 200 + 155 * Math.cos(angle), y = 200 + 155 * Math.sin(angle);
            const current = active && s.active_question?.number === q.number;
            return <g key={q.number} aria-label={`${q.number}: ${labels[q.state]}${current ? ", actual" : ""}`}>
            <title>{`${q.number}: ${labels[q.state]}${current ? ", actual" : ""}`}</title>
            <circle cx={x} cy={y} r="21" fill={q.state === "CORRECT" ? "#166534" : q.state === "WRONG" ? "#991b1b" : q.state === "PASSED" ? "#92400e" : "#1e3a8a"} stroke={current ? "#0284c7" : "white"} strokeWidth={current ? 7 : 2}/>
            <text x={x} y={y + 1} textAnchor="middle" fill="white" fontSize="15" fontWeight="bold">{q.number}</text>
            <text x={x} y={y + 15} textAnchor="middle" fill="white" fontSize="12">{symbols[q.state]}</text>
            </g>;
        })}<text x="200" y="197" textAnchor="middle" fill="#1e3a8a" fontSize="20" fontWeight="bold">{active ? "Turno activo" : "Pasapalabra"}</text>
    <text x="200" y="223" textAnchor="middle" fill="#475569" fontSize="14">20 preguntas</text>
    </svg>
    </section>;
}
export function PasapalabraGame({ id }: {
    id: number;
}) {
    const [state, setState] = useState<Match | null>(null);
    const latest = useRef<Match | null>(null);
    const [text, setText] = useState("");
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);
    const [uncertain, setUncertain] = useState(false);
    const pending = useRef<Operation | null>(null);
    const lock = useRef(false);
    const [abandon, setAbandon] = useState<number | null>(null);
    const [elapsed, setElapsed] = useState(0);
    const received = useRef(0);
    const mounted = useRef(false);
    function accept(s: Match) {
        if (!mounted.current || !newer(latest.current, s))
            return;
        if (latest.current && questionKey(latest.current) !== questionKey(s))
            setText("");
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
            fetching = true;
            try {
                const response = await getMatch(id);
                if (live)
                    accept(response);
            }
            catch (e) {
                if (mounted.current)
                    setError(message(e));
            }
            finally {
                fetching = false;
                if (live && latest.current?.status !== "FINISHED")
                    timer = setTimeout(poll, 1000);
            }
        }
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
            if (!q)
                return;
            pending.current = { kind, body: { operation_id: crypto.randomUUID(), expected_version: s.version, participant: participant ?? q.participant, ...(kind === 'abandon' ? {} : { number: q.number }), ...(kind === 'answer' ? { text_answer: text } : {}) } };
        }
        lock.current = true;
        setBusy(true);
        setError("");
        try {
            const next = await sendOperation(id, pending.current);
            pending.current = null;
            setUncertain(false);
            setAbandon(null);
            accept(next);
        }
        catch (e) {
            setError(message(e));
            if (isAxiosError(e) && e.response && e.response.status < 500 && e.response.status !== 408) {
                pending.current = null;
                setUncertain(false);
                try {
                    const response = await getMatch(id);
                    if (mounted.current)
                        accept(response);
                }
                catch { /* polling will retry */ }
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
    const corrections = s?.participants.flatMap(p => p.resolved.map(r => ({ ...r, name: p.name, position: p.position }))) ?? [];
    return <Frame>{error && <p role="alert" className="notice-error my-4">{error} <Link href="/login">Iniciar sesión</Link>
        </p>}{!s ? <p role="status">{error ? "No se pudo cargar la partida. Revisa el aviso anterior o vuelve al panel." : "Cargando partida…"}</p> : <>
        <div className="flex flex-col lg:grid lg:grid-cols-[1fr_1.2fr_1fr] lg:gap-4">
        <div className="order-2 grid gap-5 lg:contents">
        <Rosco p={s.participants[0]} s={s} elapsed={elapsed}/>
        <Rosco p={s.participants[1]} s={s} elapsed={elapsed}/>
        </div>
        <section className="order-1 my-5 min-w-0 rounded-2xl border bg-white p-5 lg:col-start-2 lg:row-start-1 lg:my-0" aria-label="Pregunta y controles">
        <div className="mb-4 grid grid-cols-2 gap-3 lg:hidden" aria-label="Relojes de ambos jugadores">{s.participants.map(p => <p key={p.position} className="min-w-0 break-words text-sm">
            <strong>{p.name}</strong>
            <br />{timeLabel(remaining(s, p, elapsed))}{s.active_participant === p.position ? " · Turno activo" : ""}</p>)}</div>
        <p className="text-sm">· Pendiente · ↻ Pasada · ✓ Acertada · × Fallada · Borde azul: actual</p>{s.status === "FINISHED" ? <>
            <h2 className="my-3 break-words text-2xl font-bold">{s.winner_position ? `Gana ${s.participants.find(p => p.position === s.winner_position)?.name}` : "Empate"}</h2>
            <p>{s.outcome === "ABANDONMENT" ? "Victoria por abandono del rival" : "Finalización normal"}</p>
            <Link className="button-primary mr-3 inline-flex" href={`/partidas/${s.personal_session_id}`}>Historial personal del anfitrión</Link>
            <Link className="text-link" href="/dashboard">Preparar otra partida</Link>
            </> : q && <>
            <h2 className="my-3 break-words text-xl font-bold">Turno de {s.participants.find(p => p.position === q.participant)?.name} · Pregunta {q.number}</h2>
            <p className="my-4 break-words text-lg leading-8" aria-live="polite">{q.text}</p>
            <form onSubmit={e => {
                    e.preventDefault();
                    if (text.trim() && !uncertain)
                        void act('answer');
                }}>
            <label htmlFor="word" className="form-label">Respuesta</label>
            <input id="word" className="form-input" autoComplete="off" value={text} onChange={e => setText(e.target.value)} readOnly={busy || uncertain}/>
            <div className="my-4 flex flex-wrap gap-3">
            <button className="button-primary" disabled={busy || uncertain || !text.trim()}>Responder</button>
            <button type="button" className="button-secondary" disabled={busy || uncertain} onClick={() => act('pass')}>Pasapalabra</button>
            </div>
            </form>
            <p>El reloj continúa aunque cierres esta pestaña.</p>
            <button className="text-link my-4" disabled={busy || uncertain} onClick={() => setAbandon(q.participant)}>Abandonar…</button>{abandon !== null && <div role="alert" className="notice-warning">
                <label>Jugador que abandona<select className="form-input" value={abandon} onChange={e => setAbandon(Number(e.target.value))}>{s.participants.map(p => <option key={p.position} value={p.position}>{p.name}</option>)}</select>
                </label>
                <p>{s.participants.find(p => p.position === abandon)?.name} abandona. Su rival gana por abandono.</p>
                <button className="button-primary" disabled={busy} onClick={() => act('abandon', abandon)}>Confirmar abandono</button>
                <button className="button-secondary" onClick={() => setAbandon(null)}>Cancelar</button>
                </div>}</>}{uncertain && <button className="button-primary" disabled={busy} onClick={() => act(pending.current!.kind)}>Reintentar la misma acción</button>}</section>
        </div>
        <section aria-label="Correcciones" className="rounded-2xl bg-white p-5">
        <h2 className="text-xl font-bold">Respuestas resueltas</h2>{corrections.length === 0 ? <p>Aún no hay respuestas corregidas.</p> : corrections.map(r => <p key={`${r.position}-${r.number}`} className="my-3 break-words">{r.is_correct ? '✓' : '×'} {r.name} · {r.number}: {r.text_answer}. Solución: <strong>{r.exact_word}</strong>
            </p>)}</section>
        </>}</Frame>;
}
