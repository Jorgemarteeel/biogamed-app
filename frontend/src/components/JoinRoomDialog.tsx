"use client";
import {useEffect,useRef} from "react";
import {PasapalabraEntry} from "@/components/PasapalabraOnline";
export default function JoinRoomDialog({onClose}:{onClose:()=>void}){
 const dialog=useRef<HTMLDialogElement>(null);
 useEffect(()=>{const node=dialog.current;const previous=document.activeElement as HTMLElement|null;node?.showModal();return()=>{node?.close();previous?.focus();};},[]);
 return <dialog ref={dialog} aria-label="Unirme con código" onCancel={onClose} className="m-auto max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-lg overflow-y-auto rounded-2xl border border-slate-300 bg-white p-5 text-slate-900 shadow-xl backdrop:bg-slate-950/50"><div className="mb-3 flex justify-end"><button className="button-secondary" onClick={onClose}>Cerrar</button></div><PasapalabraEntry compact/></dialog>;
}
