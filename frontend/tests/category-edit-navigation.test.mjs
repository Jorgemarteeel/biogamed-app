import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";
import React from "react";

for (const saved of [false, true]) test(`returning after ${saved ? "save" : "cancel"} preserves filtered page`, async () => {
  const slots = [], effects = [], calls = [], focus = [];
  let cursor = 0;
  const hooks = { ...React,
    useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = initial; return [slots[i], (v) => { slots[i] = typeof v === "function" ? v(slots[i]) : v; }]; },
    useRef(initial) { const i = cursor++; return slots[i] ??= { current: initial }; },
    useEffect(effect, deps) { const i = cursor++; if (!slots[i] || deps.some((v, j) => slots[i][j] !== v)) { slots[i] = deps; effects.push(effect); } },
  };
  const question = { id: 81, text: "Original", question_type: "TRIVIAL", difficulty: 2, topic: { id: 19, name: "Topic" }, topic_id: 19, options: ["A", "B", "C", "D"], correct_option_index: 1 };
  const router = { replace: () => assert.fail("No redirect expected"), push: () => assert.fail("No URL change expected") };
  function QuestionForm() { return null; }
  let View;
  const original = Module._load;
  try {
    Module._load = function (request, parent, main) {
      if (request === "react") return hooks;
      if (request === "next/navigation") return { useRouter: () => router };
      if (request === "next/link") return () => null;
      if (["@/components/Brand", "@/components/ProfileMenu", "@/components/ContentBreadcrumbs"].includes(request)) return () => null;
      if (request === "@/components/CreateQuestionForm") return QuestionForm;
      if (request === "@/lib/subjects") return { SUBJECTS_PAGE_SIZE: 12, canManageSubjects: () => true };
      if (request === "@/services/api") return {
        getCurrentUser: async () => ({ role: "teacher" }),
        getCategoryDetail: async () => ({ id: 9, name: "Category", block: { id: 7, subject: { id: 3 } } }),
        getCategoryQuestions: async (...args) => { calls.push(args); return calls.length === 1 ? [question] : []; },
      };
      return original.call(this, request, parent, main);
    };
    const filename = fileURLToPath(new URL("../src/components/CategoryQuestionsView.tsx", import.meta.url));
    const loaded = new Module(filename);
    loaded.filename = filename; loaded.paths = Module._nodeModulePaths(path.dirname(filename));
    loaded._compile(ts.transpileModule(fs.readFileSync(filename, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    }).outputText, filename);
    View = loaded.exports.default;
  } finally { Module._load = original; }
  global.window = { localStorage: { getItem: () => "test-token" } };
  global.document = { getElementById: (id) => id === "edit-81" && saved ? null : { focus: () => focus.push(id) } };
  global.requestAnimationFrame = (fn) => fn();
  try {
    const render = () => { cursor = 0; return View({ subjectId: 3, blockId: 7, categoryId: 9, page: 2, mode: "TRIVIAL", level: "2", invalidFilters: false }); };
    const flush = async () => { effects.splice(0).forEach((effect) => effect()); await new Promise(setImmediate); };
    function all(node) { return !node || typeof node !== "object" ? [] : [node, ...React.Children.toArray(node.props?.children).flatMap(all)]; }
    render(); await flush();
    all(render()).find((node) => node.props?.id === "edit-81").props.onClick();
    const editor = all(render()).find((node) => node.type === QuestionForm);
    assert.equal(editor.props.question.id, 81);
    editor.props.onClose(saved);
    render(); await flush(); render();
    assert.equal(calls.length, saved ? 2 : 1);
    assert.deepEqual(calls[0], [3, 7, 9, 12, 13, { mode: "TRIVIAL", difficulty: 2 }]);
    if (saved) assert.deepEqual(calls[1], calls[0]);
    assert.equal(all(render()).find((node) => node.props?.id === "question-mode").props.value, "TRIVIAL");
    assert.equal(all(render()).find((node) => node.props?.id === "question-level").props.value, "2");
    assert.ok(focus.includes(saved ? "question-list-heading" : "edit-81"));
  } finally { delete global.window; delete global.document; delete global.requestAnimationFrame; }
});
