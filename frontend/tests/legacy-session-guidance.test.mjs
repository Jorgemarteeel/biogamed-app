import "./helpers/academic-aliases.mjs";
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

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
const api = load("../src/services/api.ts");
const review = load("../src/lib/game-review.ts");

for (const specific of [true, false]) test(`active game handles ${specific ? "specific legacy" : "other 409"} conflict`, async () => {
  const slots = [], effects = [];
  let cursor = 0, requests = 0;
  const hooks = { ...React,
    useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial; return [slots[i], (v) => { slots[i] = typeof v === "function" ? v(slots[i]) : v; }]; },
    useRef(initial) { const i = cursor++; return slots[i] ??= { current: initial }; },
    useEffect(effect) { const i = cursor++; if (!(i in slots)) { slots[i] = true; effects.push(effect); } },
  };
  const original = Module._load;
  let Game;
  try {
    Module._load = function (request, parent, main) {
      if (request === "react") return hooks;
      if (request === "next/link") return function Link({ href, children, ...props }) { return React.createElement("a", { href, ...props }, children); };
      if (request === "@/components/LegacySessionNotice") return load("../src/components/LegacySessionNotice.tsx").default;
      if (request === "@/components/GameReview") return () => null;
      if (request === "@/lib/game-review") return review;
      if (request === "@/lib/question-exposure") return { QuestionExposure: class { show() {} setVisible() {} stop() {} resume() {} milliseconds() { return 0; } } };
      if (request === "@/services/api") return {
        isLegacySessionError: api.isLegacySessionError,
        submitTrivialGame: async () => { requests++; throw { isAxiosError: true, response: { status: 409, data: { detail: specific ? { code: "LEGACY_SESSION_NO_SNAPSHOT" } : "Other conflict" } } }; },
      };
      return original.call(this, request, parent, main);
    };
    Game = load("../src/components/TrivialGame.tsx").default;
  } finally { Module._load = original; }
  global.document = { visibilityState: "visible", addEventListener() {}, removeEventListener() {} };
  try {
    const session = { session_id: 1, topic_id: 7, content_context: null, questions: [{ id: 9, text: "Original", options: ["A", "B", "C", "D"] }] };
    const render = () => { cursor = 0; return Game({ session, topicName: "Topic" }); };
    function all(node) { return !node || typeof node !== "object" ? [] : [node, ...React.Children.toArray(node.props?.children).flatMap(all)]; }
    render(); effects.forEach((effect) => effect());
    all(render()).find((node) => node.type === "input").props.onChange();
    await all(render()).find((node) => node.type === "button" && node.props.children === "Finalizar y ver resultado").props.onClick();
    assert.equal(requests, 1);
    const html = renderToStaticMarkup(render());
    if (specific) {
      assert.match(html, /Esta partida se inició con una versión anterior y ya no puede continuarse. Puedes empezar una nueva/);
      assert.match(html, /href="\/game\?topicId=7&amp;mode=TRIVIAL"/);
      assert.match(html, /href="\/historial"/);
      assert.doesNotMatch(html, /Finalizar y ver resultado/);
    } else {
      assert.doesNotMatch(html, /se inició con una versión anterior|Preparar otra partida/);
      assert.match(html, /No se puede corregir esta partida con una copia válida/);
      assert.match(html, /Finalizar y ver resultado/);
    }
  } finally { delete global.document; }
});
