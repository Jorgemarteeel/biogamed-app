"use client";

import Brand from "@/components/Brand";
import ProfileMenu from "@/components/ProfileMenu";
import GamePicker from "@/components/GamePicker";
import GameSummaryCard from "@/components/GameSummaryCard";
import {DashboardSubjects} from "@/components/AcademicCatalog";
import JoinRoomDialog from "@/components/JoinRoomDialog";
import {recentAcademicHref,academicReplayAvailable} from "@/lib/academic";
import { Suspense, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import Link from "next/link";
import api, {
  getCurrentUser, getRecentGames, getTopics,
  type GameHistorySummary, type Topic, type UserResponse,
} from "@/services/api";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserResponse | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [games, setGames] = useState<GameHistorySummary[]>([]);
  const [replay,setReplay]=useState<{href:string|null;message:string}>({href:null,message:""});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [joinOpen, setJoinOpen] = useState(false);
  const [noSubjects,setNoSubjects]=useState(false);
  const [legacyOpen, setLegacyOpen] = useState(false);
  useEffect(()=>{const q=new URLSearchParams(window.location.search);Promise.resolve().then(()=>{setJoinOpen(q.get("join")==="1");setLegacyOpen(q.get("banks")==="1");});},[]);

  useEffect(() => {
    if (!window.localStorage.getItem("token")) {
      router.replace("/login");
      return;
    }
    let active = true;
    async function loadDashboard() {
      try {
        // Validate the token before displaying the authenticated area.
        const currentUser = await getCurrentUser();
        if (!active) return;
        setUser(currentUser);
        const [topicResult, historyResult] = await Promise.allSettled([
          getTopics(), getRecentGames(),
        ]);
        if (!active || !window.localStorage.getItem("token")) return;
        if (topicResult.status === "fulfilled") {
          setTopics(topicResult.value);
        } else {
          // This list only labels the history; the picker loads its own filtered topics.
          setTopics([]);
        }
        if (historyResult.status === "fulfilled") {
          setGames(historyResult.value);
          const href=recentAcademicHref(historyResult.value);
          if(href){
            try{const playable=await academicReplayAvailable(href,async(mode,body)=>(await api.post(`/game/academic/preparations?mode=${mode}`,body,{timeout:10000})).data);if(!active)return;setReplay({href:playable?href:null,message:playable?"":"Tu selección anterior ya no tiene suficientes preguntas jugables. Elige contenido para preparar otra partida."});}
            catch(err){if(!active)return;if(isAxiosError(err)&&err.response?.status===401)return;setReplay({href:null,message:"No se pudo comprobar la disponibilidad de tu selección anterior. Puedes elegir contenido o volver a intentarlo."});}
          }

        } else {
          setHistoryError("No se pudo cargar tu historial.");
        }
        setLoading(false);
      } catch (err: unknown) {
        if (!active) return;
        // The shared interceptor clears rejected tokens and redirects to login.
        if (isAxiosError(err) && err.response?.status === 401) return;
        setError("No se pudo verificar tu sesión. Comprueba la conexión e inténtalo de nuevo.");
        setLoading(false);
      }
    }
    void loadDashboard();
    return () => { active = false; };
  }, [router, attempt]);

  function retry() {
    setLoading(true);
    setError("");
    setHistoryError("");
    setAttempt((value) => value + 1);
  }

  function logout() {
    window.localStorage.removeItem("token");
    setUser(null);
    setTopics([]);
    setGames([]);
    setLoading(true);
    router.replace("/login");
  }

  return (
    <div className="min-h-screen bg-background font-sans text-slate-900">
      <header className="site-header">
        <div className="mx-auto flex max-w-[68rem] flex-wrap items-center justify-between gap-4 px-5 py-3 sm:px-8 lg:px-12">
          <Brand />
          <div className="flex w-full min-w-0 items-center justify-between gap-4 sm:w-auto">
            <ProfileMenu name={user?.name} role={user?.role} />
            <button onClick={logout} className="button-primary shrink-0">
              Cerrar sesión
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[68rem] px-5 py-5 sm:px-8 sm:py-6 lg:px-12" aria-busy={loading}>
        <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0"><p className="text-sm text-slate-600">{user?`Hola, ${user.name || user.email}`:"Tu espacio de aprendizaje"}</p><h1 className="mt-2 break-words text-2xl font-black tracking-tight text-blue-950 sm:text-3xl">¿Qué quieres practicar hoy?</h1><p className="mt-2 text-slate-600">{noSubjects?"Prepara tu práctica con los bancos de preguntas existentes.":"Elige una asignatura para preparar tu práctica."}</p></div>
          {user&&<button className="button-secondary" aria-haspopup="dialog" onClick={()=>setJoinOpen(true)}>Unirme con código</button>}
        </div>

        {loading ? (
          <div role="status" className="rounded-2xl border border-slate-200 bg-white p-8 text-slate-600">
            Cargando tu panel…
          </div>
        ) : (
          <div className="space-y-5">
            <section className="min-w-0" aria-label="Contenido para practicar">
              {error?<div role="alert" className="notice-warning">{error}<button className="button-secondary ml-3" onClick={retry}>Volver a intentar</button></div>:user?<>
                {replay.href&&<Link className="text-link mb-5 inline-flex min-h-11 items-center break-words" href={replay.href}>Volver a practicar · {games.find(game=>game.content_context?.academic)?.content_context?.academic?.category_name}</Link>}
                {replay.message&&<p role="status" className="mb-3 text-sm text-slate-600">{replay.message} <button className="text-link min-h-11" onClick={retry}>Volver a comprobar</button></p>}
                <Suspense fallback={<p role="status">Cargando asignaturas…</p>}><DashboardSubjects onEmptyChange={setNoSubjects}/></Suspense>
                <button className={`${noSubjects?"button-primary":"text-link"} mt-5 inline-flex min-h-11 items-center`} aria-expanded={legacyOpen} aria-controls="legacy-banks" onClick={()=>{setLegacyOpen(v=>!v);const url=new URL(window.location.href);if(!legacyOpen)url.searchParams.set("banks","1");else url.searchParams.delete("banks");window.history.replaceState(null,"",url);}}>{noSubjects?"Practicar con los bancos disponibles":"Explorar otros contenidos →"}</button>
                {(legacyOpen||noSubjects)&&<section hidden={!legacyOpen} id="legacy-banks" className="mt-4 border-t border-slate-200 pt-5" aria-label="Otros bancos de preguntas">{noSubjects&&<h2 className="mb-3 text-xl font-bold text-blue-950">Bancos de preguntas disponibles</h2>}<p className="mb-4 text-sm text-slate-600">Acceso por temáticas, incluido contenido sin clasificación académica.</p><GamePicker/></section>}
              </>:null}
            </section>

            {user && (
              <section aria-labelledby="history-heading" className="rounded-2xl border border-slate-200 bg-white text-blue-950">
                <div className="flex flex-wrap items-center justify-between gap-3 px-5 pt-4"><h2 id="history-heading" className="text-xl font-bold">Partidas recientes</h2><Link href="/historial" className="text-link inline-flex min-h-11 items-center">Ver historial →</Link></div>
                <div id="recent-games" className="px-5 pb-5">
                {historyError ? (
                  <div className="mt-4">
                    <p role="alert" className="notice-error">{historyError}</p>
                    <button onClick={retry} className="text-link mt-3 min-h-11">Reintentar</button>
                  </div>
                ) : games.length === 0 ? (
                  <p className="mt-4 text-sm leading-7 text-slate-600">Aún no has iniciado ninguna partida. Cuando juegues, podrás consultar aquí tus resultados recientes.</p>
                ) : (
                  <ul className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {games.slice(0,3).map((game) => (
                      <li key={game.id}><GameSummaryCard game={game} topicName={topics.find((topic) => topic.id === game.topic_id)?.name ?? `Temática ${game.topic_id}`} compact /></li>
                    ))}
                  </ul>
                )}
                </div>
              </section>
            )}
          </div>
        )}
        {joinOpen&&user&&<JoinRoomDialog onClose={()=>setJoinOpen(false)}/>}
      </main>
    </div>
  );
}
