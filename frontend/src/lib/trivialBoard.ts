import api from '@/services/api';
export type BankKey='LYMPHOCYTE'|'MACROPHAGE'|'SPLEEN'|'FLASK'|'SYRINGE';
export type Destination={kind:'category'|'topic';id:number;name:string;academic:{subject_id:number;subject_name:string;block_id:number;block_name:string}|null};
export type Binding={bank:BankKey;kind:Destination['kind'];id:number};
export type Coverage={board_version:string;binding_version:null;bindings_persisted:false;can_start:false;sufficiency:'UNDETERMINED';banks:{key:BankKey;name:string;status:'PENDING'|'UNBOUND'|'EMPTY'|'COUNTS_AVAILABLE';destination:Destination|null;levels:{level:number;count:number}[]|null;unclassified:number|null;total:number|null}[];blockers:{code:string;message:string}[];overlaps:{left:BankKey;right:BankKey;count:number}[]};
export type BoardDefinition={version:string;source_sha256:string;width:number;height:number;cells:{id:number;order:number;label:string;source_label:string;kind:string;bank:BankKey|null;level:number;vertices:{x:number;y:number}[]}[];effects:Record<string,{status:'OBSERVED'|'PENDING';description:string}>};
export type DestinationPage={items:Destination[];total:number;skip:number;limit:number};
export const readBoard=async():Promise<{board:BoardDefinition;coverage:Coverage}>=>(await api.get('/trivial-board',{timeout:10000})).data;
export const readDestinations=async(kind:Destination['kind'],skip=0):Promise<DestinationPage>=>(await api.get('/trivial-board/destinations',{params:{kind,skip,limit:50},timeout:10000})).data;
export const checkCoverage=async(bindings:Binding[]):Promise<Coverage>=>(await api.post('/trivial-board/coverage',{bindings},{timeout:10000})).data;
export function destinationLabel(d:Destination){return `${d.kind==='category'?'Categoría':'Temática'} · ${d.academic?`${d.academic.subject_name} → ${d.academic.block_name} → `:''}${d.name} · ID ${d.id}`;}
export function bindingsFrom(draft:Partial<Record<BankKey,string>>):Binding[]{return Object.entries(draft).filter(([,v])=>v&&v!=='none').map(([bank,v])=>{const [kind,id]=v!.split(':');return {bank:bank as BankKey,kind:kind as Destination['kind'],id:Number(id)};});}
