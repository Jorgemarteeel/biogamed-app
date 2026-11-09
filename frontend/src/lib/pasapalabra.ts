import api from "@/services/api";
export interface Player {
    position: number;
    name: string;
    registered: boolean;
    remaining_ms: number;
    correct: number;
    wrong: number;
    pending: number;
    status: string;
    finish_reason: string | null;
    slots: {
        number: number;
        state: string;
    }[];
    resolved: {
        number: number;
        resolution_order: number;
        text: string;
        text_answer: string;
        exact_word: string;
        is_correct: boolean;
    }[];
}
export interface Match {
    academic?: import("@/services/api").AcademicContext | null;
    play_mode?: "LOCAL" | "ONLINE";
    self_position?: number;
    id: number;
    version: number;
    server_now: string;
    turn_deadline_at: string | null;
    active_participant: number | null;
    active_question: {
        participant: number;
        number: number;
        text: string;
        letter: string;
    } | null;
    participants: Player[];
    status: string;
    outcome: string | null;
    winner_position: number | null;
    personal_session_id: number;
}
export interface Operation {
    kind: "answer" | "pass" | "abandon";
    body: {
        operation_id: string;
        expected_version: number;
        participant: number;
        number?: number;
        text_answer?: string;
    };
}
export function newer(current: Match | null, incoming: Match) { return !current || incoming.version > current.version || incoming.version === current.version && Date.parse(incoming.server_now) >= Date.parse(current.server_now); }
export const questionKey = (s: Match) => s.active_question ? `${s.active_question.participant}:${s.active_question.number}` : "finished";
export async function getMatch(id: number): Promise<Match> { return (await api.get(`/pasapalabra/matches/${id}`, {timeout:10000})).data; }
export async function sendOperation(id: number, operation: Operation): Promise<Match> { return (await api.post(`/pasapalabra/matches/${id}/${operation.kind}`, operation.body, {timeout:10000})).data.state; }
export function remaining(s: Match, p: Player, elapsed: number) { return s.active_participant === p.position && s.turn_deadline_at ? Math.max(0, Date.parse(s.turn_deadline_at) - Date.parse(s.server_now) - elapsed) : p.remaining_ms; }

export function resolvedInOrder(s: Match) {
    return s.participants.filter(p => s.play_mode !== "ONLINE" || p.position === s.self_position).flatMap(p => (p.resolved??[]).map(r => ({ ...r, name: p.name, position: p.position })))
        .sort((a, b) => b.resolution_order - a.resolution_order);
}
export function startsCelebration(previous: Match | null, next: Match) {
    return previous?.status === "RUNNING" && next.status === "FINISHED" && next.outcome === "NORMAL";
}
