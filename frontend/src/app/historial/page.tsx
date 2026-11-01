import HistoryView from "@/components/HistoryView";

export default async function HistoryPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const { page } = await searchParams;
  const parsed = page && /^[1-9]\d*$/.test(page) ? Number(page) : 1;
  const currentPage = Number.isSafeInteger(parsed) ? Math.min(parsed, 1000000) : 1;
  return <HistoryView key={currentPage} page={currentPage} />;
}
