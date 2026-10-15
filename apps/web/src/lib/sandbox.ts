/**
 * Per-visitor demo sandbox (contract: docs/api-contract.md §2–3).
 * The browser creates a random UUID v4 on first visit, keeps it in
 * localStorage and sends it as `X-Sandbox-Id` on every API call. Firestore
 * listeners read `sandboxes/{sandboxId}/**` with the same id.
 */

const SANDBOX_KEY = "demand-radar.sandboxId";
let cached: string | null = null;

export function sandboxId(): string {
  if (cached) return cached;
  try {
    cached = localStorage.getItem(SANDBOX_KEY);
  } catch {
    // Storage blocked (private mode, previews): keep a per-page id instead.
  }
  if (!cached) {
    cached = crypto.randomUUID();
    try {
      localStorage.setItem(SANDBOX_KEY, cached);
    } catch {
      // ignore
    }
  }
  return cached;
}
