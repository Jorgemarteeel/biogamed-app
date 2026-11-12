import {test} from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import Module from 'node:module';import {fileURLToPath} from 'node:url';import ts from 'typescript';import React from 'react';
function harness(){
 const slots=[],effects=[],calls=[],routes=[],events=[];let cursor=0,resolve,reject;
 const hooks={...React,useState(initial){const i=cursor++;if(!(i in slots))slots[i]=initial;return [slots[i],v=>slots[i]=typeof v==='function'?v(slots[i]):v];},useRef(initial){const i=cursor++;return slots[i]??={current:initial};},useEffect(effect){const i=cursor++;if(!(i in slots)){slots[i]=true;effects.push(effect);}}};
 global.requestAnimationFrame=fn=>fn();
 const store=new Map([['token','old-fixture-token']]);global.window={localStorage:{getItem:k=>store.get(k)??null,removeItem:k=>store.delete(k)},dispatchEvent:e=>events.push(e.type)};
 const file=fileURLToPath(new URL('../src/components/AccountView.tsx',import.meta.url)),m=new Module(file);m.filename=file;m.paths=Module._nodeModulePaths(path.dirname(file));const old=Module._load;
 try{Module._load=function(r,p,main){if(r==='react')return hooks;if(r==='next/navigation')return {useRouter:()=>({replace:url=>routes.push(url)})};if(r.startsWith('@/components/'))return ()=>null;if(r==='@/services/api')return {__esModule:true,getCurrentUser:async()=>({id:'fixture',name:'Original',email:'fixture@example.com',role:'student'}),default:{patch:(...args)=>{calls.push(['patch',...args]);return new Promise((yes,no)=>{resolve=yes;reject=no;});},post:(...args)=>{calls.push(['post',...args]);return new Promise((yes,no)=>{resolve=yes;reject=no;});}}};return old.call(this,r,p,main);};m._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,file);}finally{Module._load=old;}
 function all(n){return !n||typeof n!=='object'?[]:[n,...React.Children.toArray(n.props?.children).flatMap(all)];}
 const nodes=()=>{cursor=0;return all(m.exports.default());};const find=f=>nodes().find(f);const change=(id,value)=>find(n=>n.props?.id===id).props.onChange({target:{value}});
 return {calls,routes,events,store,find,change,nodes,security:()=>find(n=>n.type==='button'&&n.props.children==='Cambiar contraseña').props.onClick(),open:async()=>{nodes();effects.splice(0).forEach(f=>f());await new Promise(setImmediate);},submit:index=>nodes().filter(n=>n.type==='form')[index].props.onSubmit({preventDefault(){}}),resolve:data=>resolve({data}),reject:e=>reject(e)};
}
test('own name trims, cancels, rejects blank and updates the visible profile explicitly',async()=>{const h=harness();await h.open();h.change('account-name','Discard');h.find(n=>n.type==='button'&&n.props.children==='Cancelar').props.onClick();assert.equal(h.find(n=>n.props?.id==='account-name').props.value,'Original');assert.equal(h.calls.length,0);h.change('account-name','  ');await h.submit(0);assert.equal(h.calls.length,0);h.change('account-name',' Nuevo ñ ');const p=h.submit(0);await h.submit(0);assert.equal(h.calls.length,1);assert.deepEqual(h.calls[0],['patch','/auth/me',{name:'Nuevo ñ'}]);h.resolve({name:'Nuevo ñ',email:'fixture@example.com',role:'student'});await p;assert.equal(h.find(n=>n.props?.id==='account-name').props.value,'Nuevo ñ');assert.ok(h.events.includes('biogamed:role-refresh'));});
test('password mismatch and Unicode length are validated before network; success closes session',async()=>{const h=harness();await h.open();h.security();h.change('account-current','current-fixture');h.change('account-new','ñ'.repeat(72)+'A');h.change('account-confirm','different');await h.submit(1);assert.equal(h.calls.length,0);h.change('account-confirm','ñ'.repeat(72)+'A');const p=h.submit(1);await h.submit(1);assert.equal(h.calls.length,1);assert.equal(h.calls[0][2].new_password.length,73);h.resolve({message:'ok'});await p;assert.equal(h.store.get('token'),undefined);assert.deepEqual(h.routes,['/login?password=changed']);assert.equal(h.find(n=>n.props?.id==='account-new').props.value,'');});
test('wrong current password preserves session and fields with recoverable error',async()=>{const h=harness();await h.open();h.security();h.change('account-current','wrong-fixture');h.change('account-new','new-fixture-password');h.change('account-confirm','new-fixture-password');const p=h.submit(1);h.reject({isAxiosError:true,response:{status:400,data:{detail:'La contraseña actual no es correcta.'}}});await p;assert.equal(h.store.get('token'),'old-fixture-token');assert.equal(h.routes.length,0);assert.match(h.find(n=>n.props?.role==='alert').props.children,/actual no es correcta/);});

test('account data groups readonly details and save only enables a valid changed name',async()=>{
 const h=harness();await h.open();const save=()=>h.find(n=>n.type==='button'&&n.props.children==='Guardar');
 assert.equal(save().props.disabled,true);await h.submit(0);assert.equal(h.calls.length,0);h.change('account-name',' Original ');assert.equal(save().props.disabled,true);
 h.change('account-name','  ');assert.equal(save().props.disabled,true);assert.ok(h.find(n=>n.props?.role==='alert'));
 h.change('account-name','x'.repeat(256));assert.equal(save().props.disabled,true);
 h.change('account-name','Nuevo');assert.equal(save().props.disabled,false);
 assert.equal(h.nodes().filter(n=>n.type==='section').length,2);
 assert.equal(h.nodes().filter(n=>n.type==='input').length,1);
});
test('password disclosure, per-field visibility and cancellation preserve independent forms',async()=>{
 const h=harness();await h.open();assert.equal(h.nodes().filter(n=>n.type==='form').length,1);h.security();
 assert.equal(h.nodes().filter(n=>n.type==='form').length,2);
 for(const [id,label] of [['account-current','contraseña actual'],['account-new','nueva contraseña'],['account-confirm','confirmación de contraseña']]){
  h.change(id,'synthetic-fixture');const toggle=h.find(n=>n.props?.['aria-label']==='Mostrar '+label);
  assert.equal(toggle.props.type,'button');toggle.props.onClick();assert.equal(h.find(n=>n.props?.id===id).props.type,'text');
  assert.equal(h.find(n=>n.props?.id===id).props.value,'synthetic-fixture');
  h.find(n=>n.props?.['aria-label']==='Ocultar '+label).props.onClick();assert.equal(h.find(n=>n.props?.id===id).props.type,'password');
 }
 h.change('account-new','short');await h.submit(1);assert.equal(h.calls.length,0);assert.ok(h.find(n=>n.props?.role==='alert'));
 h.find(n=>n.props?.['aria-label']==='Mostrar contraseña actual').props.onClick();
 h.nodes().filter(n=>n.type==='button'&&n.props.children==='Cancelar')[1].props.onClick();
 assert.equal(h.nodes().filter(n=>n.type==='form').length,1);h.security();
 for(const id of ['account-current','account-new','account-confirm']){assert.equal(h.find(n=>n.props?.id===id).props.value,'');assert.equal(h.find(n=>n.props?.id===id).props.type,'password');}
 assert.equal(h.find(n=>n.props?.role==='alert'),undefined);assert.equal(h.calls.length,0);
});
