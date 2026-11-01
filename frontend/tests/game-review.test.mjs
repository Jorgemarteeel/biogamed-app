import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const filename = fileURLToPath(new URL("../src/lib/game-review.ts", import.meta.url));
const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true },
}).outputText;
const loaded = new Module(filename);
loaded.filename = filename;
loaded.paths = Module._nodeModulePaths(path.dirname(filename));
loaded._compile(compiled, filename);
const { describeContentContext, historyReviewItems, liveReviewItems } = loaded.exports;

test("historical Trivial review uses saved text, options and correction", () => {
  const game = { question_ids: [7], answer_logs: [{ question_id: 7, question_type: "TRIVIAL",
    question_text: "Enunciado guardado", options: ["Antes A", "Antes B"],
    selected_index: 0, correct_option_index: 1, is_correct: false }] };
  assert.deepEqual(historyReviewItems(game), [{ questionId: 7, position: 1, text: "Enunciado guardado",
    isCorrect: false, selectedAnswer: "Antes A", correctAnswer: "Antes B", acceptedAnswers: [] }]);
});

test("missing historical answer text or solution remains unavailable", () => {
  const game = { question_ids: [3, 7], answer_logs: [{ question_id: 7, question_type: "TRIVIAL",
    question_text: "Pregunta antigua", options: null,
    selected_index: 0, correct_option_index: null, is_correct: false }] };
  assert.deepEqual(historyReviewItems(game)[0], { questionId: 7, position: 2, text: "Pregunta antigua",
    isCorrect: false, selectedAnswer: null, correctAnswer: null, acceptedAnswers: [] });
  assert.equal(describeContentContext(null), null);
});

test("historical Pasapalabra shows the stored answer and accepted solutions", () => {
  const game = { question_ids: [8], answer_logs: [{ question_id: 8, question_type: "PASAPALABRA",
    question_text: "Empieza por A", text_answer: "Aorta", exact_word: "aorta",
    accepted_answers: ["arteria aorta"], is_correct: true }] };
  assert.deepEqual(historyReviewItems(game)[0], { questionId: 8, position: 1, text: "Empieza por A",
    isCorrect: true, selectedAnswer: "Aorta", correctAnswer: "aorta",
    acceptedAnswers: ["arteria aorta"] });
});

test("live result keeps the current Trivial correction presentation", () => {
  const session = { questions: [{ id: 1, text: "Pregunta", options: ["A", "B"] }] };
  const result = { corrections: [{ question_id: 1, selected_index: 0, correct_option_index: 1, is_correct: false }] };
  assert.deepEqual(liveReviewItems(session, result), [{ questionId: 1, position: 1, text: "Pregunta",
    isCorrect: false, selectedAnswer: "A", correctAnswer: "B" }]);
});

test("context labels use the classification saved when the game started", () => {
  const context = { selection: { category_id: 3, category_name: "Linfocito", difficulty: 2, difficulty_unknown: false },
    questions: [{ question_id: 7, category_id: 3, category_name: "Linfocito", difficulty: 2 }] };
  assert.deepEqual(describeContentContext(context), { category: "Linfocito", difficulty: "Nivel 2" });
});
