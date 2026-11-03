import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

const originalLoad = Module._load;
let Breadcrumbs;
let CreatePanel;
try {
  Module._load = function (request, parent, isMain) {
    if (request === "next/link") return function Link({ href, children, ...props }) {
      return React.createElement("a", { href, ...props }, children);
    };
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
  Breadcrumbs = load("ContentBreadcrumbs.tsx");
  CreatePanel = load("CreateContentPanel.tsx");
} finally { Module._load = originalLoad; }

test("breadcrumbs use actual subject and block names and identify the current level", () => {
  const subject = { id: 7, name: "Bioinformática avanzada" };
  const block = { name: "Análisis de secuencias" };
  const html = renderToStaticMarkup(React.createElement(Breadcrumbs, { subject, block }));
  assert.match(html, /href="\/dashboard"[^>]*>Panel/);
  assert.match(html, /href="\/gestion\/asignaturas"[^>]*>Asignaturas/);
  assert.match(html, /href="\/gestion\/asignaturas\/7"[^>]*>Bioinformática avanzada/);
  assert.match(html, /aria-current="page"[^>]*>Análisis de secuencias/);
  const root = renderToStaticMarkup(React.createElement(Breadcrumbs));
  assert.match(root, /aria-current="page"[^>]*>Asignaturas/);
});

test("creation form starts collapsed with an announced state", () => {
  const html = renderToStaticMarkup(React.createElement(CreatePanel, {
    id: "create-category", label: "Crear categoría",
  }, React.createElement("input", { id: "category-name" })));
  assert.match(html, /aria-expanded="false"/);
  assert.match(html, /aria-controls="create-category-panel"/);
  assert.doesNotMatch(html, /id="category-name"/);
});
