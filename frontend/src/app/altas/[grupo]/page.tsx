import { notFound } from "next/navigation";
import UserImportView from "@/components/UserImportView";

export default async function UserImportPage({ params }: { params: Promise<{ grupo: string }> }) {
  const { grupo } = await params;
  if (grupo !== "alumnado" && grupo !== "profesorado") notFound();
  return <UserImportView target={grupo} />;
}
