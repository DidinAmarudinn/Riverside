// Thin client for the FastAPI backend (contract: docs/api-contract.md §3).
// Every call carries X-Sandbox-Id so each visitor (judge) gets an isolated demo.

const SANDBOX_KEY = "demand-radar.sandboxId";
let cachedSandboxId: string | null = null;

export function sandboxId(): string {
  if (cachedSandboxId) return cachedSandboxId;
  try {
    cachedSandboxId = localStorage.getItem(SANDBOX_KEY);
  } catch {
    // storage blocked (private mode, previews): keep a per-page id instead
  }
  if (!cachedSandboxId) {
    cachedSandboxId = crypto.randomUUID();
    try {
      localStorage.setItem(SANDBOX_KEY, cachedSandboxId);
    } catch {
      // ignore
    }
  }
  return cachedSandboxId;
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", "X-Sandbox-Id": sandboxId(), ...init?.headers },
  });
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, body?.error?.code ?? "http_error", body?.error?.message ?? res.statusText);
  return body as T;
}

const post = (body?: unknown): RequestInit => ({ method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export type Product = { sku: string; name: string; inStock: boolean; aisle: string };
export type KioskReply = { reply: string; products: Product[]; alternatives: Product[]; nearestBranch?: unknown };
export type ManagerReply = { reply: string; citations: unknown[]; sessionId: string };

export const api = {
  healthz: () => request<{ ok: boolean }>("/healthz"),
  stores: () => request<{ items: unknown[] }>("/stores"),
  products: (q: string) => request<{ items: unknown[] }>(`/products?q=${encodeURIComponent(q)}`),

  kioskSession: (storeId: string) => request<{ sessionId: string }>("/kiosk/sessions", post({ storeId })),
  kioskMessage: (sessionId: string, text: string) =>
    request<KioskReply>(`/kiosk/sessions/${sessionId}/messages`, post({ text })),

  overview: (storeId: string) => request<Record<string, unknown>>(`/manager/${storeId}/overview`),
  recommendations: (storeId: string, risk?: string) =>
    request<{ items: unknown[] }>(`/manager/${storeId}/recommendations${risk ? `?risk=${risk}` : ""}`),
  sku: (storeId: string, sku: string) => request<Record<string, unknown>>(`/manager/${storeId}/sku/${sku}`),
  managerChat: (storeId: string, message: string, sessionId?: string) =>
    request<ManagerReply>(`/manager/${storeId}/chat`, post({ sessionId, message })),
  gaps: (storeId: string) => request<Record<string, unknown>>(`/manager/${storeId}/gaps`),

  resetDemo: () => request<void>("/demo/reset", post()),
  nextMorning: (storeId: string) => request<Record<string, unknown>>("/demo/next-morning", post({ storeId })),
};
