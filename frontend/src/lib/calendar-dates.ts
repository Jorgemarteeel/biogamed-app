/** Date-only values: no parsing ISO dates as UTC instants. */
export function parseDate(value:string):Date|null {
 const m=/^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);if(!m)return null;
 const [,d,month,y]=m.map(Number);if(y<1||y>9998)return null;
 const date=new Date(0);date.setFullYear(y,month-1,d);date.setHours(12,0,0,0);
 return date.getFullYear()===y&&date.getMonth()===month-1&&date.getDate()===d?date:null;
}
export function dateText(d:Date){return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getFullYear()).padStart(4,'0')}`;}
export function dateISO(value:string){const d=parseDate(value);return d?`${String(d.getFullYear()).padStart(4,'0')}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`:'';}
export function fromISO(value:string){const m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(value);return m?`${m[3]}/${m[2]}/${m[1]}`:value;}
export function canaryToday(now=new Date()){const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Atlantic/Canary',day:'2-digit',month:'2-digit',year:'numeric'}).formatToParts(now);return ['day','month','year'].map(k=>parts.find(p=>p.type===k)!.value).join('/');}
export function quickRange(days:number|null,now=new Date()) {if(days===null)return {start:'',end:''};const end=canaryToday(now),start=parseDate(end)!;start.setDate(start.getDate()-(days-1));return {start:dateText(start),end};}
export function rangeError(start:string,end:string){if(start&&!parseDate(start))return 'Desde: introduce una fecha existente con formato día/mes/año.';if(end&&!parseDate(end))return 'Hasta: introduce una fecha existente con formato día/mes/año.';if(start&&end&&dateISO(start)>dateISO(end))return 'Desde no puede ser posterior a Hasta.';return '';}
