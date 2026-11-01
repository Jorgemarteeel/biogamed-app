import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

// Render the real components with the Next navigation/image wrappers replaced
// by plain HTML elements; no browser runner or new dependency is needed.
const originalLoad = Module._load;
let BestMarkCard;
let ProgressContent;
try {
  Module._load = function (request, parent, isMain) {
    if (request === "next/link") return function MockLink({ href, children, ...props }) { return React.createElement("a", { href, ...props }, children); };
    if (request === "next/image") return function MockImage({ src, alt, ...props }) { return React.createElement("img", { src, alt, ...props }); };
    if (request === "@/lib/topic-presentation") return { topicIllustration: (name) => name === "Linfocito" ? "/topics/linfocito.png" : "/topics/generic.svg" };
    if (request === "@/components/BestMarkCard") return BestMarkCard;
    return originalLoad.call(this, request, parent, isMain);
  };
  function load(file) {
    const filename = fileURLToPath(new URL(`../src/components/${file}`, import.meta.url));
    const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    }).outputText;
    const loaded = new Module(filename);
    loaded.filename = filename;
    loaded.paths = Module._nodeModulePaths(path.dirname(filename));
    loaded._compile(compiled, filename);
    return loaded.exports.default;
  }
  BestMarkCard = load("BestMarkCard.tsx");
  ProgressContent = load("ProgressContent.tsx");
} finally {
  Module._load = originalLoad;
}

const counts = { started: 3, completed: 2, unfinished: 1 };
const progress = (marks) => ({ ...counts, by_mode: {
  TRIVIAL: counts, PASAPALABRA: { started: 0, completed: 0, unfinished: 0 },
}, best_marks: marks });
const mark = (overrides = {}) => ({
  game_mode: "TRIVIAL", topic_id: 6, topic_name: "Linfocito",
  category_id: 3, category_name: "Linfocito", category_name_source: "historical",
  difficulty: 2, total_questions: 10, best_score: 4, session_id: 11,
  started_at: "2026-10-30T12:06:20Z", valid_results: 1, tied_best_results: 1,
  ...overrides,
});
const render = (marks) => renderToStaticMarkup(React.createElement(ProgressContent, { progress: progress(marks) }));

test("empty best marks retain the activity summary", () => {
  const html = render([]);
  assert.match(html, /Resumen de actividad/);
  assert.match(html, /Iniciadas/);
  assert.match(html, /Mis mejores marcas/);
  assert.match(html, /Todavía no hay partidas con clasificación suficiente/);
  assert.doesNotMatch(html, /Todavía no has iniciado ninguna partida/);
});

test("tied best mark and plural valid results are visible without implying evolution", () => {
  const html = render([mark({ valid_results: 3, tied_best_results: 2 })]);
  assert.match(html, /4 de 10 aciertos/);
  assert.match(html, /3 partidas válidas en este grupo/);
  assert.match(html, /Mejor marca empatada en 2 partidas/);
  assert.match(html, /href="\/partidas\/11"/);
  assert.doesNotMatch(html, /evolución/i);
});

test("one valid result uses singular and does not claim a tie", () => {
  const html = render([mark()]);
  assert.match(html, /1 partida válida en este grupo/);
  assert.doesNotMatch(html, /Mejor marca empatada/);
});

test("historical and current fallback category names keep their provenance", () => {
  const html = render([
    mark({ category_id: 4, category_name: "Macrófago", category_name_source: "historical" }),
    mark({ category_id: 5, category_name: "Jeringuilla", category_name_source: "current", difficulty: 3 }),
    mark({ category_id: 6, category_name: null, category_name_source: null, difficulty: 4 }),
  ]);
  assert.match(html, /Categoría: Macrófago/);
  assert.doesNotMatch(html, /Macrófago \(nombre actual\)/);
  assert.match(html, /Categoría: Jeringuilla \(nombre actual\)/);
  assert.match(html, /Categoría: Categoría 6 \(nombre no disponible\)/);
  assert.match(html, /nombres de temática reflejan el catálogo actual/);
});
