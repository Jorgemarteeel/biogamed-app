import {test} from 'node:test';
import assert from 'node:assert/strict';
import {harness} from './helpers/question-management.mjs';
const question={id:7,text:'Synthetic question',reference_answer:'Reference',bank:'SPLEEN',difficulty:2,note_reference:'T3',is_active:true,question_type:'INMUNOQUEST',subject_id:1,block_id:null,category_id:null};
test('students do not load private catalog, import forms or coverage',async()=>{const h=harness({role:'student'});await h.boot();assert.equal(h.calls.length,0);assert.equal(h.nodes().some(n=>n.type==='form'),false);});
test('catalog is paginated; direct URL preserves all applied filters',async()=>{const h=harness({query:'subject=1&mode=INMUNOQUEST&difficulty=2&state=active&bank=SPLEEN&page=3'});await h.boot();const c=h.calls.find(c=>c.url==='/questions/catalog');assert.equal(c.config.params.skip,40);assert.equal(c.config.params.subject_id,1);assert.equal(c.config.params.bank,'SPLEEN');assert.equal(c.config.params.difficulty,2);assert.ok(h.calls.some(c=>c.url==='/inmunoquest/coverage'&&c.config.params.subject_id===1));});
test('editing filters does not query; explicit consultation retains context and resets page',async()=>{const h=harness({query:'subject=1&page=2'});await h.boot();const count=h.calls.length;h.find(n=>n.props?.label==='Juego o formato').props.onValueChange('PASAPALABRA');assert.equal(h.calls.length,count);h.find(n=>n.props?.['aria-label']==='Filtros de preguntas').props.onSubmit({preventDefault(){}});const p=new URLSearchParams(h.routes.at(-1).split('?')[1]);assert.equal(p.get('subject'),'1');assert.equal(p.get('mode'),'PASAPALABRA');assert.equal(p.has('page'),false);});
test('unassigned clears academic filters and bank is removed when changing game',async()=>{const h=harness({query:'subject=1&block=2&category=3&mode=INMUNOQUEST&bank=SPLEEN'});await h.boot();h.find(n=>n.props?.label==='Clasificación').props.onValueChange('unassigned');h.find(n=>n.props?.label==='Juego o formato').props.onValueChange('PASAPALABRA');h.find(n=>n.props?.['aria-label']==='Filtros de preguntas').props.onSubmit({preventDefault(){}});const p=new URLSearchParams(h.routes.at(-1).split('?')[1]);assert.equal(p.get('classification'),'unassigned');assert.equal(p.has('subject'),false);assert.equal(p.has('bank'),false);});
test('question and CSV forms are exclusive; toggling preserves draft without saving',async()=>{const h=harness();await h.boot();h.button('Crear pregunta').props.onClick({currentTarget:{focus(){}}});h.find(n=>n.type==='textarea').props.onChange({target:{value:'Draft'}});h.button('Importar CSV').props.onClick({currentTarget:{focus(){}}});const editor=h.find(n=>n.type==='section'&&n.props.hidden===true);assert.ok(editor);h.button('Crear pregunta').props.onClick({currentTarget:{focus(){}}});assert.equal(h.find(n=>n.type==='textarea').props.value,'Draft');assert.equal(h.calls.some(c=>c.method!=='get'),false);});
test('edit and cancel retain list URL; save sends explicit destination without Topic for open questions',async()=>{const h=harness({questions:[question],total:41,query:'subject=1&page=2&difficulty=2'});await h.boot();h.button('Editar').props.onClick({currentTarget:{focus(){}}});const old=global.window;global.window={confirm:()=>true};try{h.button('Cancelar').props.onClick({currentTarget:{focus(){}}});assert.equal(h.routes.length,0);h.button('Editar').props.onClick({currentTarget:{focus(){}}});await h.find(n=>n.type==='form'&&!n.props['aria-label']).props.onSubmit({preventDefault(){}});const request=h.calls.find(c=>c.method==='put');assert.equal(request.url,'/questions/manage/7');assert.equal(request.data.subject_id,1);assert.equal(request.data.category_id,null);assert.equal('topic_id' in request.data,false);assert.equal(h.routes.length,0);}finally{global.window=old;}});
test('no manual question selection, activities or targets remain in management',async()=>{const h=harness({questions:[question]});await h.boot();assert.equal(h.nodes().some(n=>n.type==='input'&&n.props.type==='checkbox'),false);assert.equal(h.calls.some(c=>c.url.includes('configurations')),false);assert.ok(h.find(n=>n.props?.['aria-label']==='Disponibilidad de Trivial'));});

test('reload restores only the import destination and opens receipt recovery, never resends a file',async()=>{const h=harness({query:'action=import&importSubject=7&importBlock=0&importCategory=0&importMode=PASAPALABRA'});await h.boot();const importer=h.find(n=>String(n.type).endsWith('/QuestionImportForm'));const recovery=h.find(n=>String(n.type).endsWith('/ImportRecovery'));assert.equal(importer.props.subjectId,7);assert.equal(importer.props.fixedMode,'PASAPALABRA');assert.equal(recovery.props.subjectId,7);assert.equal(h.calls.some(c=>c.method!=='get'),false);});

