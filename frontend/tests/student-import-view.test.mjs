import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import Module from "node:module";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

// Render the actual import controls with a teacher and deterministic API responses.
function importer(preview, receipt) {
  const slots = [];
  const effects = [];
  const posts = [];
  let cursor = 0;
  const router = { replace() {} };
  const hooks = {
    ...React,
    useState(initial) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = initial;
      return [slots[index], value => { slots[index] = typeof value === "function" ? value(slots[index]) : value; }];
    },
    useRef(value) { const index = cursor++; return slots[index] ??= { current: value }; },
    useEffect(effect, deps) {
      const index = cursor++;
      if (!slots[index] || deps.some((value, i) => slots[index][i] !== value)) effects.push(effect);
      slots[index] = deps;
    },
  };
  const file = fileURLToPath(new URL("../src/components/UserImportView.tsx", import.meta.url));
  const component = new Module(file);
  const original = Module._load;
  try {
    Module._load = function (name, parent, main) {
      if (name === "react") return hooks;
      if (name === "next/link") return "a";
      if (name === "next/navigation") return { useRouter: () => router };
      if (name.startsWith("@/components/")) return () => null;
      if (name === "@/services/api") return {
        __esModule: true, getCurrentUser: async () => ({ role: "teacher" }),
        default: {
          get: async () => ({ data: { total: 0, items: [] } }),
          post: async url => { posts.push(url); return { data: url.endsWith("/validate") ? preview : receipt }; },
        },
      };
      return original.call(this, name, parent, main);
    };
    component.paths = Module._nodeModulePaths(process.cwd());
    component._compile(ts.transpileModule(readFileSync(file, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    }).outputText, file);
  } finally { Module._load = original; }
  function render() { cursor = 0; return component.exports.default({ target: "alumnado" }); }
  function walk(node) {
    return React.isValidElement(node) ? [node, ...React.Children.toArray(node.props.children).flatMap(walk)] : [];
  }
  const find = predicate => walk(render()).find(predicate);
  const flush = async () => { render(); effects.splice(0).forEach(effect => effect()); await new Promise(setImmediate); };
  const button = name => find(node => node.type === "button" && node.props.children === name);
  const choose = name => find(node => node.props.type === "file").props.onChange({ target: { files: [new File(["synthetic"], name)] } });
  return { posts, button, choose, html: () => renderToStaticMarkup(render()), async validate() {
    await flush(); await flush();
    choose("alumnado.csv");
    button("Validar sin guardar").props.onClick();
    await flush();
  } };
}

test("one account shared across rows and direct links for both years", async t => {
  const original = globalThis.window;
  globalThis.window = { localStorage: { getItem: () => "synthetic" } };
  t.after(() => { if (original === undefined) delete globalThis.window; else globalThis.window = original; });
  const base = { dni: "•••", name: "Ada", email: "ada@example.com", academic_year: "2026-2027", enabled_year: "2026-2027" };
  const ui = importer({ total: 3, valid: 3, proof: "fixture", errors: [],
    summary: { new_accounts: 1, new_enrollments: 3, year_changes: 1 }, preview: [
      { ...base, row: 2, account_row: 2, action: "new_account", edition_id: 10, subject_name: "Inmunología" },
      { ...base, row: 3, account_row: 2, action: "new_account", edition_id: 11, subject_name: "Fisiología" },
      { ...base, name: "Leo", email: "leo@example.com", row: 4, action: "new_enrollment", subject_name: "Inmunología",
        edition_id: 10, previous_edition_id: 9, previous_year: "2025-2026" },
    ] }, { count: 1, sent: 1, enrolled: 3, already_enrolled: 0, replayed: false });
  await ui.validate();
  assert.match(ui.html(), /Misma cuenta que la fila 2/);
  assert.match(ui.html(), /2025–2026 → 2026–2027/);
  assert.equal(ui.button("Confirmar importación").props.disabled, false);
  ui.button("Confirmar importación").props.onClick();
  await new Promise(setImmediate);
  const html = ui.html();
  assert.match(html, /Cuentas creadas: 1\. Matrículas añadidas: 3/);
  assert.deepEqual([...html.matchAll(/href="\/altas\/ediciones\?edicion=(\d+)"/g)].map(match => match[1]).sort(),
    ["10", "11", "9"]);
  assert.deepEqual(ui.posts, ["/user-imports/alumnado/validate", "/user-imports/alumnado/confirm"]);
});
test("no-op skips confirmation, inactive enrollment still needs it, new file clears review", async t => {
  const original = globalThis.window;
  globalThis.window = { localStorage: { getItem: () => "synthetic" } };
  t.after(() => { if (original === undefined) delete globalThis.window; else globalThis.window = original; });
  const report = { total: 1, valid: 1, proof: "fixture", errors: [], has_changes: false,
    summary: { new_accounts: 0, new_enrollments: 0, year_changes: 0 }, preview: [
      { row: 2, name: "Ada", email: "ada@example.com", action: "existing_enrollment",
        subject_name: "Inmunología", academic_year: "2026-2027", enabled_year: "2026-2027", edition_id: 10 },
    ] };
  const ui = importer(report);
  await ui.validate();
  assert.match(ui.html(), /Este lote no requiere cambios/);
  assert.match(ui.html(), /Ver matrículas existentes/);
  assert.match(ui.html(), /1 fila · 1 válida/);
  assert.equal(ui.button("Confirmar importación"), undefined);
  assert.deepEqual(ui.posts, ["/user-imports/alumnado/validate"]);
  const activation = importer({ ...report, has_changes: true });
  await activation.validate();
  assert.equal(activation.button("Confirmar importación").props.disabled, false);
  activation.choose("otro-archivo.csv");
  assert.equal(activation.button("Confirmar importación"), undefined);
  assert.doesNotMatch(activation.html(), /1 fila · 1 válida/);
  assert.match(activation.html(), /otro-archivo.csv/);
});
