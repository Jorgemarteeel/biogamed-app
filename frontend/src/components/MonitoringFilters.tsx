"use client";
import {useId,useRef,useState} from 'react';
import {DayPicker} from 'react-day-picker';
import {es} from 'react-day-picker/locale';
import 'react-day-picker/style.css';
import styles from './MonitoringFilters.module.css';
import {canaryToday,dateISO,dateText,fromISO,parseDate,quickRange,rangeError} from '@/lib/calendar-dates';
function DateField({label,value,onChange}:{label:string;value:string;onChange:(v:string)=>void}) {
 const id=useId(),dialog=useRef<HTMLDialogElement>(null),trigger=useRef<HTMLButtonElement>(null);const [open,setOpen]=useState(false);
 const selected=parseDate(value),today=parseDate(canaryToday())!;
 function close(){dialog.current?.close();}
 return <div className="min-w-0"><label className="block font-semibold" htmlFor={id}>{label}</label><span id={id+'-hint'} className="block text-xs text-slate-600">día/mes/año</span><div className="flex gap-1"><input id={id} className="form-input w-40" type="text" inputMode="numeric" placeholder="dd/mm/aaaa" value={value} aria-describedby={id+'-hint'} aria-invalid={!!value&&!selected} onChange={e=>onChange(e.target.value)}/><button ref={trigger} className="button-secondary" type="button" aria-label={`Abrir calendario de ${label}`} aria-haspopup="dialog" onClick={()=>{setOpen(true);dialog.current?.showModal();}}>▦</button><button className="text-link min-h-11 px-2" type="button" disabled={!value} aria-label={`Borrar ${label}`} onClick={()=>onChange('')}>Borrar</button></div>
 <dialog ref={dialog} aria-label={`Calendario de ${label}`} className={styles.dialog} onClose={()=>{setOpen(false);trigger.current?.focus();}}>
 <div className="flex items-center justify-between gap-2"><h2 className="font-bold text-blue-950">{label} · Hora de Canarias</h2><button type="button" className="button-secondary" onClick={close}>Cerrar</button></div>
 {open&&<DayPicker mode="single" locale={es} weekStartsOn={1} captionLayout="dropdown" navLayout="after" autoFocus selected={selected??undefined} defaultMonth={selected??today} today={today} startMonth={new Date(Math.min(1900,selected?.getFullYear()??1900),0)} endMonth={new Date(Math.max(today.getFullYear()+10,selected?.getFullYear()??0),11)} onSelect={d=>{if(d){onChange(dateText(d));close();}}}/>}<p className="text-xs text-slate-600">✓ Fecha seleccionada · Hoy subrayado. Flechas para recorrer los días; Escape para cerrar.</p>
 </dialog></div>;
}
export default function MonitoringFilters({query,onApply}:{query:string;onApply:(query:string)=>void}){
 const original=new URLSearchParams(query),[start,setStart]=useState(fromISO(original.get('start')||'')),[end,setEnd]=useState(fromISO(original.get('end')||'')),[game,setGame]=useState(original.get('game')||'ALL');
 const error=rangeError(start,end);const changed=start!==fromISO(original.get('start')||'')||end!==fromISO(original.get('end')||'')||game!==(original.get('game')||'ALL');const errorId=useId();
 return <form className={styles.filters} onSubmit={e=>{e.preventDefault();if(error)return;const p=new URLSearchParams();if(start)p.set('start',dateISO(start));if(end)p.set('end',dateISO(end));p.set('game',game);onApply(p.toString());}} aria-describedby={error?errorId:undefined}>
 <div className="flex flex-wrap items-end gap-3"><DateField label="Desde" value={start} onChange={setStart}/><DateField label="Hasta" value={end} onChange={setEnd}/><label className="font-semibold">Juego<select className="form-input" value={game} onChange={e=>setGame(e.target.value)}><option value="ALL">Todos</option><option>TRIVIAL</option><option>PASAPALABRA</option></select></label><button className="button-primary" disabled={!!error}>Consultar</button></div>
 {error&&<p id={errorId} role="alert" className="mt-2 text-sm font-semibold text-red-800">{error}</p>}
 <div className="mt-3 flex flex-wrap gap-2" aria-label="Intervalos rápidos">{[['Hoy',1],['Últimos 7 días',7],['Últimos 30 días',30],['Todo el periodo',null]].map(([text,days])=><button className="button-secondary text-sm" key={text} type="button" onClick={()=>{const range=quickRange(days as number|null);setStart(range.start);setEnd(range.end);}}>{text}</button>)}</div>
 {changed&&<p role="status" className="mt-2 text-sm font-semibold text-amber-900">Cambios pendientes de aplicar. Los resultados corresponden a la última consulta.</p>}
 </form>;
}
