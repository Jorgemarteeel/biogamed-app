import type { Match } from "@/lib/pasapalabra";

const key = (state: Match) => `biogamed-pasapalabra-answer:${state.id}`;

function turnKey(state: Match): string | null {
  const question = state.active_question;
  if (state.status !== "RUNNING" || !question || state.self_position === undefined) return null;
  return `${state.self_position}:${state.version}:${question.participant}:${question.number}`;
}

// Use only a state already authorized for this account by the matches API.
export function readAnswerDraft(state: Match): string {
  try {
    const stored = JSON.parse(window.sessionStorage.getItem(key(state)) ?? "null");
    const turn = turnKey(state);
    if (turn && stored?.turn === turn && typeof stored.text === "string" && stored.text.length <= 2000) return stored.text;
    window.sessionStorage.removeItem(key(state));
  } catch { /* play remains available without tab storage */ }
  return "";
}

export function saveAnswerDraft(state: Match, text: string) {
  try {
    const turn = turnKey(state);
    if (turn && text && text.length <= 2000) window.sessionStorage.setItem(key(state), JSON.stringify({ turn, text }));
    else window.sessionStorage.removeItem(key(state));
  } catch { /* the input still retains its value in memory */ }
}
