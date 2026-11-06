import {PasapalabraRoom} from "@/components/PasapalabraOnline";
export default async function Page({params}:{params:Promise<{id:string}>}){const {id}=await params;return /^[1-9]\d*$/.test(id)&&Number.isSafeInteger(Number(id))?<PasapalabraRoom key={id} id={Number(id)}/>:<p>Identificador de sala no válido.</p>;}
