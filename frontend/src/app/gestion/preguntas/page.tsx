import {Suspense} from "react";
import QuestionManagement from "@/components/QuestionManagement";
export default function Page(){return <Suspense fallback={<p>Cargando preguntas…</p>}><QuestionManagement/></Suspense>;}
