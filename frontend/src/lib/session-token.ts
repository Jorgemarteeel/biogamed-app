"use client";

import { useSyncExternalStore } from "react";

function subscribe(onChange: () => void) {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

function hasSessionToken() {
  try {
    return Boolean(window.localStorage.getItem("token"));
  } catch {
    return false;
  }
}

function publicSnapshot() {
  return false;
}

export default function useSessionToken() {
  return useSyncExternalStore(subscribe, hasSessionToken, publicSnapshot);
}
