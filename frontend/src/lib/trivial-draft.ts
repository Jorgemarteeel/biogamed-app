import type { GameSessionStart } from "@/services/api";

export interface TrivialDraft {
  questionIndex: number;
  answers: Record<number, number>;
  exposure: Record<number, number>;
}

const keyFor = (id: number) => `biogamed-trivial-draft:${id}`;

// Load only after the API has authorized access to this session and returned its copy.
export function readTrivialDraft(session: GameSessionStart): TrivialDraft {
  const draft: TrivialDraft = { questionIndex: 0, answers: {}, exposure: {} };
  try {
    const saved = JSON.parse(window.sessionStorage.getItem(keyFor(session.session_id)) ?? "null");
    if (!saved) return draft;
    if (Number.isInteger(saved.questionIndex) && saved.questionIndex >= 0 && saved.questionIndex < session.questions.length) {
      draft.questionIndex = saved.questionIndex;
    }
    for (const question of session.questions) {
      const answer = saved.answers?.[question.id];
      const time = saved.exposure?.[question.id];
      if (Number.isInteger(answer) && answer >= 0 && answer < (question.options?.length ?? 0)) draft.answers[question.id] = answer;
      if (Number.isInteger(time) && time >= 0 && time <= 2147483647) draft.exposure[question.id] = time;
    }
  } catch { /* a blocked store or corrupted draft does not stop the game */ }
  return draft;
}

export function saveTrivialDraft(id: number, draft: TrivialDraft) {
  try { window.sessionStorage.setItem(keyFor(id), JSON.stringify(draft)); }
  catch { /* the running game still retains its state in memory */ }
}

export function clearTrivialDraft(id: number) {
  try { window.sessionStorage.removeItem(keyFor(id)); }
  catch { /* the server has already recorded the result */ }
}
