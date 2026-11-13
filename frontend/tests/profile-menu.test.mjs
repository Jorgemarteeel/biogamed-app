import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import Module from 'node:module';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';
import React from 'react';

function harness(name,role='student'){
 const slots=[],pending=[],listeners=new Map();let cursor=0,focuses=0;
 const hooks={...React,useState(initial){const i=cursor++;if(!(i in slots))slots[i]=initial;return[slots[i],v=>slots[i]=typeof v==='function'?v(slots[i]):v];},useRef(initial){const i=cursor++;return slots[i]??={current:initial};},useEffect(effect,deps){const i=cursor++;const prev=slots[i];if(!prev||deps.some((v,j)=>v!==prev.deps[j])){prev?.cleanup?.();slots[i]={deps};pending.push(()=>{slots[i].cleanup=effect();});}}};
 global.window={addEventListener(){},removeEventListener(){}};
 global.document={addEventListener:(k,f)=>listeners.set(k,f),removeEventListener:k=>listeners.delete(k)};
 const file=fileURLToPath(new URL('../src/components/ProfileMenu.tsx',import.meta.url)),m=new Module(file);m.filename=file;m.paths=Module._nodeModulePaths(path.dirname(file));const old=Module._load;
 try{Module._load=function(r,p,main){if(r==='react')return hooks;if(r==='next/link')return 'a';if(r==='@/services/api')return {getCurrentUser:async()=>({name,role})};if(r==='@/lib/subjects')return {canManageSubjects:r=>['teacher','admin'].includes(r)};return old.call(this,r,p,main);};m._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,file);}finally{Module._load=old;}
 function all(n){return !n||typeof n!=='object'?[]:[n,...React.Children.toArray(n.props?.children).flatMap(all)];}
 function nodes(){cursor=0;const result=all(m.exports.default({name,role}));result.find(n=>n.type==='button').props.ref.current={focus:()=>focuses++};result[0].props.ref.current={contains:()=>false};return result;}
 async function flush(){nodes();pending.splice(0).forEach(f=>f());await new Promise(setImmediate);nodes();}
 return{nodes,flush,listeners,focuses:()=>focuses,toggle:()=>nodes().find(n=>n.type==='button').props.onClick()};
}

test('long visible names retain their full accessible text and linked navigation state',async()=>{
 const name='Nombre ficticio muy largo con apellidos y ñ '.repeat(5);const h=harness(name);await h.flush();
 const n=h.nodes(),button=n.find(x=>x.type==='button');assert.equal(button.props['aria-expanded'],false);assert.equal(button.props['aria-controls'],'profile-navigation');
 assert.equal(n.find(x=>x.props?.className==='sr-only').props.children,name.trim());
 h.toggle();await h.flush();assert.ok(h.nodes().some(x=>x.props?.href==='/cuenta'));assert.ok(!h.nodes().some(x=>x.props?.href==='/administracion/usuarios'));
});
test('Escape closes the menu and returns focus to its trigger without changing identity',async()=>{
 const h=harness('Cuenta ficticia extensa para teclado','admin');await h.flush();h.toggle();await h.flush();
 assert.ok(h.nodes().some(x=>x.props?.href==='/administracion/usuarios'));
 h.listeners.get('keydown')({key:'Escape'});await h.flush();assert.equal(h.focuses(),1);assert.equal(h.nodes().find(x=>x.type==='button').props['aria-expanded'],false);assert.ok(!h.nodes().some(x=>x.type==='nav'));
});
test('outside click and navigation links close the menu',async()=>{
 const h=harness('Cuenta ficticia');await h.flush();h.toggle();await h.flush();h.listeners.get('pointerdown')({target:{}});await h.flush();assert.ok(!h.nodes().some(x=>x.type==='nav'));
 h.toggle();await h.flush();h.nodes().find(x=>x.props?.href==='/cuenta').props.onClick();await h.flush();assert.ok(!h.nodes().some(x=>x.type==='nav'));
});
