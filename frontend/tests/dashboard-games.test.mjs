import {test} from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import Module from "node:module";
import path from "node:path";
import {fileURLToPath} from "node:url";
import React from "react";
import {renderToStaticMarkup} from "react-dom/server";
import ts from "typescript";
const file=fileURLToPath(new URL("../src/components/DashboardGames.tsx",import.meta.url));
const m=new Module(file);m.filename=file;m.paths=Module._nodeModulePaths(path.dirname(file));
const original=Module._load;
try{Module._load=function(r,p,main){
 if(r==="next/link")return function MockLink({children,...props}){return React.createElement("a",props,children);};
 if(r==="next/image")return function MockImage({src,alt}){return React.createElement("img",{src,alt});};
 if(r.endsWith(".module.css"))return {};
 return original.call(this,r,p,main);
};m._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,file);}finally{Module._load=original;}
const html=renderToStaticMarkup(React.createElement(m.exports.default));
test("game cards identify both games through original images, descriptions and readable clue",()=>{
 assert.equal((html.match(/<article/g)||[]).length,2);
 assert.match(html,/Rosco de letras/);assert.match(html,/Tablero con recorrido/);
 assert.match(html,/Vaso que sale del corazón/);assert.match(html,/Resuelve pistas y completa el rosco/);assert.match(html,/Tira el dado, responde preguntas/);
});
test("only Pasapalabra offers a preparation action; future board is not an actionable control",()=>{
 assert.equal((html.match(/<a /g)||[]).length,1);assert.match(html,/href="\/pasapalabra"/);assert.match(html,/Preparar Pasapalabra/);
 const board=html.slice(html.indexOf('aria-label="Trivial, próximamente"'));
 assert.match(board,/Próximamente/);assert.doesNotMatch(board,/<a |<button/);
});
