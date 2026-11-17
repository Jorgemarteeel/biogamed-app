import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import Module from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";

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


import {harness} from './helpers/question-management.mjs';

const q={id:81,text:'Synthetic',is_active:true,question_type:'INMUNOQUEST',reference_answer:'Reference',bank:'DNA',difficulty:2,subject_id:3,block_id:7,category_id:9};
test('retirement cancels safely and prevents duplicate actions while a request is pending',async()=>{
 const h=harness({questions:[q],controlled:true});await h.boot();const old=global.window;global.window={confirm:()=>false};
 try{await h.button('Retirar').props.onClick();assert.equal(h.calls.filter(c=>c.method==='put').length,0);global.window.confirm=()=>true;const sent=h.button('Retirar').props.onClick();await h.button('Retirar').props.onClick();assert.equal(h.calls.filter(c=>c.method==='put').length,1);h.resolve();await sent;await new Promise(setImmediate);assert.equal(h.calls.find(c=>c.method==='put').url,'/questions/manage/81/state');assert.deepEqual(h.calls.find(c=>c.method==='put').data,{is_active:false});assert.ok(h.find(n=>n.props?.role==='status'&&String(n.props.children).includes('retirada')));}finally{global.window=old;}
});
test('retirement network error is recoverable without changing filters',async()=>{
 const h=harness({questions:[q],controlled:true,query:'subject=3&state=active&difficulty=2'});await h.boot();const old=global.window;global.window={confirm:()=>true};try{const first=h.button('Retirar').props.onClick();h.reject();await first;await new Promise(setImmediate);assert.ok(h.find(n=>n.props?.role==='alert'));const next=h.button('Retirar').props.onClick();h.resolve();await next;await new Promise(setImmediate);assert.equal(h.calls.filter(c=>c.method==='put').length,2);assert.equal(h.routes.length,0);}finally{global.window=old;}
});
test('reactivation remains explicit and retains the current query',async()=>{const h=harness({questions:[{...q,is_active:false}],query:'state=retired&mode=INMUNOQUEST'});await h.boot();const old=global.window;global.window={confirm:()=>true};try{await h.button('Reactivar').props.onClick();assert.deepEqual(h.calls.find(c=>c.method==='put').data,{is_active:true});assert.equal(h.routes.length,0);}finally{global.window=old;}});
