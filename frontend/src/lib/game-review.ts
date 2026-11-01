import type { GameContentContext, GameHistoryDetail, GameResult, GameSessionStart } from "@/services/api";

export interface ReviewItem {
  questionId: number;
  position: number | null;
  text: string;
  isCorrect: boolean | null;
  selectedAnswer: string | null;
  correctAnswer: string | null;
  acceptedAnswers?: string[];
}

export function describeContentContext(context: GameContentContext | null): { category: string; difficulty: string } | null {
  if (!context) return null;
  const categories = [...new Set(context.questions.map((item) =>
    item.category_id === null ? "Sin categoría" : item.category_name || `Categoría ${item.category_id}`))];
  const category = context.selection.category_id !== null
    ? context.selection.category_name || `Categoría ${context.selection.category_id}`
    : categories.length === 1 ? categories[0] : categories.length > 1
      ? `Varias categorías${categories.includes("Sin categoría") ? ", incluidas preguntas sin categoría" : ""}`
      : "Categoría no disponible";
  const difficulties = [...new Set(context.questions.map((item) => item.difficulty))];
  const difficulty = context.selection.difficulty !== null
    ? `Nivel ${context.selection.difficulty}`
    : context.selection.difficulty_unknown ? "Dificultad sin clasificar"
      : difficulties.length === 1 ? difficulties[0] === null ? "Dificultad sin clasificar" : `Nivel ${difficulties[0]}`
        : difficulties.length > 1 ? `Dificultad mixta${difficulties.includes(null) ? ", incluidas preguntas sin clasificar" : ""}`
          : "Dificultad no disponible";
  return { category, difficulty };
}

export function liveReviewItems(session: GameSessionStart, result: GameResult): ReviewItem[] {
  return session.questions.map((question, index) => {
    const correction = result.corrections.find((item) => item.question_id === question.id);
    return {
      questionId: question.id,
      position: index + 1,
      text: question.text,
      isCorrect: correction?.is_correct ?? null,
      selectedAnswer: correction?.selected_index === null || correction?.selected_index === undefined
        ? null : question.options?.[correction.selected_index] ?? null,
      correctAnswer: correction?.correct_option_index === null || correction?.correct_option_index === undefined
        ? null : question.options?.[correction.correct_option_index] ?? null,
    };
  });
}

export function historyReviewItems(game: GameHistoryDetail): ReviewItem[] {
  return game.answer_logs.map((answer) => ({
    questionId: answer.question_id,
    position: game.question_ids.indexOf(answer.question_id) + 1 || null,
    text: answer.question_text,
    isCorrect: answer.is_correct,
    selectedAnswer: answer.question_type === "TRIVIAL"
      ? answer.selected_index === null ? "Sin respuesta registrada" : answer.options?.[answer.selected_index] ?? null
      : answer.text_answer ?? "Sin respuesta registrada",
    correctAnswer: answer.question_type === "TRIVIAL"
      ? answer.correct_option_index === null ? null : answer.options?.[answer.correct_option_index] ?? null
      : answer.exact_word,
    acceptedAnswers: answer.question_type === "PASAPALABRA" ? answer.accepted_answers ?? [] : [],
  })).sort((a, b) => (a.position ?? Infinity) - (b.position ?? Infinity));
}
