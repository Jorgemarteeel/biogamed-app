"use client";
import {useEffect,useState} from "react";
import api from "@/services/api";
import Select from "@/components/MonitoringGameSelect";
export type AcademicChoice={subject:number;block:number;category:number};
type Option={id:number;name:string;display_name?:string;subject_id?:number|null;block_id?:number|null};
function DestinationField({kind,value,subject,block,disabled,onPick}:{kind:"subject"|"block"|"category";value:number;subject:number;block:number;disabled:boolean;onPick:(option:Option|null)=>void}){
 const [items,setItems]=useState<Option[]>([]),[total,setTotal]=useState(0),[skip,setSkip]=useState(0),[retry,setRetry]=useState(0),[error,setError]=useState(false),[loading,setLoading]=useState(true);
 const context=`${subject}:${block}`;const [loadedContext,setLoadedContext]=useState(context);
 useEffect(()=>{let active=true;const offset=loadedContext===context?skip:0;
 void api.get<{items:Option[];total:number;selected:Option|null}>("/questions/destinations",{params:{kind,subject_id:subject||undefined,block_id:block||undefined,selected_id:value||undefined,skip:offset,limit:100}}).then(({data})=>{if(active){setItems(old=>{const next=[...(offset?old:[]),...data.items,...(data.selected?[data.selected]:[])];return next.filter((v,i)=>next.findIndex(o=>o.id===v.id)===i);});setTotal(data.total);setError(false);setLoading(false);if(loadedContext!==context){setSkip(0);setLoadedContext(context);}}}).catch(()=>{if(active){setError(true);setLoading(false);}});return()=>{active=false;};
 },[kind,subject,block,skip,retry,context,loadedContext,value]);
 const label={subject:"Asignatura",block:"Bloque",category:"Categoría"}[kind];
 return <div className="min-w-0 space-y-1"><Select label={label} name={kind} value={String(value)} disabled={disabled||loading||loadedContext!==context||error} onValueChange={v=>onPick(items.find(i=>i.id===Number(v))??null)} options={[{value:"0",label:`Sin seleccionar ${label.toLowerCase()}`},...items.map(i=>({value:String(i.id),label:i.display_name??i.name}))]}/>{loading&&<p role="status">Cargando {label.toLowerCase()}…</p>}{error&&<p role="alert">No se pudo cargar. <button type="button" className="text-link" onClick={()=>setRetry(n=>n+1)}>Reintentar</button></p>}{skip+100<total&&<button type="button" disabled={disabled} className="text-link min-h-11" onClick={()=>setSkip(skip+100)}>Cargar más {label.toLowerCase()}s</button>}</div>;
}
export default function AcademicDestination({value,onChange,disabled=false}:{value:AcademicChoice;onChange:(value:AcademicChoice)=>void;disabled?:boolean}){
 return <div className="grid min-w-0 gap-3 sm:grid-cols-3"><DestinationField kind="subject" value={value.subject} subject={0} block={0} disabled={disabled} onPick={o=>onChange({subject:o?.id??0,block:0,category:0})}/><DestinationField kind="block" value={value.block} subject={value.subject} block={0} disabled={disabled} onPick={o=>onChange({subject:o?.subject_id??value.subject,block:o?.id??0,category:0})}/><DestinationField kind="category" value={value.category} subject={value.subject} block={value.block} disabled={disabled} onPick={o=>onChange({subject:o?.subject_id??value.subject,block:o?(o.block_id??0):value.block,category:o?.id??0})}/></div>;
}
