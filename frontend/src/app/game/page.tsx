import {PasapalabraPrepare} from "@/components/Pasapalabra";
import GameStart from "@/components/GameStart";

export default async function GamePage({
  searchParams,
}: {
  searchParams: Promise<{ topicId?: string | string[]; mode?: string | string[] }>;
}) {
  const params = await searchParams;
  const id = typeof params.topicId === "string" && /^[1-9]\d*$/.test(params.topicId)
    ? Number(params.topicId)
    : NaN;
  const topicId = Number.isSafeInteger(id) ? id : null;
  const mode = params.mode === "TRIVIAL" || params.mode === "PASAPALABRA"
    ? params.mode
    : null;

  if (mode === "PASAPALABRA" && topicId !== null) return <PasapalabraPrepare key={topicId} topicId={topicId}/>;
  return <GameStart key={`${topicId}-${mode}`} topicId={topicId} mode={mode} />;
}
