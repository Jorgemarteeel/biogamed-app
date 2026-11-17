import {Suspense} from "react";
import InmunoQuestContent from "@/components/InmunoQuestContent";
export default function Page(){return <Suspense fallback={<p>Cargando…</p>}><InmunoQuestContent/></Suspense>;}
