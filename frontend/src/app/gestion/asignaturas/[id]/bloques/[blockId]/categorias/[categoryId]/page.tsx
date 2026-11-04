import CategoryQuestionsView from "@/components/CategoryQuestionsView";
import type { GameMode, QuestionStateFilter } from "@/services/api";

export default async function CategoryQuestionsPage({ params, searchParams }: {
  params: Promise<{ id: string; blockId: string; categoryId: string }>;
  searchParams: Promise<{ page?: string; mode?: string; level?: string; state?: string; adjusted?: string }>;
}) {
  const [route, query] = await Promise.all([params, searchParams]);
  const parseId = (value: string) => /^[1-9]\d*$/.test(value) && Number.isSafeInteger(Number(value))
    ? Number(value) : 0;
  const parsedPage = query.page && /^[1-9]\d*$/.test(query.page) ? Number(query.page) : 1;
  const page = Number.isSafeInteger(parsedPage) ? Math.min(parsedPage, 1000000) : 1;
  const mode = query.mode || "";
  const level = query.level || "";
  const questionState = query.state || "all";
  const invalidFilters = !["", "TRIVIAL", "PASAPALABRA"].includes(mode) ||
    !["", "unknown", "1", "2", "3", "4"].includes(level) ||
    !["active", "retired", "all"].includes(questionState);
  return <CategoryQuestionsView key={`${route.id}-${route.blockId}-${route.categoryId}-${page}-${mode}-${level}-${questionState}`}
    subjectId={parseId(route.id)} blockId={parseId(route.blockId)}
    categoryId={parseId(route.categoryId)} page={page} mode={mode as GameMode | ""}
    adjusted={query.adjusted === "1"} level={level} questionState={questionState as QuestionStateFilter} invalidFilters={invalidFilters} />;
}
