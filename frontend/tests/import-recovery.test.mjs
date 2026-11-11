import {test} from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import Module from 'node:module';import {fileURLToPath} from 'node:url';import ts from 'typescript';import React from 'react';
function load(file){const filename=fileURLToPath(new URL(file,import.meta.url));const m=new Module(filename);m.filename=filename;m.paths=Module._nodeModulePaths(path.dirname(filename));m._compile(ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,filename);return m.exports;}
const refs=load('../src/lib/import-recovery.ts');
const userId='00000000-0000-4000-8000-000000000001';const ref={version:1,userId,subjectId:1,blockId:2,categoryId:3,operationId:'00000000-0000-4000-8000-000000000002'};
function storage(){const map=new Map();return {getItem:k=>map.get(k)??null,setItem:(k,v)=>map.set(k,v)};}
test('reference contains only minimal fields and rejects invalid or mismatched data',()=>{
 const s=storage();refs.writeReference(s,ref);assert.deepEqual(refs.readReference(s,userId,1,2,3),ref);assert.equal(refs.readReference(s,'other',1,2,3),null);
 for(const value of ['bad',JSON.stringify({...ref,proof:'secret'}),JSON.stringify({...ref,userId:'other'}),JSON.stringify({...ref,operationId:'invalid'})]){s.setItem(refs.referenceKey(userId,3),value);assert.throws(()=>refs.readReference(s,userId,1,2,3));}
 assert.throws(()=>refs.readReference({getItem(){throw new Error('blocked')}},userId,1,2,3));
});
function harness({status='confirmed',invalid=false,blocked=false,http=0,switchUser=false}={}){
 const s=storage();refs.writeReference(s,ref);if(invalid)s.setItem(refs.referenceKey(userId,3),'invalid');
 global.window={sessionStorage:blocked?{getItem(){throw new Error('blocked')}}:s};
 const slots=[],effects=[],calls=[];let cursor=0,meCalls=0;
 const hooks={...React,useState(initial){const i=cursor++;if(!(i in slots))slots[i]=initial;return [slots[i],v=>slots[i]=typeof v==='function'?v(slots[i]):v];},useRef(v){const i=cursor++;return slots[i]??={current:v};},useEffect(fn){effects.push(fn);},useCallback(fn){return fn;}};
 const old=Module._load;let Component;try{Module._load=function(r,p,m){if(r==='react')return hooks;if(r==='next/link')return 'a';if(r==='@/lib/import-recovery')return refs;if(r==='@/services/api')return {__esModule:true,getCurrentUser:async()=>({id:switchUser&&++meCalls>1?'other':userId,role:'teacher'}),default:{get:async url=>{calls.push(url);if(http)throw {isAxiosError:true,response:{status:http}};return {data:{status,count:2}};}}};return old.call(this,r,p,m);};Component=load('../src/components/ImportRecovery.tsx').default;}finally{Module._load=old;}
 const render=()=>{cursor=0;return Component({subjectId:1,blockId:2,categoryId:3});};function all(n){return !n||typeof n!=='object'?[]:[n,...React.Children.toArray(n.props?.children).flatMap(all)];}
 const find=f=>all(render()).find(f);
 return {find,calls,open:async()=>{render();effects.splice(0).forEach(fn=>fn());await new Promise(setImmediate);},text:()=>JSON.stringify(render())};
}
test('fresh component recovers committed receipt using GET only, no file or proof',async()=>{const h=harness();await h.open();assert.match(h.text(),/Importación confirmada: 2/);assert.ok(h.find(n=>n.type==='a'));assert.equal(h.calls.length,1);assert.match(h.calls[0],/receipts\/00000000/);});
test('unknown is uncertainty, manual repeated lookups do not poll or submit',async()=>{const h=harness({status:'unknown'});await h.open();assert.match(h.text(),/podría seguir ejecutándose/);assert.equal(h.calls.length,1);await h.find(n=>n.type==='button').props.onClick();assert.equal(h.calls.length,2);});
test('invalid or unavailable storage performs no receipt query',async()=>{for(const options of [{invalid:true},{blocked:true}]){const h=harness(options);await h.open();assert.equal(h.calls.length,0);assert.match(h.text(),/inválida/);}});
test('connection, authentication, permissions and changed account stay distinct',async()=>{for(const [http,text] of [[401,/Sesión caducada/],[403,/No tienes permisos/],[503,/No se pudo conectar/]]){const h=harness({http});await h.open();assert.match(h.text(),text);}const h=harness({switchUser:true});await h.open();assert.doesNotMatch(h.text(),/confirmada: 2/);assert.match(h.text(),/cuenta ha cambiado/);});
