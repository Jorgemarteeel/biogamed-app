import GameHistoryView from "@/components/GameHistoryView";

export default async function GameHistoryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const parsed = /^[1-9]\d*$/.test(id) ? Number(id) : NaN;
  const sessionId = Number.isSafeInteger(parsed) ? parsed : null;
  return <GameHistoryView key={sessionId} sessionId={sessionId} />;
}
