import './helpers/academic-aliases.mjs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import Module from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import ts from 'typescript';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';

function load(relative, mocks={}) {
  const filename=fileURLToPath(new URL(relative,import.meta.url));
  const mod=new Module(filename);mod.filename=filename;mod.paths=Module._nodeModulePaths(path.dirname(filename));
  const original=Module._load;
  Module._load=function(request,parent,main){return request in mocks?mocks[request]:original.call(this,request,parent,main);};
  try {
    mod._compile(ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,filename);
    return mod.exports.default;
  } finally {Module._load=original;}
}
const Illustration=load('../src/components/GameIllustration.tsx');
const ChoiceCards=load('../src/components/GameChoiceCards.tsx',{'@/components/GameIllustration':Illustration});
const mocks={
  'next/link':({children,...props})=>React.createElement('a',props,children),
  'next/image':({alt,...props})=>React.createElement('img',{alt,...props}),
  'next/navigation':{useRouter:()=>({push:()=>{throw Error('No navigation during rendering');}})},
  '@/components/Brand':()=>React.createElement('a',{href:'/'},'BioGaMed'),
  '@/components/GameIllustration':Illustration,
  '@/components/GameChoiceCards':ChoiceCards,
  '@/services/api':{getTopics:()=>{throw Error('The landing must not request a question bank');}},
  '@/lib/topic-presentation':{topicIllustration:()=>''},
};
const Home=load('../src/app/page.tsx',mocks);
const Picker=load('../src/components/GamePicker.tsx',mocks);
const html=renderToStaticMarkup(React.createElement(Home));

test('public landing describes academic preparation and both Pasapalabra modes with existing entry points',()=>{
  assert.match(html,/Dos juegos para practicar/);
  assert.ok(html.includes('Elige los contenidos de tu asignatura y practica con Trivial o Pasapalabra. Consulta después tus resultados'));
  for(const text of ['Elige qué practicar','asignatura, bloque y categoría','Prepara tu partida','Consulta tus resultados','evolución de partidas comparables','de forma individual','rosco numerado','con un invitado','en línea con otra cuenta'])assert.ok(html.includes(text),text);
  for(const href of ['/practicar','/login','/registro','#modalidades'])assert.ok(html.includes(`href="${href}"`),href);
  assert.doesNotMatch(html,/Selecciona el tema|Al terminar Trivial|Empieza por L|Pasapalabra local y consulta|Disponible/);
});

test('landing and existing selector render the exact same shared illustrations',()=>{
  const picker=renderToStaticMarkup(React.createElement(Picker));
  for(const mode of ['TRIVIAL','PASAPALABRA']){
    const svg=renderToStaticMarkup(React.createElement(Illustration,{mode}));
    assert.ok(html.includes(svg),mode+' landing');
    assert.ok(picker.includes(svg),mode+' selector');
  }
});

test('examples explain options and a numbered clue without pretending to be playable',()=>{
  const cards=[...html.matchAll(/<article\b[^>]*>([\s\S]*?)<\/article>/g)].map(x=>x[1]);
  assert.equal(cards.length,2);
  for(const card of cards){assert.ok(card.includes('Ejemplo ilustrativo · No es una partida'));assert.doesNotMatch(card,/<(?:button|input|select)\b|role="(?:button|radio)"/);}
  assert.match(cards[0],/Opciones del ejemplo de Trivial/);
  for(const option of ['Plasmocitos','Eritrocitos','Plaquetas'])assert.ok(cards[0].includes(option));
  assert.match(cards[1],/Casilla 7/);
  assert.match(cards[1],/Pista: Unidad básica de los seres vivos/);
});