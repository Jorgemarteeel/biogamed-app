// Invitation drafts stay in this tab and origin. Restoring never joins a room.
const KEY = "pasapalabra-join-code";
export function saveJoinDraft(code: string) {
  try {
    const value = code.trim().toUpperCase().slice(0, 12);
    if (value) window.sessionStorage.setItem(KEY, value);
    else window.sessionStorage.removeItem(KEY);
  } catch { /* joining still works when storage is unavailable */ }
}
export function readJoinDraft(): string {
  try { return window.sessionStorage.getItem(KEY)?.slice(0, 12) ?? ""; }
  catch { return ""; }
}
export function clearJoinDraft() { saveJoinDraft(""); }
