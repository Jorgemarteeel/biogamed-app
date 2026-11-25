import {test} from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import Module from "node:module";
import path from "node:path";
import {fileURLToPath} from "node:url";
import React from "react";
import ts from "typescript";
function harness(available=40){
 let cursor=0;const slots=[],effects=[],calls=[],routes=[];
 const hooks={...React,useState(v){const i=cursor++;if(!(i in slots))slots[i]=v;return[slots[i],x=>slots[i]=typeof x==="function"?x(slots[i]):x];},useRef(v){const i=cursor++;return slots[i]??={current:v};},useEffect(fn,deps){const i=cursor++;if(!slots[i]||deps.some((v,j)=>v!==slots[i][j])){slots[i]=deps;effects.push(fn);}}};
 const source=fileURLToPath(new URL("../src/components/EnrollmentPasapalabra.tsx",import.meta.url)),m=new Module(source);m.filename=source;m.paths=Module._nodeModulePaths(path.dirname(source));
 const load=Module._load;
 try{Module._load=function(r,p,main){
  if(r==="react")return hooks;if(r==="next/navigation")return{useRouter:()=>({push:url=>routes.push(url)})};if(r==="next/image")return "img";
  if(r==="@/services/api")return{__esModule:true,default:{get:async url=>({data:url.endsWith("/subjects")?[{id:3,name:"Physiology",academic_year:"2026-2027"}]:{academic_year:"2026-2027",topics:[{id:8,name:"Vocabulary",icon:null,levels:[{level:1,available}]}]}}),post:async(url,body)=>{calls.push({url,body});return{data:url.endsWith("preparations")?{can_start:available>=40,available,academic:{academic_year:"2026-2027"}}:{id:15}};}}};
  if(r==="@/components/Pasapalabra")return{Frame:"frame"};if(r==="@/components/PasapalabraOnline")return{PasapalabraEntry:"join"};if(r==="@/components/MonitoringGameSelect")return "select";if(r==="@/components/PasapalabraModePicker")return "mode-picker";
  return load.call(this,r,p,main);
 };m._compile(ts.transpileModule(fs.readFileSync(source,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,source);}finally{Module._load=load;}
 const walk=n=>React.isValidElement(n)?[n,...React.Children.toArray(n.props.children).flatMap(walk)]:[];
 const nodes=()=>{cursor=0;return walk(m.exports.default());};
 const flush=async()=>{nodes();effects.splice(0).forEach(f=>f());await new Promise(setImmediate);};
 const button=name=>nodes().find(n=>n.type==="button"&&n.props.children===name);
 const select=(label,v)=>nodes().find(n=>n.type==="select"&&n.props.label===label).props.onValueChange(v);
 return{nodes,flush,button,select,calls,routes,async boot(){await flush();await flush();select("Asignatura","3");await flush();await flush();select("Temática","8");}};
}
test("enrollment preparation confirms registered companion without replacing host or persisting credentials",async t=>{
 const previous=globalThis.window,urls=[];globalThis.window={location:{search:""},history:{replaceState:(a,b,url)=>urls.push(url)}};t.after(()=>{globalThis.window=previous;});
 const h=harness();await h.boot();await h.button("Continuar a modalidad").props.onClick();await h.flush();
 h.nodes().find(n=>n.type==="mode-picker").props.onSelect("LOCAL");
 const inputs=h.nodes().filter(n=>n.type==="input");inputs[0].props.onChange({target:{value:"synthetic-dni"}});inputs[1].props.onChange({target:{value:"synthetic-password"}});
 h.nodes().find(n=>n.type==="form").props.onSubmit({preventDefault(){}});await h.flush();
 assert.deepEqual(h.routes,["/pasapalabra/15"]);
 const request=h.calls.find(r=>r.url.endsWith("/local/start"));assert.equal(request.body.subject_id,3);assert.equal(request.body.topic_id,8);assert.equal(request.body.difficulty,1);assert.equal(request.body.guest_password,"synthetic-password");
 assert.equal(h.nodes().find(n=>n.type==="input"&&n.props.type==="password").props.value,"");assert.ok(urls.every(url=>!url.includes("synthetic")));
});
test("insufficient theme and level blocks mode preparation without changing filters",async t=>{
 const previous=globalThis.window;globalThis.window={location:{search:""},history:{replaceState(){}}};t.after(()=>{globalThis.window=previous;});const h=harness(39);await h.boot();assert.equal(h.button("Continuar a modalidad").props.disabled,true);assert.equal(h.calls.length,0);
});
