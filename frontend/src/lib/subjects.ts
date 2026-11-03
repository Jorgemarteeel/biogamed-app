import type { Category, ContentBlock, Subject, UnassignedCategory, UserResponse } from "@/services/api";

export const SUBJECTS_PAGE_SIZE = 12;

export function canManageSubjects(role: UserResponse["role"]): boolean {
  return role === "teacher" || role === "admin";
}

export function visibleSubjectsPage(received: Subject[]): { items: Subject[]; hasMore: boolean } {
  return {
    items: received.slice(0, SUBJECTS_PAGE_SIZE),
    hasMore: received.length > SUBJECTS_PAGE_SIZE,
  };
}

export function visibleBlocksPage(received: ContentBlock[]): { items: ContentBlock[]; hasMore: boolean } {
  return {
    items: received.slice(0, SUBJECTS_PAGE_SIZE),
    hasMore: received.length > SUBJECTS_PAGE_SIZE,
  };
}

export function visibleCategoriesPage(received: Category[]): { items: Category[]; hasMore: boolean } {
  return { items: received.slice(0, SUBJECTS_PAGE_SIZE), hasMore: received.length > SUBJECTS_PAGE_SIZE };
}

export function visibleUnassignedPage(received: UnassignedCategory[]): { items: UnassignedCategory[]; hasMore: boolean } {
  return { items: received.slice(0, SUBJECTS_PAGE_SIZE), hasMore: received.length > SUBJECTS_PAGE_SIZE };
}
