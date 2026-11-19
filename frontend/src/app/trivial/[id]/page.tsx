import TrivialSession from "@/components/TrivialSession";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[1-9]\d*$/.test(id) || !Number.isSafeInteger(Number(id))) return <p>Identificador de partida no válido.</p>;
  return <TrivialSession key={id} id={Number(id)} />;
}
