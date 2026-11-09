import Module from "node:module";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import ts from "typescript";
const original=Module._load;
Module._load=function(request,parent,main){
  if(!["@/lib/academic","@/lib/category-presentation","@/components/BackLink","@/components/AcademicContext","@/components/GameChoiceCards","@/components/GameIllustration","@/components/PasapalabraModePicker"].includes(request))return original.call(this,request,parent,main);
  const filename=fileURLToPath(new URL(`../../src/${request.slice(2)}${request.includes("components/")?".tsx":".ts"}`,import.meta.url));
  const mod=new Module(filename);mod.filename=filename;mod.paths=Module._nodeModulePaths(path.dirname(filename));
  mod._compile(ts.transpileModule(fs.readFileSync(filename,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,filename);
  return mod.exports;
};
