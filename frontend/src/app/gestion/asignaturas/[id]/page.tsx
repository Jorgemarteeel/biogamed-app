import BlocksView from "@/components/BlocksView";

export default async function BlocksPage({ params, searchParams }: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const [{ id }, { page }] = await Promise.all([params, searchParams]);
  const subjectId = /^[1-9]\d*$/.test(id) ? Number(id) : 0;
  const parsedPage = page && /^[1-9]\d*$/.test(page) ? Number(page) : 1;
  const currentPage = Number.isSafeInteger(parsedPage) ? Math.min(parsedPage, 1000000) : 1;
  return <BlocksView key={`${subjectId}-${currentPage}`} subjectId={subjectId} page={currentPage} />;
}
