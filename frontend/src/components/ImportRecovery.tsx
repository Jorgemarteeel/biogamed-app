"use client";
import {useCallback,useEffect,useRef,useState} from 'react';
import {isAxiosError} from 'axios';
import Link from 'next/link';
import api,{getCurrentUser} from '@/services/api';
import {readReference,type ImportReference} from '@/lib/import-recovery';
export default function ImportRecovery({subjectId,blockId,categoryId,refresh=0}:{subjectId:number;blockId:number;categoryId:number;refresh?:number}){
 const [message,setMessage]=useState(''),[confirmed,setConfirmed]=useState(false),[busy,setBusy]=useState(false);
 const reference=useRef<ImportReference|null>(null),locked=useRef(false);
 const base=`/subjects/${subjectId}/blocks/${blockId}/categories/${categoryId}/imports`;
 const query=useCallback(async()=>{
  if(locked.current)return;locked.current=true;setBusy(true);setConfirmed(false);setMessage('Consultando resultado…');
  try{const user=await getCurrentUser();reference.current=readReference(window.sessionStorage,user.id,subjectId,blockId,categoryId);
   if(!reference.current){setMessage('');return;}
   const {data}=await api.get<{status:string;count?:number}>(`${base}/receipts/${reference.current.operationId}`);
   // Recheck identity before presenting a result from an earlier authenticated request.
   const current=await getCurrentUser();if(current.id!==user.id || !['teacher','admin'].includes(current.role)){setMessage('La cuenta ha cambiado. Consulta de nuevo con tu cuenta.');return;}
   if(data.status==='confirmed'){setConfirmed(true);setMessage(`Importación confirmada: ${data.count} ${data.count===1?"pregunta":"preguntas"}.`);}
   else setMessage('Todavía no se puede acreditar el resultado. La confirmación original podría seguir ejecutándose.');
  }catch(error){const status=isAxiosError(error)?error.response?.status:undefined;
   setMessage(status===401?'Sesión caducada. Inicia sesión para consultar el resultado.':status===403?'No tienes permisos para consultar la importación.':isAxiosError(error)?'No se pudo conectar para consultar el resultado. Conservamos la referencia.':'La referencia de recuperación no está disponible o es inválida. No se reenviará ninguna importación.');
  }finally{locked.current=false;setBusy(false);}
 },[base,subjectId,blockId,categoryId]);
 useEffect(()=>{let active=true;Promise.resolve().then(()=>{if(active)void query();});return()=>{active=false;};},[query,refresh]); // one lookup per category/change; never polling
 return message?<section aria-label="Recuperación de importación" className="notice-warning mt-4" aria-busy={busy}><p role="status">{message}</p>{confirmed?<Link className="text-link min-h-11 inline-flex items-center" href="#question-list-heading">Ver listado de preguntas</Link>:<button type="button" className="button-secondary mt-3" disabled={busy} onClick={()=>void query()}>Consultar de nuevo</button>}</section>:null;
}
