import './helpers/academic-aliases.mjs';
import {test} from 'node:test';
import React from 'react';
import assert from 'node:assert/strict';
import fs from 'node:fs';import Module from 'node:module';import path from 'node:path';import {fileURLToPath} from 'node:url';import ts from 'typescript';
const file=fileURLToPath(new URL('../src/lib/navigation-return.ts',import.meta.url));const m=new Module(file);m.filename=file;m.paths=Module._nodeModulePaths(path.dirname(file));m._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,file);
const {screenTrail,screenReturn,readTrail,safeScreen}=m.exports;
test('history page, detail, match and back preserve the entire route after reload',()=>{
 let trail=[];for(const url of ['/dashboard','/historial?page=3','/partidas/58','/pasapalabra/30'])trail=screenTrail(trail,url);
 trail=readTrail(JSON.stringify(trail));assert.equal(screenReturn(trail,'/pasapalabra/30','/historial'),'/partidas/58');
 trail=screenTrail(trail,'/partidas/58');assert.equal(screenReturn(trail,'/partidas/58','/historial'),'/historial?page=3');
 trail=screenTrail(trail,'/historial?page=3');assert.equal(screenReturn(trail,'/historial?page=3','/dashboard'),'/dashboard');
});
test('query and paging edits are not extra screens; latest filters are recovered',()=>{
 let trail=[];for(const url of ['/dashboard','/seguimiento?game=TRIVIAL','/seguimiento?game=PASAPALABRA&start=2026-11-01','/seguimiento/dificultades?game=PASAPALABRA&minimum=5'])trail=screenTrail(trail,url);
 assert.equal(trail.length,3);assert.equal(screenReturn(trail,trail.at(-1),'/dashboard'),'/seguimiento?game=PASAPALABRA&start=2026-11-01');
});
test('management, account and progress retain their actual origin and list page',()=>{
 for(const [parent,child] of [['/gestion/asignaturas?page=2','/gestion/asignaturas/4'],['/gestion/asignaturas/4?page=3','/gestion/asignaturas/4/bloques/5'],['/progreso','/partidas/57'],['/historial?page=2','/cuenta']]){
 const trail=screenTrail(screenTrail([],parent),child);assert.equal(screenReturn(trail,child,'/dashboard'),parent);
 }
});
test('direct or unknown entry uses safe fallback, never arbitrary external destinations',()=>{
 assert.equal(screenReturn([],'/partidas/57','/historial'),'/historial');
 assert.equal(screenReturn(['/dashboard','/cuenta'],'/partidas/57','/historial'),'/historial');
 for(const value of ['https://evil.test','//evil.test','/\\evil.test','javascript:alert(1)','/unknown'])assert.equal(safeScreen(value),null);
 assert.deepEqual(readTrail('not json'),[]);assert.deepEqual(readTrail('["//evil.test"]'),[]);
 assert.equal(safeScreen('/historial?page=2&token=private'),'/historial?page=2');
});
test('started room redirect does not trap back in a redirect loop',()=>{
 let trail=[];for(const url of ['/dashboard','/practicar?subject=4','/pasapalabra/rooms/16','/pasapalabra/26'])trail=screenTrail(trail,url);
 assert.equal(screenReturn(trail,trail.at(-1),'/historial'),'/practicar?subject=4');assert.equal(trail.length,3);
});
test('logout/login resets tab origins and trail is bounded',()=>{
 assert.deepEqual(screenTrail(['/dashboard','/cuenta'],'/login'),[]);
 let trail=[];for(let i=1;i<40;i++)trail=screenTrail(trail,`/partidas/${i}`);assert.equal(trail.length,25);
 assert.equal(screenReturn(readTrail(JSON.stringify(trail)),trail.at(-1),'/historial'),'/partidas/38');
});


function integration(initial,blocked=false){
 let current='/dashboard';const previous=[global.window,global.sessionStorage];const saved=new Map(initial?[['biogamed-screen-trail-v1',JSON.stringify(initial)]]:[]);
 global.sessionStorage={getItem:k=>{if(blocked)throw Error('blocked');return saved.get(k)??null;},setItem:(k,v)=>{if(blocked)throw Error('blocked');saved.set(k,v);},removeItem:k=>saved.delete(k)};
 const filename=fileURLToPath(new URL('../src/components/ReturnLink.tsx',import.meta.url)),mod=new Module(filename);mod.filename=filename;mod.paths=Module._nodeModulePaths(path.dirname(filename));const old=Module._load;
 try{Module._load=function(r,parent,main){if(r==='react')return{...React,useEffect:f=>f(),useSyncExternalStore:(subscribe,get)=>get()};if(r==='next/link')return 'a';if(r==='next/navigation')return{usePathname:()=>new URL(current,'http://local').pathname,useSearchParams:()=>new URL(current,'http://local').searchParams};if(r==='@/lib/navigation-return')return m.exports;return old.call(this,r,parent,main);};mod._compile(ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,filename);}finally{Module._load=old;}
 return{navigate(url){current=url;const parsed=new URL(url,'http://local');global.window={location:{pathname:parsed.pathname,search:parsed.search}};mod.exports.NavigationObserver();},link(fallback){return mod.exports.default({href:fallback,children:'Volver al panel',className:'text-link'});},saved,close(){[global.window,global.sessionStorage]=previous;}};
}
test('observer and real return component recover history page through detail and match',()=>{const h=integration();try{for(const url of ['/dashboard','/historial?page=3','/partidas/58','/pasapalabra/30'])h.navigate(url);assert.equal(h.link('/historial').props.href,'/partidas/58');h.navigate('/partidas/58');assert.equal(h.link('/historial').props.href,'/historial?page=3');assert.equal(h.link('/historial').props.children,'← Volver');}finally{h.close();}});
test('reload restores origin; blocked storage still permits memory-only back',()=>{for(const blocked of [false,true]){const h=integration(['/dashboard','/historial?page=3','/partidas/58'],blocked);try{h.navigate('/partidas/58');assert.equal(h.link('/historial').props.href,blocked?'/historial':'/historial?page=3');h.navigate('/cuenta');assert.equal(h.link('/dashboard').props.href,'/partidas/58');}finally{h.close();}}});
test('old preparation query keeps topicId and account switch clears origins',()=>{const h=integration();try{h.navigate('/dashboard');h.navigate('/game?topicId=4&mode=PASAPALABRA&play=LOCAL');h.navigate('/pasapalabra/30');assert.equal(h.link('/historial').props.href,'/game?topicId=4&mode=PASAPALABRA&play=LOCAL');h.navigate('/login');assert.equal(h.saved.size,0);h.navigate('/cuenta');assert.equal(h.link('/dashboard').props.href,'/dashboard');}finally{h.close();}});

test('InmunoQuest return restores management or category origin and filters after reload',()=>{for(const origin of ['/gestion/asignaturas?page=2','/gestion/asignaturas/1/bloques/2/categorias/3?mode=TRIVIAL&page=4']){let trail=screenTrail([],origin);trail=screenTrail(trail,'/gestion/inmunoquest?subject=1&block=2&category=3');trail=readTrail(JSON.stringify(trail));assert.equal(screenReturn(trail,trail.at(-1),'/gestion/asignaturas'),origin);}});
