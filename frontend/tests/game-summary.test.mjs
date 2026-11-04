import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const filename = fileURLToPath(new URL("../src/lib/game-summary.ts", import.meta.url));
const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
const loaded = new Module(filename);
loaded.filename = filename;
loaded.paths = Module._nodeModulePaths(path.dirname(filename));
loaded._compile(compiled, filename);
const { gameSummary } = loaded.exports;

test("completed classified game has a definitive answer per question", () => {
  assert.deepEqual(gameSummary({ is_completed: true, score: 2, question_ids: [1, 2, 3], content_context: {} }), { correct: 2, errors: 1, total: 3 });
});

test("unfinished and legacy games do not invent errors or zero scores", () => {
  assert.deepEqual(gameSummary({ is_completed: false, score: 0, question_ids: [1], content_context: {} }), { correct: null, errors: null, total: null });
  assert.deepEqual(gameSummary({ is_completed: true, score: 0, question_ids: [1], content_context: null }), { correct: null, errors: null, total: null });
  assert.deepEqual(gameSummary({ is_completed: true, score: 3, question_ids: [1, 2, 3, 4], content_context: null }), { correct: 3, errors: null, total: null });
});

test("shared matches preserve pending questions separately from mistakes, including abandonment", () => {
  for (const is_completed of [true, false]) {
    assert.deepEqual(gameSummary({ shared_match_id: 7, is_completed, score: 3,
      question_ids: Array.from({ length: 20 }, (_, i) => i + 1), wrong_count: 2, pending_count: 15 }),
    { correct: 3, errors: 2, total: 20 });
  }
});
