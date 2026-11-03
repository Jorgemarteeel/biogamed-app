import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

function load(relative) {
  const filename = fileURLToPath(new URL(relative, import.meta.url));
  const loaded = new Module(filename);
  loaded.filename = filename;
  loaded.paths = Module._nodeModulePaths(path.dirname(filename));
  loaded._compile(ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText, filename);
  return loaded.exports;
}
const review = load("../src/lib/game-review.ts");
const summary = load("../src/lib/game-summary.ts");
let viewState = [], cursor = 0;
let HistoryView, SummaryCard;
const original = Module._load;
try {
  Module._load = function (request, parent, main) {
    if (request === "react") return { ...React, useEffect() {}, useState: () => [viewState[cursor++], () => {}] };
    if (request === "next/navigation") return { useRouter: () => ({}) };
    if (request === "next/link") return function Link({ href, children, ...props }) { return React.createElement("a", { href, ...props }, children); };
    if (request === "next/image") return function Image({ src, alt }) { return React.createElement("img", { src, alt }); };
    if (request === "@/lib/game-review") return review;
    if (request === "@/lib/game-summary") return summary;
    if (request === "@/lib/topic-presentation") return { topicIllustration: () => "/generic.svg" };
    if (request === "@/services/api") return {};
    if (request === "@/components/Brand" || request === "@/components/ProfileMenu") return () => null;
    if (request === "@/components/GameReview") return load("../src/components/GameReview.tsx").default;
    return original.call(this, request, parent, main);
  };
  HistoryView = load("../src/components/GameHistoryView.tsx").default;
  SummaryCard = load("../src/components/GameSummaryCard.tsx").default;
} finally { Module._load = original; }

const game = {
  id: 7, topic_id: 1, game_mode: "TRIVIAL", question_ids: [9], score: 1,
  created_at: "2026-11-03T12:00:00Z", is_completed: true, question_content_source: "session_start",
  content_context: { topic_name: "Tema original", selection: { category_id: 3, category_name: "Categoría original", difficulty: 2, difficulty_unknown: false },
    questions: [{ question_id: 9, category_id: 3, category_name: "Categoría original", difficulty: 2 }] },
  answer_logs: [{ question_id: 9, question_text: "Enunciado original", question_type: "TRIVIAL", options: ["Original A", "Original B"], selected_index: 1, correct_option_index: 1, is_correct: true }],
};
function history(data) {
  cursor = 0;
  viewState = ["ready", data, "Tema cambiado del catálogo", 0];
  return renderToStaticMarkup(React.createElement(HistoryView, { sessionId: data.id }));
}
test("history and cards prefer stored labels and saved answer content over current catalog", () => {
  const html = history(game);
  assert.match(html, /Tema original/);
  assert.doesNotMatch(html, /Tema cambiado del catálogo/);
  assert.match(html, /Enunciado original/);
  assert.match(html, /Original B/);
  assert.match(html, /tal como estaban al iniciarse/);
  const card = renderToStaticMarkup(React.createElement(SummaryCard, { game, topicName: "Tema cambiado del catálogo" }));
  assert.match(card, /Tema original/);
  assert.doesNotMatch(card, /Tema cambiado del catálogo|nombre original no registrado/);
});
test("legacy history states provenance and does not fabricate an original version", () => {
  const html = history({ ...game, question_content_source: "legacy", content_context: null });
  assert.match(html, /Tema cambiado del catálogo/);
  assert.match(html, /nombre original no registrado/);
  assert.match(html, /detalles guardados al corregir/);
  assert.doesNotMatch(html, /tal como estaban al iniciarse/);
  const open = history({ ...game, question_content_source: "legacy", content_context: null, is_completed: false, answer_logs: [] });
  assert.match(open, /No puede corregirse con garantías/);
  assert.doesNotMatch(open, /Enunciado original|Original B/);
});
