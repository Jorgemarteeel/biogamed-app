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
  const mod = new Module(filename);
  mod.filename = filename; mod.paths = Module._nodeModulePaths(path.dirname(filename));
  mod._compile(ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText, filename);
  return mod.exports;
}

test("state operation sends explicit authenticated state and list preserves filters and offset", async () => {
  const client = load("../src/services/api.ts");
  global.window = { localStorage: { getItem: () => "test-token" } };
  const adapter = client.default.defaults.adapter, calls = [];
  client.default.defaults.adapter = async (config) => {
    calls.push(config);
    assert.equal(config.headers.Authorization, "Bearer test-token");
    return { status: 200, headers: {}, config, data: { is_active: false } };
  };
  try {
    for (const active of [false, false, true]) await client.setCategoryQuestionState(3, 7, 9, 81, active);
    assert.deepEqual(calls.map(c => JSON.parse(c.data)), [{ is_active: false }, { is_active: false }, { is_active: true }]);
    assert.ok(calls.every(c => c.method === "put" && c.url === "/subjects/3/blocks/7/categories/9/questions/81/state"));
    await client.getCategoryQuestions(3, 7, 9, 12, 13, { state: "retired", mode: "TRIVIAL", difficulty: 2 });
    assert.deepEqual(calls[3].params, { skip: 12, limit: 13, state: "retired", mode: "TRIVIAL", difficulty: 2 });
  } finally { client.default.defaults.adapter = adapter; delete global.window; }
});

function harness({ active = true, filter = "all", page = 2, emptyAfter = false } = {}) {
  const slots = [], effects = [], calls = [], reads = [], routes = [], focus = [];
  let cursor = 0, resolve, reject;
  const question = { id: 81, is_active: active, text: "Original", question_type: "TRIVIAL", difficulty: 2,
    topic_id: 19, topic: { id: 19, name: "Topic" }, options: ["A", "B", "C", "D"], correct_option_index: 1 };
  const hooks = { ...React,
    useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial; return [slots[i], v => { slots[i] = typeof v === "function" ? v(slots[i]) : v; }]; },
    useRef(initial) { const i = cursor++; return slots[i] ??= { current: initial }; },
    useCallback(fn, deps) { const i = cursor++; if (!slots[i] || deps.some((v, j) => slots[i].deps[j] !== v)) slots[i] = { fn, deps }; return slots[i].fn; },
    useEffect(effect, deps) { const i = cursor++; if (!slots[i] || deps.some((v, j) => slots[i][j] !== v)) { slots[i] = deps; effects.push(effect); } },
  };
  const router = { push: url => routes.push(url), replace: url => routes.push(url) };
  let View; const original = Module._load;
  function Editor() { return null; }
  try {
    Module._load = function (request, parent, main) {
      if (request === "react") return hooks;
      if (request === "next/navigation") return { useRouter: () => router };
      if (request === "next/link") return "a";
      if (request.startsWith("@/components/")) return request.endsWith("CreateQuestionForm") ? Editor : () => null;
      if (request === "@/lib/subjects") return { SUBJECTS_PAGE_SIZE: 12, canManageSubjects: () => true };
      if (request === "@/services/api") return {
        getCurrentUser: async () => ({ role: "teacher" }),
        getCategoryDetail: async () => ({ id: 9, block: { id: 7, subject: { id: 3 } } }),
        getCategoryQuestions: async (...args) => { reads.push(args); return emptyAfter && reads.length > 1 ? [] : [question]; },
        setCategoryQuestionState: (...args) => { calls.push(args); return new Promise((yes, no) => { resolve = yes; reject = no; }); },
      };
      return original.call(this, request, parent, main);
    };
    View = load("../src/components/CategoryQuestionsView.tsx").default;
  } finally { Module._load = original; }
  global.window = { localStorage: { getItem: () => "test-token" } };
  global.document = { getElementById: id => ({ focus: () => focus.push(id) }) };
  global.requestAnimationFrame = fn => fn();
  const render = () => { cursor = 0; return View({ subjectId: 3, blockId: 7, categoryId: 9, page, mode: "TRIVIAL", level: "2", questionState: filter, invalidFilters: false }); };
  function all(node) { return !node || typeof node !== "object" ? [] : [node, ...React.Children.toArray(node.props?.children).flatMap(all)]; }
  const find = predicate => all(render()).find(predicate);
  return { render, find, calls, reads, routes, focus, Editor,
    button: text => find(n => n.type === "button" && n.props.children === text),
    flush: async () => { effects.splice(0).forEach(e => e()); await new Promise(setImmediate); },
    resolve: () => resolve({ ...question, is_active: !active }), reject: () => reject(new Error("Lost response")),
    cleanup: () => { delete global.window; delete global.document; delete global.requestAnimationFrame; },
  };
}

test("retirement requires confirmation, cancels by button or Escape, blocks duplicate sends and recovers errors", async () => {
  const h = harness();
  try {
    h.render(); await h.flush();
    assert.ok(h.find(n => n.type === "p" && React.Children.toArray(n.props.children).includes("Activa")));
    h.button("Retirar").props.onClick();
    assert.match(JSON.stringify(h.find(n => n.props?.id === "retirement-warning")), /partidas nuevas.*historial/);
    h.button("Cancelar").props.onClick(); assert.equal(h.calls.length, 0); assert.ok(h.focus.includes("state-81"));
    h.button("Retirar").props.onClick();
    h.find(n => n.props?.role === "group").props.onKeyDown({ key: "Escape" });
    assert.equal(h.calls.length, 0);
    h.button("Retirar").props.onClick();
    const confirm = h.button("Confirmar retirada");
    const pending = confirm.props.onClick(); confirm.props.onClick();
    assert.equal(h.calls.length, 1); assert.equal(h.button("Confirmar retirada").props.disabled, true);
    h.reject(); await new Promise(setImmediate); await pending;
    assert.match(h.find(n => n.props?.role === "alert").props.children[0], /repetir/);
    h.button("Confirmar retirada").props.onClick(); h.resolve(); await new Promise(setImmediate);
    assert.deepEqual(h.calls[1], [3, 7, 9, 81, false]);
    h.render(); await h.flush();
    assert.match(h.find(n => n.props?.role === "status").props.children, /retirada/);
    assert.deepEqual(h.reads[1], h.reads[0]);
  } finally { h.cleanup(); }
});

