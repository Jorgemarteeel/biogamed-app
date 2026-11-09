import type {AcademicContext} from "@/services/api";
export const academicLabel = (context?: AcademicContext | null) => context ? `${context.subject_name} → ${context.block_name} → ${context.category_name}` : null;
export function practiceQuery(query: URLSearchParams) {
  const ids: Record<string, number | undefined> = {};
  let valid = true;
  for (const key of ["subject", "block", "category", "subjectsPage", "blocksPage", "categoriesPage"]) {
    const raw = query.get(key);
    if (raw !== null) {
      if (!/^[1-9]\d*$/.test(raw) || !Number.isSafeInteger(Number(raw))) valid = false;
      else ids[key] = Number(raw);
    }
  }
  if (ids.block && !ids.subject || ids.category && !ids.block) valid = false;
  const mode = query.get("mode") ?? "TRIVIAL";
  const difficulty = query.get("difficulty") ?? "all";
  const play = query.get("play") ?? "LOCAL";
  if (!["TRIVIAL", "PASAPALABRA"].includes(mode) || !["all", "unknown", "1", "2", "3", "4"].includes(difficulty) || !["LOCAL", "ONLINE"].includes(play)) valid = false;
  if(query.has("edit")&&query.get("edit")!=="content")valid=false;
  const explicitMode = query.has("mode");
  const explicitPlay = query.has("play");
  const requestedStep = query.get("step");
  if (requestedStep !== null && !["game", "mode", "prepare"].includes(requestedStep)) valid = false;
  const step = requestedStep ?? (!explicitMode ? "game" : mode === "PASAPALABRA" && !explicitPlay ? "mode" : "prepare");
  if (step === "mode" && mode !== "PASAPALABRA" || step === "prepare" && (!explicitMode || mode === "PASAPALABRA" && !explicitPlay)) valid = false;
  return {ids, mode, difficulty, play, step, explicitMode, explicitPlay, valid};
}
export function practiceHref(query: string, changes: Record<string, string | number | undefined>) {
  const next = new URLSearchParams(query);
  for (const [key, value] of Object.entries(changes)) {
    if (value === undefined) next.delete(key); else next.set(key, String(value));
  }
  return `/practicar${next.size ? `?${next}` : ""}`;
}

export function academicReturn(value: string) {
  try { const url=new URL(value,"https://biogamed.invalid"); return url.origin==="https://biogamed.invalid" && url.pathname==="/practicar" && practiceQuery(url.searchParams).valid; } catch { return false; }
}

/** Only use persisted academic context, never current Topic/category associations. */
export function recentAcademicHref(games: import("@/services/api").GameHistorySummary[]) {
  const game=games.find(g=>g.content_context?.academic);
  const a=game?.content_context?.academic;
  if(!game||!a||![a.subject_id,a.block_id,a.category_id].every(id=>Number.isSafeInteger(id)&&id>0)||!a.category_name)return null;
  const selection=game.content_context!.selection;
  return practiceHref("",{subject:a.subject_id,block:a.block_id,category:a.category_id,mode:game.game_mode,step:"prepare",...(game.game_mode==="PASAPALABRA"?(game.format_key==="pasapalabra-online-v1"?{play:"ONLINE"}:game.format_key==="pasapalabra-local-v1"?{play:"LOCAL"}:{step:"mode"}):{}),difficulty:selection?.difficulty_unknown?"unknown":selection?.difficulty??"all"});
}

/** Deterministic parent step: works without browser history, including after reload. */
export function practiceBackHref(query: string, unavailable=false) {
  const parsed=new URLSearchParams(query), selected=practiceQuery(parsed);
  const {ids,mode,step,explicitMode,explicitPlay,valid}=selected;
  if(!valid||!ids.subject)return `/dashboard${ids.subjectsPage?`?subjectsPage=${ids.subjectsPage}`:""}`;
  if(unavailable&&ids.category)return practiceHref(query,{category:undefined,edit:undefined,step:"game",focus:"prepare"});
  if(!ids.category){
    if(ids.block)return practiceHref(query,{block:undefined,categoriesPage:undefined,edit:undefined,step:"game",focus:"prepare"});
    return `/dashboard${ids.subjectsPage?`?subjectsPage=${ids.subjectsPage}`:""}`;
  }
  if(parsed.get("edit")==="content")return practiceHref(query,{edit:undefined,focus:"prepare"});
  if(!explicitMode||step==="game")return practiceHref(query,{edit:"content",focus:"prepare"});
  if(mode==="PASAPALABRA"&&(!explicitPlay||step==="mode"))return practiceHref(query,{step:"game",focus:"prepare"});
  return practiceHref(query,{step:mode==="PASAPALABRA"?"mode":"game",focus:"prepare"});
}
export function questionsForDifficulty(bank: import("@/services/api").GameAvailability | null | undefined,difficulty:string) {
  return (bank?.combinations??[]).filter(c=>difficulty==="all"||(difficulty==="unknown"?c.difficulty===null:c.difficulty===Number(difficulty))).reduce((sum,c)=>sum+c.count,0);
}
export function gameAvailabilityLabel(mode: import("@/services/api").GameMode,count:number) {
  if(count===0)return "Sin preguntas disponibles";
  if(mode==="PASAPALABRA"&&count<40)return `${count} preguntas disponibles · Se necesitan 40 distintas para dos jugadores.`;
  return mode==="TRIVIAL"?`${count} ${count===1?"pregunta disponible":"preguntas disponibles"} · Hasta ${Math.min(10,count)} por partida.`:`${count} preguntas disponibles · 40 distintas por partida.`;
}

/** Optional presentation configuration, never a catalog permission or data filter. */
export function demoSubjectGroups<T extends {id:number}>(items:T[],configured?:string) {
 const ids=new Set((configured??"").split(",").filter(v=>/^[1-9]\d*$/.test(v.trim())).map(Number));
 const page=items.slice(0,12);
 return {primary:page.filter(item=>!ids.has(item.id)),secondary:page.filter(item=>ids.has(item.id))};
}
/** Check the saved filters against current eligibility; never choose a replacement. */
export async function academicReplayAvailable(href:string,prepare:(mode:string,body:Record<string,number>)=>Promise<import("@/services/api").GameAvailability>) {
 const selection=practiceQuery(new URL(href,"https://biogamed.invalid").searchParams);
 if(!selection.valid||!selection.ids.category)return false;
 const {subject,block,category}=selection.ids;
 const bank=await prepare(selection.mode,{subject_id:subject!,block_id:block!,category_id:category});
 return questionsForDifficulty(bank,selection.difficulty)>=(selection.mode==="PASAPALABRA"?40:1);
}
