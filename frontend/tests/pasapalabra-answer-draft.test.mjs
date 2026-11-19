import { afterEach, test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const file = fileURLToPath(new URL("../src/lib/pasapalabra-answer-draft.ts", import.meta.url));
const loaded = new Module(file);
loaded._compile(ts.transpileModule(fs.readFileSync(file, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText, file);
const { readAnswerDraft, saveAnswerDraft } = loaded.exports;

const state = { id: 3, self_position: 0, status: "RUNNING", version: 8, active_question: { participant: 0, number: 4 } };
function startTab() {
  const values = new Map();
  global.window = { sessionStorage: {
    getItem: (key) => values.get(key), setItem: (key, value) => values.set(key, value), removeItem: (key) => values.delete(key),
  }};
}
afterEach(() => { delete global.window; });

test("resume restores unsubmitted text only for the same match, player, question and version", () => {
  startTab();
  saveAnswerDraft(state, "Linfocito");
  assert.equal(readAnswerDraft({ ...state, id: 4 }), "");
  assert.equal(readAnswerDraft({ ...state, server_now: "later" }), "Linfocito");
  for (const change of [{ self_position: 1 }, { version: 9 }, { active_question: null }, { status: "FINISHED" }]) {
    saveAnswerDraft(state, "Linfocito");
    assert.equal(readAnswerDraft({ ...state, ...change }), "");
    assert.equal(readAnswerDraft(state), "");
  }
});

test("clearing the input and remounting never restore an earlier word", () => {
  startTab();
  saveAnswerDraft(state, "Linfocito");
  saveAnswerDraft(state, "");
  assert.equal(readAnswerDraft(state), "");
});
