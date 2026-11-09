import {Suspense} from "react";
import AcademicPractice from "@/components/AcademicPractice";
export default function Page(){return <Suspense fallback={<p role="status">Cargando recorrido…</p>}><AcademicPractice/></Suspense>;}
