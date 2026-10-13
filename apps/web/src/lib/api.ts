// Thin client for the FastAPI backend (see docs/api-contract.md).
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  shopperChat: (body: { session_id: string; store_id: string; message: string }) =>
    request<{ reply: string; signal: unknown }>("/shopper/chat", { method: "POST", body: JSON.stringify(body) }),
  managerChat: (body: { session_id: string; message: string; store_id: string; sku?: string }) =>
    request<{ reply: string; tool_calls: unknown[] }>("/manager/chat", { method: "POST", body: JSON.stringify(body) }),
  skus: (storeId: string) => request<{ items: unknown[] }>(`/skus?store_id=${storeId}`),
  sku: (sku: string, storeId: string) => request<Record<string, unknown>>(`/skus/${sku}?store_id=${storeId}`),
  gaps: () => request<{ items: unknown[] }>("/gaps"),
  recentSignals: (limit = 20) => request<{ items: unknown[] }>(`/signals/recent?limit=${limit}`),
  experiment: () => request<Record<string, unknown>>("/experiment"),
  resetDemo: () => request<{ status: string }>("/demo/reset", { method: "POST" }),
};