for (const active of [true, false]) test(`${active ? "retiring" : "reactivating"} last matching question adjusts page and preserves URL filters`, async () => {
  const h = harness({ active, filter: active ? "active" : "retired", emptyAfter: true });
  try {
    h.render(); await h.flush();
    h.button(active ? "Retirar" : "Reactivar").props.onClick();
    if (active) h.button("Confirmar retirada").props.onClick();
    h.resolve(); await new Promise(setImmediate); h.render(); await h.flush();
    const url = new URL(h.routes[0], "http://localhost");
    assert.equal(url.searchParams.get("state"), active ? "active" : "retired");
    assert.equal(url.searchParams.get("mode"), "TRIVIAL"); assert.equal(url.searchParams.get("level"), "2");
    assert.equal(url.searchParams.get("page"), null); assert.equal(url.searchParams.get("adjusted"), "1");
  } finally { h.cleanup(); }
});

test("state filter resets page; retired questions remain editable and retain state filter", async () => {
  const h = harness({ active: false, filter: "retired" });
  try {
    h.render(); await h.flush();
    assert.ok(h.find(n => n.type === "p" && React.Children.toArray(n.props.children).includes("Retirada")));
    const next = h.find(n => n.type === "a" && n.props.children === "Anterior");
    assert.match(next.props.href, /state=retired/);
    h.find(n => n.props?.id === "edit-81").props.onClick();
    const editor = h.find(n => n.type === h.Editor);
    assert.equal(editor.props.question.is_active, false); assert.equal(editor.props.questionState, "retired");
    editor.props.onClose(true); h.render(); await h.flush();
    assert.deepEqual(h.reads[1], h.reads[0]);
    h.find(n => n.props?.id === "question-state").props.onValueChange("active");
    h.find(n => n.type === "form").props.onSubmit({ preventDefault() {} });
    assert.match(h.routes[0], /state=active/); assert.doesNotMatch(h.routes[0], /page=/);
  } finally { h.cleanup(); }
});

test("page restores state, mode, difficulty and page from the URL and rejects invalid state", async () => {
  const original = Module._load;
  let Page;
  try {
    Module._load = function (request, parent, main) {
      if (request === "@/components/CategoryQuestionsView") return () => null;
      return original.call(this, request, parent, main);
    };
    Page = load("../src/app/gestion/asignaturas/[id]/bloques/[blockId]/categorias/[categoryId]/page.tsx").default;
  } finally { Module._load = original; }
  const params = Promise.resolve({ id: "3", blockId: "7", categoryId: "9" });
  const result = await Page({ params, searchParams: Promise.resolve({ state: "retired", mode: "PASAPALABRA", level: "unknown", page: "3" }) });
  assert.equal(result.props.questionState, "retired"); assert.equal(result.props.page, 3);
  assert.equal(result.props.level, "unknown"); assert.equal(result.props.mode, "PASAPALABRA");
  assert.equal(result.props.invalidFilters, false);
  const invalid = await Page({ params, searchParams: Promise.resolve({ state: "deleted" }) });
  assert.equal(invalid.props.invalidFilters, true);
});


test("shared selectors keep all options and only apply pending filters on submit", async () => {
  const h = harness({ filter: "all" });
  try {
    h.render(); await h.flush();
    const mode = () => h.find(n => n.props?.id === "question-mode");
    const level = () => h.find(n => n.props?.id === "question-level");
    const state = () => h.find(n => n.props?.id === "question-state");
    assert.deepEqual(mode().props.options.map(o => o.value), ["ALL", "TRIVIAL", "PASAPALABRA"]);
    assert.deepEqual(level().props.options.map(o => o.value), ["ALL", "1", "2", "3", "4", "unknown"]);
    assert.equal(level().props.options[0].label, "Todas las dificultades");
    assert.deepEqual(state().props.options.map(o => o.value), ["all", "active", "retired"]);
    mode().props.onValueChange("PASAPALABRA"); level().props.onValueChange("unknown"); state().props.onValueChange("retired");
    assert.equal(h.routes.length, 0); assert.equal(h.reads.length, 1);
    h.find(n => n.type === "form").props.onSubmit({ preventDefault() {} });
    let url = new URL(h.routes.pop(), "http://localhost");
    assert.equal(url.searchParams.get("mode"), "PASAPALABRA");
    assert.equal(url.searchParams.get("level"), "unknown"); assert.equal(url.searchParams.get("state"), "retired");
    assert.equal(url.searchParams.get("page"), null);
    mode().props.onValueChange("ALL"); level().props.onValueChange("ALL"); state().props.onValueChange("all");
    assert.equal(h.routes.length, 0);
    h.find(n => n.type === "form").props.onSubmit({ preventDefault() {} });
    url = new URL(h.routes[0], "http://localhost");
    assert.equal(url.searchParams.get("mode"), null); assert.equal(url.searchParams.get("level"), null);
    assert.equal(url.searchParams.get("state"), "all");
  } finally { h.cleanup(); }
});
