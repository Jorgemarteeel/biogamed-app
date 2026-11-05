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
        text: string;
        text_answer: string;
        exact_word: string;
        is_correct: boolean;
    }[];
}
export interface Match {
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
export async function getMatch(id: number): Promise<Match> { return (await api.get(`/pasapalabra/matches/${id}`)).data; }
export async function sendOperation(id: number, operation: Operation): Promise<Match> { return (await api.post(`/pasapalabra/matches/${id}/${operation.kind}`, operation.body)).data.state; }
export function remaining(s: Match, p: Player, elapsed: number) { return s.active_participant === p.position && s.turn_deadline_at ? Math.max(0, Date.parse(s.turn_deadline_at) - Date.parse(s.server_now) - elapsed) : p.remaining_ms; }
