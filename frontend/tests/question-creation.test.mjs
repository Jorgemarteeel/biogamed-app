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
function harness(question) {
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
        editCategoryQuestion: (...args) => { calls.push(args); return new Promise((yes, no) => { resolve = yes; reject = no; }); },
      };
      return original.call(this, request, parent, main);
    };
    Form = load("../src/components/CreateQuestionForm.tsx").default;
  } finally { Module._load = original; }
  let refreshed = 0;
  const closed = [];
  const closureDetails = [];
  const render = () => { cursor = 0; return Form({ subjectId: 3, blockId: 7, categoryId: 9, mode: "TRIVIAL", level: "2", question, onClose: (saved, uncertain) => { closed.push(saved); closureDetails.push({ saved, uncertain }); }, onRefresh: () => refreshed++ }); };
  function all(node) { return !node || typeof node !== "object" ? [] : [node, ...React.Children.toArray(node.props?.children).flatMap(all)]; }
  const find = (predicate) => all(render()).find(predicate);
  const change = (id, value) => find((n) => n.props?.id === id).props.onChange({ target: { value } });
  return { render, find, change, calls, effects, closed, closureDetails, resolve: (v) => resolve(v), reject: (e) => reject(e), get refreshed() { return refreshed; } };
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

for (const mode of ["TRIVIAL", "PASAPALABRA"]) test(`editing ${mode} preloads fields, preserves errors and confirms save or cancellation`, async () => {
  const question = { id: 81, text: "Original", category_id: 9, topic_id: 19, topic: { name: "Tema API" },
    question_type: mode, difficulty: 2, options: mode === "TRIVIAL" ? ["A", "B", "C", "D"] : null,
    correct_option_index: mode === "TRIVIAL" ? 0 : null, letter: mode === "PASAPALABRA" ? "L" : null,
    exact_word: mode === "PASAPALABRA" ? "Luna" : null, accepted_answers: mode === "PASAPALABRA" ? ["Satelite"] : null };
  const h = harness(question);
  let focused;
  global.document = { getElementById: (id) => ({ focus: () => { focused = id; } }) };
  try {
    h.render(); h.effects.forEach((effect) => effect()); await Promise.resolve();
    assert.equal(focused, "create-text");
    assert.equal(h.find((n) => n.props?.id === "create-text").props.value, "Original");
    assert.equal(h.find((n) => n.props?.id === "create-mode").props.disabled, true);
    if (mode === "PASAPALABRA") assert.equal(h.find((n) => n.props?.id === "create-alternatives").props.value, "Satelite");
    h.change("create-text", "Edited");
    const submit = () => h.find((n) => n.type === "form").props.onSubmit({ preventDefault() {} });
    const first = submit(); await submit(); assert.equal(h.calls.length, 1);
    assert.deepEqual(h.calls[0].slice(0, 4), [3, 7, 9, 81]);
    assert.equal(h.calls[0][4].question_type, mode);
    assert.equal(h.calls[0][4].category_id, undefined);
    h.reject({ isAxiosError: true, response: { status: 422, data: { detail: "Validation failed" } } }); await first;
    assert.match(h.find((n) => n.props?.role === "alert").props.children, /Validation failed/);
    assert.equal(h.find((n) => n.props?.id === "create-text").props.value, "Edited");
    const second = submit(); h.resolve({ ...question, text: "Edited" }); await second;
    assert.match(JSON.stringify(h.find((n) => n.props?.role === "status").props.children), /guardada/);
    h.find((n) => n.type === "button" && n.props.children === "Volver al listado").props.onClick();
    assert.deepEqual(h.closed, [true]);
    const cancel = harness(question);
    cancel.render(); cancel.effects.forEach((effect) => effect()); await Promise.resolve();
    cancel.change("create-text", "Unsaved");
    cancel.find((n) => n.type === "button" && n.props.children === "Cancelar").props.onClick();
    assert.deepEqual(cancel.closed, []);
    assert.match(JSON.stringify(cancel.find((n) => n.props?.role === "alert").props.children), /No se guardarán/);
    cancel.find((n) => n.type === "button" && n.props.children === "Descartar cambios").props.onClick();
    assert.deepEqual(cancel.closed, [false]); assert.equal(cancel.calls.length, 0);
  } finally { delete global.document; }
});

test("editing uses authenticated PUT and legacy error detection is specific", async () => {
  global.window = { localStorage: { getItem: () => "demo-token" } };
  const adapter = client.default.defaults.adapter;
  client.default.defaults.adapter = async (config) => {
    assert.equal(config.method, "put");
    assert.equal(config.url, "/subjects/3/blocks/7/categories/9/questions/81");
    assert.equal(config.headers.Authorization, "Bearer demo-token");
    return { status: 200, headers: {}, config, data: { id: 81 } };
  };
  try {
    assert.equal((await client.editCategoryQuestion(3, 7, 9, 81, { text: "Edited" })).id, 81);
    const error = (status, detail) => ({ isAxiosError: true, response: { status, data: { detail } } });
    assert.equal(client.isLegacySessionError(error(409, { code: "LEGACY_SESSION_NO_SNAPSHOT" })), true);
    assert.equal(client.isLegacySessionError(error(409, "Already completed")), false);
    assert.equal(client.isLegacySessionError(error(409, { code: "OTHER" })), false);
    assert.equal(client.isLegacySessionError(error(403, { code: "LEGACY_SESSION_NO_SNAPSHOT" })), false);
    assert.equal(client.isLegacySessionError(new Error("Network")), false);
  } finally { client.default.defaults.adapter = adapter; delete global.window; }
});

test("closing after an unconfirmed save warns that the server might have persisted it", async () => {
  const h = harness({ id: 81, topic_id: 19, text: "Draft", question_type: "TRIVIAL", options: ["A", "B", "C", "D"], correct_option_index: 0 });
  h.render();
  const pending = h.find((n) => n.type === "form").props.onSubmit({ preventDefault() {} });
  h.reject(new Error("Response lost")); await pending;
  assert.equal(h.find((n) => n.props?.id === "create-text").props.value, "Draft");
  h.find((n) => n.type === "button" && n.props.children === "Cancelar").props.onClick();
  assert.match(JSON.stringify(h.find((n) => n.props?.role === "alert" && n.props.className === "notice-warning").props.children), /podría haberse guardado/);
  h.find((n) => n.type === "button" && n.props.children === "Descartar cambios").props.onClick();
  assert.deepEqual(h.closureDetails, [{ saved: false, uncertain: true }]);
});
