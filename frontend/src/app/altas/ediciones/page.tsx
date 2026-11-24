import { notFound } from "next/navigation";
import AcademicEditionsView from "@/components/AcademicEditionsView";

export default async function AcademicEditionsPage({ searchParams }: {
  searchParams: Promise<{ edicion?: string | string[] }>;
}) {
  const { edicion } = await searchParams;
  if (edicion === undefined) return <AcademicEditionsView key="all" />;
  if (typeof edicion !== "string" || !/^[1-9]\d*$/.test(edicion) || !Number.isSafeInteger(Number(edicion))) notFound();
  return <AcademicEditionsView key={edicion} editionId={Number(edicion)} />;
}
