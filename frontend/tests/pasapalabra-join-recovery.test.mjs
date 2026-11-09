import "./helpers/academic-aliases.mjs";
import {test,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import Module from 'node:module';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';
import React from 'react';

function load(relative,mocks={}){const filename=fileURLToPath(new URL(relative,import.meta.url));const m=new Module(filename);m.filename=filename;m.paths=Module._nodeModulePaths(path.dirname(filename));const original=Module._load;Module._load=function(r,p,main){return r in mocks?mocks[r]:original.call(this,r,p,main);};try{m._compile(ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,filename);return m.exports;}finally{Module._load=original;}}
const draft=load('../src/lib/pasapalabra-join.ts');
const academic=load('../src/lib/academic.ts');
afterEach(()=>{delete global.window;delete global.sessionStorage;delete global.localStorage;});
test('draft is normalized, bounded, retained on read and cleared only explicitly',()=>{const values=new Map();global.window={sessionStorage:{getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)}};draft.saveJoinDraft(' abcdefgh2345 ');assert.equal(draft.readJoinDraft(),'ABCDEFGH2345');assert.equal(draft.readJoinDraft(),'ABCDEFGH2345');draft.clearJoinDraft();assert.equal(draft.readJoinDraft(),'');draft.saveJoinDraft('ABCDEFGHIJKLMNOP');assert.equal(draft.readJoinDraft().length,12);});
test('blocked tab storage does not break joining',()=>{global.window={get sessionStorage(){throw Error('blocked');}};assert.doesNotThrow(()=>draft.saveJoinDraft('ABCDE'));assert.equal(draft.readJoinDraft(),'');assert.doesNotThrow(()=>draft.clearJoinDraft());});
for(const destination of ["/dashboard?join=1",'/practicar?subject=1&block=2&category=3&difficulty=2','/practicar?block=2','/pasapalabra','/pasapalabra/rooms/3','https://evil.example/pasapalabra','//evil.example','/pasapalabra?redirect=evil']){
 test(`login consumes safe return destination: ${destination}`,async()=>{const values=new Map([['pasapalabra-return',destination],['pasapalabra-join-code','ABCDEFGH2345']]);global.sessionStorage={getItem:k=>values.get(k),removeItem:k=>values.delete(k)};global.localStorage={setItem(){}};let cursor=0;const slots=[],routes=[],timers=[];const previous=global.setTimeout;global.setTimeout=f=>{timers.push(f);return 1;};const hooks={...React,useState(initial){const i=cursor++;slots[i]??=initial;return [slots[i],v=>{slots[i]=v;}];}};let calls=0;try{const Login=load('../src/components/Login.tsx',{'react':hooks,'next/navigation':{useRouter:()=>({push:p=>routes.push(p)})},'axios':{isAxiosError:()=>false},'@/services/api':{loginUser:async()=>{calls++;return {access_token:'test-token'};}}}).default;cursor=0;const form=Login({});await form.props.onSubmit({preventDefault(){}});timers.forEach(f=>f());assert.deepEqual(routes,[(destination.startsWith('/pasapalabra')&&!destination.includes('?')||destination==="/dashboard?join=1"||academic.academicReturn(destination))?destination:'/dashboard']);assert.equal(calls,1);assert.equal(values.get('pasapalabra-join-code'),'ABCDEFGH2345');assert.equal(values.has('pasapalabra-return'),false);}finally{global.setTimeout=previous;}});
}
