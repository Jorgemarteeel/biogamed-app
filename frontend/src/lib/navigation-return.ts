/** Per-tab screen origins. Query-only changes update a screen, not its parent. */
const allowed = new Set(['page','subjectsPage','blocksPage','categoriesPage','subject','block','category','mode','play','step','difficulty','edit','focus','banks','join','start','end','game','minimum','search','role','topic','topicId','state','bank','classification','action','importSubject','importBlock','importCategory','importMode']);
export function safeScreen(value:unknown):string|null {
 if(typeof value!=='string'||value.length>4096||!value.startsWith('/')||value.startsWith('//')||value.includes('\\'))return null;
 try{const u=new URL(value,'https://biogamed.invalid');if(u.origin!=='https://biogamed.invalid'||!/^\/(?:dashboard|historial|partidas\/\d+|trivial\/[1-9]\d*|progreso|cuenta|practicar|game|pasapalabra(?:\/\d+|\/rooms\/\d+)?|seguimiento(?:\/dificultades)?|administracion\/usuarios|gestion\/(?:trivial|inmunoquest|preguntas|asignaturas(?:\/\d+(?:\/bloques\/\d+(?:\/categorias\/\d+)?)?)?))$/.test(u.pathname))return null;const q=new URLSearchParams();u.searchParams.forEach((v,k)=>{if(allowed.has(k))q.set(k,v);});return u.pathname+(q.size?'?'+q:'');}catch{return null;}
}
export function readTrail(value:string|null):string[]{try{const a=JSON.parse(value??'null');return Array.isArray(a)&&a.length<=25&&a.every(x=>safeScreen(x)===x)?a:[];}catch{return [];}}
export function screenTrail(previous:readonly string[],value:string):string[]{
 const current=safeScreen(value);if(!current)return [];
 const path=current.split('?')[0];const last=previous.at(-1);
 if(last?.split('?')[0]===path)return [...previous.slice(0,-1),current];
 // A started room redirects to its match; returning to it would redirect again.
 if(/^\/pasapalabra\/\d+$/.test(path)&&/^\/pasapalabra\/rooms\/\d+$/.test(last?.split('?')[0]??''))return [...previous.slice(0,-1),current];
 const index=previous.findLastIndex(x=>x.split('?')[0]===path);
 return (index>=0?[...previous.slice(0,index),current]:[...previous,current]).slice(-25);
}
export function screenReturn(trail:readonly string[],current:string,fallback:string):string {
 const safe=safeScreen(current);return safe&&trail.at(-1)?.split('?')[0]===safe.split('?')[0]&&trail.length>1?trail[trail.length-2]:safeScreen(fallback)??'/dashboard';
}
