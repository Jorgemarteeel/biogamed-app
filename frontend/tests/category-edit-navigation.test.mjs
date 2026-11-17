import {test} from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";import Module from "node:module";import path from "node:path";import {fileURLToPath} from "node:url";import ts from "typescript";
test("legacy category route delegates to the same catalog and keeps explicit hierarchy and old format",()=>{
 const filename=fileURLToPath(new URL("../src/components/CategoryQuestionsView.tsx",import.meta.url));const m=new Module(filename);m.filename=filename;m.paths=Module._nodeModulePaths(path.dirname(filename));const original=Module._load;
 try{Module._load=function(r,p,main){if(r==="@/components/QuestionManagement")return "SharedManagement";return original.call(this,r,p,main);};m._compile(ts.transpileModule(fs.readFileSync(filename,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,filename);}finally{Module._load=original;}
 const element=m.exports.default({subjectId:3,blockId:7,categoryId:9,mode:"TRIVIAL",page:2});assert.equal(element.type,"SharedManagement");assert.deepEqual(element.props.initialContext,{subject:3,block:7,category:9});assert.equal(element.props.initialMode,"TRIVIAL");
});
