import {test} from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import Module from "node:module";
import path from "node:path";
import {fileURLToPath} from "node:url";
import React from "react";
import ts from "typescript";

function harness(){
  const slots=[],effects=[],calls=[],reads=[],getRequests=[];
  let cursor=0;
  const hooks={...React,useCallback:fn=>fn,useRef(v){const i=cursor++;return slots[i]??={current:v};},
    useState(v){const i=cursor++;if(!(i in slots))slots[i]=v;return[slots[i],x=>slots[i]=typeof x==="function"?x(slots[i]):x];},
    useEffect(fn,deps){const i=cursor++;if(!slots[i]||deps.some((v,j)=>slots[i][j]!==v)){slots[i]=deps;effects.push(fn);}}};
  const source=fileURLToPath(new URL("../src/app/gestion/contenidos/page.tsx",import.meta.url));
  const m=new Module(source);m.filename=source;m.paths=Module._nodeModulePaths(path.dirname(source));
  const original=Module._load;
  const overview={subject:"Ensayo",year:"2026-2027",topics:[{id:8,name:"Tejidos",icon:null}],board:{slots:["LYMPHOCYTE","MACROPHAGE","SPLEEN","FLASK","DNA"].map((bank,i)=>({bank,label:["Linfocito","Macrófago","Bazo","Matraz","ADN"][i],topic_id:bank==="SPLEEN"?8:null,missing_icon:bank!=="SPLEEN",decks:[1,2,3,4].map(level=>({level,count:bank==="SPLEEN"?level:0}))}))}};
  try{Module._load=function(r,p,main){
    if(r==="react")return hooks;
    if(r==="next/link")return "a";
    if(r==="next/image")return "img";
    if(r.startsWith("@/components/"))return ()=>null;
    if(r==="@/services/api")return {__esModule:true,getCurrentUser:async()=>({role:"teacher",id:"fixture-teacher"}),default:{
      get:async (url,options)=>{reads.push(url);getRequests.push({url,options});return {data:url==="/edition-content/legacy/pending"?{total:25,items:[{id:19,game:"PASAPALABRA",text:options?.params?.skip?"Pregunta sin curso de la segunda página":"Pregunta anterior sin curso"}]}:url.includes("/receipts/")?{status:"confirmed",count:2,subject_id:1,subject:"Ensayo",year:"2026-2027",topic:"Tejidos"}:url.startsWith("/subjects?")?[{id:1,name:"Ensayo"}]:url.startsWith("/academic-editions")?{items:[{id:4,subject_id:1,subject_name:"Ensayo",academic_year:"2026-2027"}]}:url.endsWith("/questions")?{items:[],total:0}:overview};},
      post:async(url,body)=>{calls.push({url,body});return{data:{total:1,valid:1,errors:[],proof:"synthetic",groups:[],preview:[],subject:"Ensayo",year:"2026-2027"}};}
    }};
    return original.call(this,r,p,main);
  };m._compile(ts.transpileModule(fs.readFileSync(source,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,source);
  }finally{Module._load=original;}
  function walk(n){return React.isValidElement(n)?[n,...React.Children.toArray(n.props.children).flatMap(walk)]:[];}
  function nodes(){cursor=0;return walk(m.exports.default());}
  const text=n=>React.isValidElement(n)?React.Children.toArray(n.props.children).map(text).join(""):String(n??"");
  const button=name=>nodes().find(n=>n.type==="button"&&text(n)===name);
  const select=(label,value)=>{const parent=nodes().find(n=>n.type==="label"&&text(n).startsWith(label));walk(parent).find(n=>n.type==="select").props.onChange({target:{value}});};
  const flush=async()=>{nodes();effects.splice(0).forEach(fn=>fn());await new Promise(setImmediate);};
  return{nodes,button,select,calls,reads,getRequests,flush,async boot(){await flush();await flush();await flush();select("Asignatura","1");select("Curso académico","4");await flush();await flush();}};
}
test("both CSV entries share validation and pending destination changes require explicit choice",async()=>{
  const h=harness();await h.boot();
  h.button("Importar CSV en esta edición").props.onClick();
  assert.ok(h.nodes().some(n=>n.props?.ref&&n.props?.accept===".csv,text/csv"));
  h.select("Temática","8");await h.flush();
  h.button("Importar CSV en esta temática").props.onClick();
  const input=h.nodes().find(n=>n.type==="input"&&n.props.accept===".csv,text/csv");
  input.props.onChange({target:{files:[new File(["data"],"scoped.csv")]}});
  await h.button("Validar sin guardar").props.onClick();
  assert.equal(h.calls[0].url,"/edition-content/4/validate");
  assert.equal(h.calls[0].body.get("topic_id"),"8");
  h.select("Temática","");
  assert.ok(h.nodes().some(n=>n.props.role==="alertdialog"));
  h.button("Seguir editando").props.onClick();
  assert.ok(h.button("Confirmar importación"));
});
test("reload reads only an operation reference and recovers the original receipt",async t=>{
  const original=globalThis.window;
  const reference={operation:"12345678-1234-1234-1234-123456789abc",edition:4,topic:8};
  const saved=new Map([["biogamed:edition-import:fixture-teacher",JSON.stringify(reference)]]);
  globalThis.window={sessionStorage:{getItem:key=>saved.get(key)||null,setItem:(key,value)=>saved.set(key,value)}};
  t.after(()=>{if(original===undefined)delete globalThis.window;else globalThis.window=original;});
  const h=harness();await h.boot();await h.flush();
  assert.ok(h.nodes().some(n=>n.type==="h2"&&n.props.children==="Importación confirmada"));
  assert.ok(h.button("Ver preguntas importadas"));
  assert.deepEqual(JSON.parse(saved.get("biogamed:edition-import:fixture-teacher")),reference);
  assert.equal(h.calls.length,0);
});
for(const storage of ["invalid","unavailable"]){
  test("recovery handles "+storage+" session storage without confirming",async t=>{
    const original=globalThis.window;
    globalThis.window={sessionStorage:{getItem(){if(storage==="unavailable")throw Error("storage");return "{broken";}}};
    t.after(()=>{if(original===undefined)delete globalThis.window;else globalThis.window=original;});
    const h=harness();await h.boot();
    assert.ok(h.nodes().some(n=>n.props.role==="status"&&typeof n.props.children==="string"&&n.props.children.includes("almacenamiento")));
    assert.equal(h.calls.length,0);
  });
}

test("neutral board labels preserve bank mappings and unassigned questions remain accessible",async()=>{
  const h=harness();await h.boot();
  const headings=h.nodes().filter(n=>n.type==="th"&&n.props.scope==="row");
  assert.deepEqual(headings.map(n=>n.props.children),[1,2,3,4,5].map(n=>"Tipo de casilla "+n));
  const spleen=h.nodes().find(n=>n.type==="select"&&n.props["aria-label"]==="Temática de Tipo de casilla 3");
  assert.equal(spleen.props.value,8);
  const row=h.nodes().find(n=>n.type==="tr"&&React.Children.toArray(n.props.children).some(c=>c.props.children==="Tipo de casilla 3"));
  assert.ok(React.Children.toArray(row.props.children).some(n=>n.props.children==="Disponible"));
  assert.deepEqual(React.Children.toArray(row.props.children).slice(3).map(n=>n.props.children),[1,2,3,4]);
  assert.ok(h.nodes().some(n=>n.type==="h2"&&n.props.children==="Preguntas sin curso asignado"));
  await h.button("Ver preguntas sin curso asignado").props.onClick();await h.flush();
  assert.ok(h.reads.includes("/edition-content/legacy/pending"));
  assert.ok(h.nodes().some(n=>n.type==="li"&&React.Children.toArray(n.props.children).includes("Pregunta anterior sin curso")));
});

test("unassigned question pagination loads the requested page without hiding the list",async()=>{
  const h=harness();await h.boot();
  await h.button("Ver preguntas sin curso asignado").props.onClick();await h.flush();
  await h.button("Página siguiente").props.onClick();await h.flush();
  assert.equal(h.getRequests.filter(r=>r.url==="/edition-content/legacy/pending").at(-1).options.params.skip,20);
  assert.ok(h.nodes().some(n=>n.type==="li"&&React.Children.toArray(n.props.children).includes("Pregunta sin curso de la segunda página")));
  await h.button("Página anterior").props.onClick();await h.flush();
  assert.equal(h.getRequests.filter(r=>r.url==="/edition-content/legacy/pending").at(-1).options.params.skip,0);
  assert.ok(h.nodes().some(n=>n.type==="li"&&React.Children.toArray(n.props.children).includes("Pregunta anterior sin curso")));
});
