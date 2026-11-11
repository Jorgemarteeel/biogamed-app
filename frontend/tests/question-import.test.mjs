import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';import path from 'node:path';import Module from 'node:module';import {fileURLToPath} from 'node:url';import ts from 'typescript';import React from 'react';
function harness(failTopics=false){
 const effects=[]; global.window={sessionStorage:{setItem(){}}}; const slots=[];let cursor=0,resolve,reject,imports=0;const calls=[];
 const hooks={...React,useEffect(effect){effects.push(effect);},useState(initial){const i=cursor++;if(!(i in slots))slots[i]=initial;return [slots[i],v=>slots[i]=typeof v==='function'?v(slots[i]):v];},useRef(initial){const i=cursor++;return slots[i]??={current:initial};}};
 const file=fileURLToPath(new URL('../src/components/QuestionImportForm.tsx',import.meta.url)),mod=new Module(file);mod.filename=file;mod.paths=Module._nodeModulePaths(path.dirname(file));
 const original=Module._load;
 try{Module._load=function(r,p,m){if(r==='react')return hooks;if(r.startsWith('@/components/'))return ()=>null;if(r==='@/lib/import-recovery')return {writeReference:(storage,value)=>storage.setItem('pending',JSON.stringify(value))};if(r==='@/services/api')return {__esModule:true,default:{post:(...args)=>{calls.push(args);return new Promise((yes,no)=>{resolve=yes;reject=no;});}},getCurrentUser:async()=>({id:'00000000-0000-4000-8000-000000000001',role:'teacher'}),getQuestionTopics:async()=>{if(failTopics)throw new Error('offline');return [{id:1,name:'Ficticia'}];}};return original.call(this,r,p,m);};mod._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,file);}finally{Module._load=original;}
 function all(n){return !n||typeof n!=='object'?[]:[n,...React.Children.toArray(n.props?.children).flatMap(all)];}
 const find=f=>{cursor=0;return all(mod.exports.default({subjectId:1,blockId:2,categoryId:3,onImported:()=>imports++})).find(f);};
 const button=text=>find(n=>n.type==='button'&&React.Children.toArray(n.props.children).join('')===text);
 const selectFile=()=>find(n=>n.props?.id==='import-file').props.onChange({target:{files:[new File(['enunciado'], 'fixture.csv')]}});
 return {open:async()=>{find(()=>false);effects.splice(0).forEach(e=>e());await new Promise(setImmediate);},find,button,selectFile,calls,resolve:data=>resolve({data}),reject:()=>reject(new Error('lost response')),imports:()=>imports};
}
const checked={total:11,valid:11,errors:[],proof:'signed-fixture',preview:Array.from({length:11},(_,i)=>({row:i+2,text:`Ficticia ${i}`,difficulty:null,options:['A','B','C','D'],correct_option_index:0}))};
test('validation is explicit, preview is paginated, changed destination invalidates confirmation',async()=>{
 const h=harness();await h.open();h.find(n=>n.props?.id==='import-topic').props.onValueChange("1");h.selectFile();assert.equal(h.calls.length,0);
 const p=h.button('Validar sin guardar').props.onClick();await h.button('Validar sin guardar').props.onClick();assert.equal(h.calls.length,1);h.resolve(checked);await p;
 assert.equal(h.calls[0][0],'/subjects/1/blocks/2/categories/3/imports/validate');
 assert.ok(h.find(n=>n.props?.['aria-label']==='Páginas de vista previa'));
 h.button('Siguiente').props.onClick();assert.ok(h.find(n=>n.type==='p'&&n.props.children==='Ficticia 10'));assert.equal(h.find(n=>n.type==='p'&&n.props.children==='Ficticia 0'),undefined);
 h.find(n=>n.props?.name==='import-game').props.onValueChange('PASAPALABRA');assert.equal(h.button('Confirmar importación de 11 preguntas'),undefined);
});
test('lost confirmation retries the identical operation without duplicate submission',async()=>{
 const h=harness();await h.open();h.find(n=>n.props?.id==='import-topic').props.onValueChange("1");h.selectFile();let p=h.button('Validar sin guardar').props.onClick();h.resolve(checked);await p;
 p=h.button('Confirmar importación de 11 preguntas').props.onClick();await new Promise(setImmediate);await h.button('Confirmar importación de 11 preguntas').props.onClick();assert.equal(h.calls.length,2);const op=h.calls[1][1].get('operation_id');assert.ok(op);h.reject();await p;
 p=h.button('Confirmar importación de 11 preguntas').props.onClick();await new Promise(setImmediate);assert.equal(h.calls[2][1].get('operation_id'),op);assert.equal(h.calls[2][1].get('proof'),'signed-fixture');h.resolve({count:11,question_ids:[1,2]});await p;assert.equal(h.imports(),1);
});
test('row errors prevent confirmation and replacing the file clears the validation',async()=>{
 const h=harness();await h.open();h.find(n=>n.props?.id==='import-topic').props.onValueChange("1");h.selectFile();const p=h.button('Validar sin guardar').props.onClick();h.resolve({...checked,proof:null,errors:[{row:2,column:'contenido',message:'Duplicado'}]});await p;
 assert.equal(h.button('Confirmar importación de 11 preguntas'),undefined);h.selectFile();assert.equal(h.find(n=>n.props?.['aria-label']==='Resultado de validación'),undefined);
});


test('automatic topic loading exposes a retry only when it fails',async()=>{
 const h=harness(true);await h.open();assert.ok(h.button('Reintentar'));
 assert.equal(h.button('Cargar temáticas'),undefined);
});
test('reload loses confirmation context even though an in-page retry retains it',async()=>{
 const h=harness();await h.open();h.find(n=>n.props?.id==='import-topic').props.onValueChange('1');h.selectFile();
 let p=h.button('Validar sin guardar').props.onClick();h.resolve(checked);await p;
 p=h.button('Confirmar importación de 11 preguntas').props.onClick();await new Promise(setImmediate);h.reject();await p;
 assert.ok(h.button('Confirmar importación de 11 preguntas'));
 const reloaded=harness();await reloaded.open();assert.equal(reloaded.button('Confirmar importación de 11 preguntas'),undefined);
 assert.equal(reloaded.find(n=>n.props?.['aria-label']==='Resultado de validación'),undefined);
 assert.equal(reloaded.calls.length,0);
});

test('unavailable session storage prevents sending confirmation',async()=>{
 const h=harness();await h.open();h.find(n=>n.props?.id==='import-topic').props.onValueChange('1');h.selectFile();let p=h.button('Validar sin guardar').props.onClick();h.resolve(checked);await p;
 global.window.sessionStorage={setItem(){throw new Error('blocked')}};
 await h.button('Confirmar importación de 11 preguntas').props.onClick();assert.equal(h.calls.length,1);
 assert.match(h.find(n=>n.props?.role==='alert').props.children,/No se ha enviado/);
});
