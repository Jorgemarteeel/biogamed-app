import Link from "next/link";
// Same local SVG stroke convention as the rest of the UI; no icon package is installed.
export function ArrowLeftIcon(){return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="h-5 w-5 shrink-0"><path d="m12 5-7 7 7 7M5 12h14"/></svg>;}
export default function BackLink({href,disabled=false}:{href:string;disabled?:boolean}){
 const content=<><ArrowLeftIcon/><span>Volver</span></>;
 const className="text-link inline-flex min-h-11 items-center gap-2 rounded-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700";
 return disabled?<button type="button" disabled className={className} aria-label="Volver al paso anterior">{content}</button>:<Link href={href} scroll={false} className={className} aria-label="Volver al paso anterior">{content}</Link>;
}
