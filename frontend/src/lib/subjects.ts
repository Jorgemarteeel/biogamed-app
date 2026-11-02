import type { Subject, UserResponse } from "@/services/api";

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
