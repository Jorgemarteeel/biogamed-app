import CategoriesView from "@/components/CategoriesView";

export default async function CategoriesPage({ params, searchParams }: {
  params: Promise<{ id: string; blockId: string }>;
  searchParams: Promise<{ page?: string }>;
}) {
  const [{ id, blockId }, { page }] = await Promise.all([params, searchParams]);
  const parseId = (value: string) => /^[1-9]\d*$/.test(value) && Number.isSafeInteger(Number(value))
    ? Number(value) : 0;
  const parsedPage = page && /^[1-9]\d*$/.test(page) ? Number(page) : 1;
  const currentPage = Number.isSafeInteger(parsedPage) ? Math.min(parsedPage, 1000000) : 1;
  const subjectId = parseId(id);
  const currentBlockId = parseId(blockId);
  return <CategoriesView key={`${subjectId}-${currentBlockId}-${currentPage}`}
    subjectId={subjectId} blockId={currentBlockId} page={currentPage} />;
}
