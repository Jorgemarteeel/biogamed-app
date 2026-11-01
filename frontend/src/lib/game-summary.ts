import type { GameHistorySummary } from "@/services/api";

export function gameSummary(game: GameHistorySummary) {
  const total = game.question_ids.length;
  const scoreKnown = game.is_completed && Number.isInteger(game.score) && game.score >= 0
    && (game.content_context !== null || game.score > 0);
  const completeCorrection = scoreKnown && game.content_context !== null && total > 0 && game.score <= total;
  return {
    correct: scoreKnown ? game.score : null,
    total: completeCorrection ? total : null,
    errors: completeCorrection ? total - game.score : null,
  };
}
