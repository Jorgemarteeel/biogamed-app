import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";
import React from "react";
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
const client = load("../src/services/api.ts");
test("authenticated creation uses category route; topic selector loads all pages without mode filter", async () => {
  global.window = { localStorage: { getItem: () => "demo-token" } };
  const adapter = client.default.defaults.adapter;
  const calls = [];
  client.default.defaults.adapter = async (config) => {
    calls.push(config);
    assert.equal(config.headers.Authorization, "Bearer demo-token");
    return { status: 200, headers: {}, config, data: config.method === "post" ? { id: 42 }
      : Array.from({ length: config.params.skip === 0 ? 100 : 1 }, (_, i) => ({ id: config.params.skip + i + 1, name: "Topic" })) };
  };
  try {
    assert.equal((await client.getQuestionTopics()).length, 101);
    assert.deepEqual(calls.map((c) => c.params), [{ skip: 0, limit: 100 }, { skip: 100, limit: 100 }]);
    const payload = { text: "Ficticia", topic_id: 101, difficulty: null, question_type: "TRIVIAL", options: ["A", "B", "C", "D"], correct_option_index: 0 };
    assert.equal((await client.createCategoryQuestion(3, 7, 9, payload)).id, 42);
    assert.equal(calls[2].url, "/subjects/3/blocks/7/categories/9/questions");
    assert.deepEqual(JSON.parse(calls[2].data), payload);
  } finally { client.default.defaults.adapter = adapter; delete global.window; }
});
function harness() {
  const states = []; let cursor = 0;
  const effects = [], calls = [];
  let resolve, reject;
  const hooks = { ...React,
    useState(initial) { const i = cursor++; if (!(i in states)) states[i] = initial; return [states[i], (v) => { states[i] = typeof v === "function" ? v(states[i]) : v; }]; },
    useRef(initial) { const i = cursor++; return states[i] ??= { current: initial }; },
    useEffect(effect) { const i = cursor++; if (!(i in states)) { states[i] = true; effects.push(effect); } },
  };
  const original = Module._load; let Form;
  try {
    Module._load = function (request, parent, main) {
      if (request === "react") return hooks;
      if (request === "@/components/CreateContentPanel") return () => null;
      if (request === "@/services/api") return {
        getQuestionTopics: async () => [{ id: 19, name: "Tema API" }],
        createCategoryQuestion: (...args) => { calls.push(args); return new Promise((yes, no) => { resolve = yes; reject = no; }); },
      };
      return original.call(this, request, parent, main);
    };
    Form = load("../src/components/CreateQuestionForm.tsx").default;
  } finally { Module._load = original; }
  let refreshed = 0;
  const render = () => { cursor = 0; return Form({ subjectId: 3, blockId: 7, categoryId: 9, mode: "TRIVIAL", level: "2", onRefresh: () => refreshed++ }); };
  function all(node) { return !node || typeof node !== "object" ? [] : [node, ...React.Children.toArray(node.props?.children).flatMap(all)]; }
  const find = (predicate) => all(render()).find(predicate);
  const change = (id, value) => find((n) => n.props?.id === id).props.onChange({ target: { value } });
  return { render, find, change, calls, effects, resolve: (v) => resolve(v), reject: (e) => reject(e), get refreshed() { return refreshed; } };
}
test("form preserves server error fields, blocks double submit, omits inactive mode fields and confirms excluded creation", async () => {
  const h = harness(); h.render(); h.effects.forEach((e) => e()); await Promise.resolve();
  h.change("create-topic", "19"); h.change("create-text", "Pregunta ficticia");
  for (let i = 0; i < 4; i++) h.change(`create-option-${i}`, `Opción ${i}`);
  h.change("create-correct", "2");
  const submit = () => h.find((n) => n.type === "form").props.onSubmit({ preventDefault() {} });
  const pending = submit(); await submit(); assert.equal(h.calls.length, 1);
  assert.deepEqual(h.calls[0][3], { topic_id: 19, text: "Pregunta ficticia", difficulty: null,
    question_type: "TRIVIAL", options: ["Opción 0", "Opción 1", "Opción 2", "Opción 3"], correct_option_index: 2 });
  h.reject({ isAxiosError: true, response: { status: 422, data: { detail: "Error ficticio de servidor" } } }); await pending;
  assert.equal(h.find((n) => n.props?.id === "create-text").props.value, "Pregunta ficticia");
  assert.match(h.find((n) => n.props?.role === "alert").props.children, /Error ficticio/);
  h.change("create-mode", "PASAPALABRA"); h.change("create-letter", "L"); h.change("create-word", "Linfocito");
  h.change("create-alternatives", "Glóbulo blanco\nLeucocito");
  const success = submit();
  assert.deepEqual(h.calls[1][3], { topic_id: 19, text: "Pregunta ficticia", difficulty: null, question_type: "PASAPALABRA", letter: "L", exact_word: "Linfocito", accepted_answers: ["Glóbulo blanco", "Leucocito"] });
  h.resolve({ id: 81, question_type: "PASAPALABRA", difficulty: null, topic: { name: "Tema API" } }); await success;
  const statusText = JSON.stringify(h.find((n) => n.props?.role === "status").props.children);
  assert.match(statusText, /81/); assert.match(statusText, /filtros actuales excluyen/);
  await submit(); assert.equal(h.calls.length, 2);
  h.find((n) => n.type === "button" && n.props.children === "Actualizar listado").props.onClick();
  assert.equal(h.refreshed, 1); assert.ok(h.find((n) => n.props?.role === "status"));
});
