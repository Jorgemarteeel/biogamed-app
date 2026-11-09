import type {AcademicContext as Context} from "@/services/api";
import {academicLabel} from "@/lib/academic";
export default function AcademicContext({value,compact=false}: {value?: Context | null;compact?: boolean}) {
  return value ? <p className={`${compact?"max-h-8":"my-1 max-h-12"} overflow-auto break-words text-sm leading-5 text-sky-900`} tabIndex={0} aria-label="Contenido académico guardado">{academicLabel(value)}</p> : null;
}