test('opening CSV from a Pasapalabra filter stores the same format in URL and recovery',async()=>{
 const h=harness({query:'mode=PASAPALABRA&subject=1'});await h.boot();h.button('Importar CSV').props.onClick({currentTarget:{focus(){}}});
 const p=new URL(h.routes.at(-1),'http://local').searchParams;
 assert.equal(p.get('importMode'),'PASAPALABRA');assert.equal(h.find(n=>String(n.type).endsWith('/QuestionImportForm')).props.fixedMode,'PASAPALABRA');
});
test('changing CSV game and destination preserves the separate question editor draft',async()=>{
 const h=harness();await h.boot();const old=global.window;global.window={confirm:()=>true};try{
 h.button('Crear pregunta').props.onClick({currentTarget:{focus(){}}});h.find(n=>n.type==='textarea').props.onChange({target:{value:'Independent open draft'}});
 h.nodes().filter(n=>String(n.type).endsWith('/AcademicDestination'))[1].props.onChange({subject:1,block:0,category:0});
 h.button('Importar CSV').props.onClick({currentTarget:{focus(){}}});h.find(n=>n.props?.label==='Juego para importar').props.onValueChange('PASAPALABRA');
 h.nodes().filter(n=>String(n.type).endsWith('/AcademicDestination'))[2].props.onChange({subject:2,block:0,category:0});
 h.button('Crear pregunta').props.onClick({currentTarget:{focus(){}}});assert.equal(h.find(n=>n.type==='textarea').props.value,'Independent open draft');assert.equal(h.find(n=>n.props?.label==='Juego de la pregunta').props.value,'INMUNOQUEST');
 assert.equal(h.nodes().filter(n=>String(n.type).endsWith('/AcademicDestination'))[1].props.value.subject,1);
 h.button('Importar CSV').props.onClick({currentTarget:{focus(){}}});const form=h.find(n=>String(n.type).endsWith('/QuestionImportForm'));assert.equal(form.props.fixedMode,'PASAPALABRA');assert.equal(form.props.subjectId,2);assert.equal(h.calls.some(c=>c.method!=='get'),false);
 }finally{global.window=old;}
});
test('CSV busy state disables external destination, game, query, actions and pagination',async()=>{
 const h=harness({total:49});await h.boot();h.button('Importar CSV').props.onClick({currentTarget:{focus(){}}});h.find(n=>String(n.type).endsWith('/QuestionImportForm')).props.onBusyChange(true);
 for(const name of ['Crear pregunta','Importar CSV','Consultar','Siguiente'])assert.equal(h.button(name).props.disabled,true);
 assert.equal(h.find(n=>n.props?.label==='Juego para importar').props.disabled,true);
 assert.equal(h.nodes().filter(n=>String(n.type).endsWith('/AcademicDestination')).at(-1).props.disabled,true);
 const count=h.routes.length;h.find(n=>n.props?.['aria-label']==='Filtros de preguntas').props.onSubmit({preventDefault(){}});assert.equal(h.routes.length,count);
 h.find(n=>String(n.type).endsWith('/QuestionImportForm')).props.onBusyChange(false);assert.equal(h.button('Crear pregunta').props.disabled,false);
});
test('paging preserves the minimal import destination needed after reload',async()=>{
 const h=harness({query:'subject=1',total:49});await h.boot();h.button('Importar CSV').props.onClick({currentTarget:{focus(){}}});h.find(n=>String(n.type).endsWith('/QuestionImportForm')).props.onDraftChange(true);h.button('Siguiente').props.onClick();
 const p=new URL(h.routes.at(-1),'http://local').searchParams;assert.equal(p.get('page'),'2');assert.equal(p.get('importSubject'),'1');assert.equal(p.get('action'),'import');assert.equal(p.get('importMode'),'INMUNOQUEST');
});

test('board format is named Trivial in catalog, editor and importer without changing internal values',async()=>{
 const h=harness();await h.boot();
 const options=h.find(n=>n.props?.label==='Juego o formato').props.options;
 assert.equal(options.find(o=>o.value==='INMUNOQUEST').label,'Trivial');
 assert.match(options.find(o=>o.value==='TRIVIAL').label,/Trivial individual/);
 h.button('Crear pregunta').props.onClick({currentTarget:{focus(){}}});
 assert.equal(h.find(n=>n.props?.label==='Juego de la pregunta').props.options.find(o=>o.value==='INMUNOQUEST').label,'Trivial');
 h.button('Importar CSV').props.onClick({currentTarget:{focus(){}}});
 assert.equal(h.find(n=>n.props?.label==='Juego para importar').props.options.find(o=>o.value==='INMUNOQUEST').label,'Trivial');
});
