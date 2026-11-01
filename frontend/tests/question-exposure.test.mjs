import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const filename = fileURLToPath(new URL("../src/lib/question-exposure.ts", import.meta.url));
const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true },
}).outputText;
const loaded = new Module(filename);
loaded.filename = filename;
loaded.paths = Module._nodeModulePaths(path.dirname(filename));
loaded._compile(compiled, filename);
const { QuestionExposure } = loaded.exports;

test("navigation and revisits accumulate only the displayed question", () => {
  let clock = 0;
  const timer = new QuestionExposure(() => clock);
  timer.show(1, true);
  clock = 100;
  timer.show(2, true);
  clock = 160;
  timer.show(1, true);
  clock = 200;
  timer.stop();
  assert.equal(timer.milliseconds(1), 140);
  assert.equal(timer.milliseconds(2), 60);
});

test("hidden tab and repeated events do not duplicate exposure", () => {
  let clock = 0;
  const timer = new QuestionExposure(() => clock);
  timer.show(1, true);
  timer.show(1, true);
  clock = 50;
  timer.setVisible(false);
  clock = 500;
  timer.setVisible(false);
  timer.setVisible(true);
  clock = 530;
  timer.stop();
  timer.stop();
  assert.equal(timer.milliseconds(1), 80);
});

test("sending freezes a snapshot; failed send resumes without network wait", () => {
  let clock = 0;
  const timer = new QuestionExposure(() => clock);
  timer.show(1, true);
  clock = 100;
  timer.stop();
  const pendingPayload = [{ question_id: 1, selected_index: 0, response_time_ms: timer.milliseconds(1) }];
  clock = 1000;
  timer.stop();
  assert.equal(timer.milliseconds(1), 100);
  assert.equal(pendingPayload[0].response_time_ms, 100);
  timer.resume(true);
  timer.resume(true);
  clock = 1025;
  timer.stop();
  assert.equal(timer.milliseconds(1), 125);
  assert.equal(pendingPayload[0].response_time_ms, 100);
});
