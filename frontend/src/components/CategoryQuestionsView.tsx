"use client";
import QuestionManagement from "@/components/QuestionManagement";
export default function CategoryQuestionsView({subjectId,blockId,categoryId,mode}:{subjectId:number;blockId:number;categoryId:number;page?:number;mode?:string;level?:string;questionState?:string;adjusted?:boolean;invalidFilters?:boolean}){
 if(![subjectId,blockId,categoryId].every(n=>Number.isSafeInteger(n)&&n>0))return <p role="alert">La ruta académica no es válida. Vuelve a Gestión de preguntas.</p>;
 return <QuestionManagement initialMode={mode||"ALL"} initialContext={{subject:subjectId,block:blockId,category:categoryId}}/>;
}
