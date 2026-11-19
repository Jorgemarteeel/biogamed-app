import { afterEach, test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const file = fileURLToPath(new URL("../src/lib/trivial-draft.ts", import.meta.url));
const compiled = ts.transpileModule(fs.readFileSync(file, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText;
const loaded = new Module(file);
loaded._compile(compiled, file);
const { clearTrivialDraft, readTrivialDraft, saveTrivialDraft } = loaded.exports;

const game = { session_id: 25, questions: [{ id: 4, options: ["A", "B"] }, { id: 8, options: ["C", "D"] }] };
const empty = { questionIndex: 0, answers: {}, exposure: {} };
function useStorage(values = new Map()) {
  global.window = { sessionStorage: {
    getItem: (key) => values.get(key), setItem: (key, data) => values.set(key, data), removeItem: (key) => values.delete(key),
  }};
  return values;
}
afterEach(() => { delete global.window; });

test("a tab reload restores the original game's selected options, position and elapsed time", () => {
  const values = useStorage();
  const draft = { questionIndex: 1, answers: { 4: 0, 8: 1 }, exposure: { 4: 1300 } };
  saveTrivialDraft(game.session_id, draft);
  useStorage(values);
  assert.deepEqual(readTrivialDraft(game), draft);
  assert.deepEqual(readTrivialDraft({ ...game, session_id: 26 }), empty);
  clearTrivialDraft(game.session_id);
  assert.deepEqual(readTrivialDraft(game), empty);
});

test("drafts discard unknown questions, invalid choices, positions and elapsed times", () => {
  useStorage();
  saveTrivialDraft(game.session_id, { questionIndex: 9, answers: { 4: 0, 8: 2, 10: 0 }, exposure: { 4: -7, 8: 2.9 } });
  assert.deepEqual(readTrivialDraft(game), { ...empty, answers: { 4: 0 } });
});

test("malformed or unavailable storage leaves the game usable", () => {
  useStorage().set("biogamed-trivial-draft:25", "{");
  assert.deepEqual(readTrivialDraft(game), empty);
  global.window = { get sessionStorage() { throw Error("blocked"); } };
  assert.deepEqual(readTrivialDraft(game), empty);
  assert.doesNotThrow(() => saveTrivialDraft(game.session_id, empty));
  assert.doesNotThrow(() => clearTrivialDraft(game.session_id));
});
