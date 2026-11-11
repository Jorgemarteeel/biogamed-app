import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";
import React from "react";
function load(relative) {
  const file = fileURLToPath(new URL(relative, import.meta.url));
  const mod = new Module(file); mod.filename = file; mod.paths = Module._nodeModulePaths(path.dirname(file));
  mod._compile(ts.transpileModule(fs.readFileSync(file, "utf8"), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText, file);
  return mod.exports;
}
function harness() {
  const states = []; let cursor = 0, resolve, reject, denied = 0;
  const calls = [], saved = [];
  const hooks = { ...React, useId: () => "fixture", useEffect() {},
    useState(initial) { const i = cursor++; if (!(i in states)) states[i] = initial; return [states[i], (v) => { states[i] = typeof v === "function" ? v(states[i]) : v; }]; },
    useRef(initial) { const i = cursor++; return states[i] ??= { current: initial }; },
  };
  const old = Module._load; let Component;
  try { Module._load = function (r, p, m) { return r === "react" ? hooks : old.call(this, r, p, m); }; Component = load("../src/components/EditContentFields.tsx").default; }
  finally { Module._load = old; }
  function all(n) { return !n || typeof n !== "object" ? [] : [n, ...React.Children.toArray(n.props?.children).flatMap(all)]; }
  const find = (predicate) => { cursor = 0; return all(Component({ item: { id: 7, name: "Original", description: "Descripción" }, save: (p) => { calls.push(p); return new Promise((yes, no) => { resolve = yes; reject = no; }); }, onSaved: (p) => saved.push(p), onForbidden: () => denied++ })).find(predicate); };
  const button = (name) => find((n) => n.type === "button" && n.props.children === name);
  const change = (field, value) => find((n) => n.props.id === `fixture-${field}`).props.onChange({ target: { value } });
  const submit = () => find((n) => n.type === "form").props.onSubmit({ preventDefault() {} });
  return { find, button, change, submit, calls, saved, resolve: (v) => resolve(v), reject: (v) => reject(v), denied: () => denied };
}
test("prefilled editor cancels without saving and resets discarded fields", () => {
  const h = harness(); h.button("Editar").props.onClick();
  assert.equal(h.find((n) => n.type === "input").props.value, "Original");
  assert.equal(h.find((n) => n.type === "textarea").props.value, "Descripción");
  h.change("name", "Descartado"); h.button("Cancelar").props.onClick();
  assert.equal(h.find((n) => n.type === "form"), undefined); assert.equal(h.calls.length, 0);
  h.button("Editar").props.onClick(); assert.equal(h.find((n) => n.type === "input").props.value, "Original");
});
test("trimmed validation, explicit save and duplicate submit guard", async () => {
  const h = harness(); h.button("Editar").props.onClick(); h.change("name", "   "); await h.submit();
  assert.equal(h.calls.length, 0); assert.match(h.find((n) => n.props.role === "alert").props.children, /nombre/);
  h.change("name", "x".repeat(256)); await h.submit(); assert.equal(h.calls.length, 0);
  h.change("name", " Nuevo "); h.change("description", "");
  const pending = h.submit(); await h.submit(); assert.deepEqual(h.calls, [{ name: "Nuevo", description: null }]);
  assert.equal(h.button("Cancelar").props.disabled, true);
  h.resolve({ id: 7, name: "Nuevo", description: null }); await pending;
  assert.equal(h.saved[0].id, 7); assert.equal(h.find((n) => n.type === "form"), undefined);
  assert.equal(h.find((n) => n.props.role === "status").props.children, "Cambios guardados.");
});
test("errors preserve fields and permission loss propagates", async () => {
  const h = harness(); h.button("Editar").props.onClick(); h.change("name", "Conservar");
  let p = h.submit(); h.reject({ isAxiosError: true, response: { status: 422 } }); await p;
  assert.equal(h.find((n) => n.type === "input").props.value, "Conservar");
  assert.match(h.find((n) => n.props.role === "alert").props.children, /Revisa/);
  p = h.submit(); h.reject(new Error("network")); await p;
  assert.match(h.find((n) => n.props.role === "alert").props.children, /confirmar/);
  p = h.submit(); h.reject({ isAxiosError: true, response: { status: 403 } }); await p;
  assert.equal(h.denied(), 1); assert.equal(h.saved.length, 0);
});
test("metadata uses authenticated PATCH, independently from category linking", async () => {
  const api = load("../src/services/api.ts"); global.window = { localStorage: { getItem: () => "fixture-token" } };
  const old = api.default.defaults.adapter, calls = [];
  api.default.defaults.adapter = async (config) => { calls.push(config); return { status: 200, headers: {}, config, data: { id: 7 } }; };
  try {
    const p = { name: "Nombre", description: null };
    await api.editSubject(1, p); await api.editContentBlock(1, 2, p); await api.editCategory(1, 2, 3, p);
    assert.deepEqual(calls.map((c) => c.url), ["/subjects/1", "/subjects/1/blocks/2", "/subjects/1/blocks/2/categories/3"]);
    for (const c of calls) { assert.equal(c.method, "patch"); assert.equal(c.headers.Authorization, "Bearer fixture-token"); assert.deepEqual(JSON.parse(c.data), p); }
  } finally { api.default.defaults.adapter = old; delete global.window; }
});
