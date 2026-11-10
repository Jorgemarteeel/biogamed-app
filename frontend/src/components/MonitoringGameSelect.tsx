"use client";
import {useId} from 'react';
import * as Select from '@radix-ui/react-select';
import styles from './MonitoringGameSelect.module.css';

const games = [
 {value:'ALL',label:'Todos'},
 {value:'TRIVIAL',label:'Trivial'},
 {value:'PASAPALABRA',label:'Pasapalabra'},
];
export default function MonitoringGameSelect({value,onValueChange}:{value:string;onValueChange:(value:string)=>void}){
 const id=useId();
 return <div className={styles.field}><label htmlFor={id} className={styles.label}>Juego</label>
 <Select.Root value={value} onValueChange={onValueChange} name="game">
  <Select.Trigger id={id} className={styles.trigger}>
   <span className={styles.value}><Select.Value>{games.find(game=>game.value===value)?.label}</Select.Value></span>
   <Select.Icon className={styles.icon}><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></Select.Icon>
  </Select.Trigger>
  <Select.Portal><Select.Content position="popper" align="start" sideOffset={5} collisionPadding={12} className={styles.content}>
   <Select.ScrollUpButton className={styles.scrollButton} aria-label="Desplazar opciones hacia arriba">⌃</Select.ScrollUpButton>
   <Select.Viewport className={styles.viewport}>
    {games.map(game=><Select.Item key={game.value} value={game.value} textValue={game.label} className={styles.item}>
     <Select.ItemIndicator className={styles.indicator}><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg></Select.ItemIndicator>
     <Select.ItemText><span className={styles.optionText}>{game.label}</span></Select.ItemText>
    </Select.Item>)}
   </Select.Viewport>
   <Select.ScrollDownButton className={styles.scrollButton} aria-label="Desplazar opciones hacia abajo">⌄</Select.ScrollDownButton>
  </Select.Content></Select.Portal>
 </Select.Root></div>;
}
