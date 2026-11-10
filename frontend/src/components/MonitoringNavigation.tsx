import Link from 'next/link';

export default function MonitoringNavigation({active,query}:{active:'activity'|'difficulties';query:string}){
 const applied=new URLSearchParams(query),common=new URLSearchParams();
 for(const key of ['start','end','game']){const value=applied.get(key);if(value!==null)common.set(key,value);}
 function href(view:'activity'|'difficulties'){
  const params=new URLSearchParams(common);
  if(view==='difficulties'&&active==='difficulties'&&applied.has('minimum'))params.set('minimum',applied.get('minimum')!);
  const route=view==='activity'?'/seguimiento':'/seguimiento/dificultades';
  return route+(params.size?'?'+params:'');
 }
 return <nav aria-label="Vistas del seguimiento docente" className="grid grid-cols-1 gap-2 sm:flex sm:flex-wrap">
 {([['activity','Participación y resultados'],['difficulties','Dificultades frecuentes']] as const).map(([view,label])=><Link key={view} href={href(view)} aria-current={active===view?'page':undefined} className={`button-secondary min-w-0 max-w-full text-center focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-orange-700 ${active===view?'border-blue-950 bg-blue-950 text-white hover:bg-blue-900':''}`}>{label}</Link>)}
 </nav>;
}
