import SubjectsView from "@/components/SubjectsView";

export default async function SubjectsPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const { page } = await searchParams;
  const parsed = page && /^[1-9]\d*$/.test(page) ? Number(page) : 1;
  const currentPage = Number.isSafeInteger(parsed) ? Math.min(parsed, 1000000) : 1;
  return <SubjectsView key={currentPage} page={currentPage} />;
}
