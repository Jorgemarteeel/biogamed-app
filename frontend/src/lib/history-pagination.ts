export const HISTORY_PAGE_SIZE = 10;

export function visibleHistoryPage<T>(received: T[]): { items: T[]; hasMore: boolean } {
  return { items: received.slice(0, HISTORY_PAGE_SIZE), hasMore: received.length > HISTORY_PAGE_SIZE };
}
