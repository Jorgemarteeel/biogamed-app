"use client";
import Link from 'next/link';
import {useEffect,useSyncExternalStore,type ComponentProps} from 'react';
import {usePathname,useSearchParams} from 'next/navigation';
import {readTrail,screenTrail,screenReturn} from '@/lib/navigation-return';
const key='biogamed-screen-trail-v1';
const empty:readonly string[]=[];
let trail:readonly string[]=empty;
let ready=false;
const listeners=new Set<()=>void>();
const subscribe=(fn:()=>void)=>{listeners.add(fn);return()=>{listeners.delete(fn);};};
export function NavigationObserver(){
 const pathname=usePathname(),query=useSearchParams().toString();
 useEffect(()=>{
  const current=pathname+(query?'?'+query:'');
  let previous=trail;
  if(!ready){try{const saved=readTrail(sessionStorage.getItem(key));previous=saved.at(-1)?.split('?')[0]===pathname?saved:empty;}catch{previous=empty;}ready=true;}
  trail=screenTrail(previous,current);
  try{if(trail.length)sessionStorage.setItem(key,JSON.stringify(trail));else sessionStorage.removeItem(key);}catch{/* Memory-only navigation remains available. */}
  listeners.forEach(fn=>fn());
 },[pathname,query]);
 return null;
}
export default function ReturnLink({href,children,...props}:Omit<ComponentProps<typeof Link>,'href'>&{href:string}){
 const saved=useSyncExternalStore(subscribe,()=>trail,()=>empty);
 const current=typeof window!=='undefined'&&window.location?window.location.pathname+window.location.search:'';
 const destination=screenReturn(saved,current,href);
 return <Link {...props} href={destination}>{destination===href?children:'← Volver'}</Link>;
}
