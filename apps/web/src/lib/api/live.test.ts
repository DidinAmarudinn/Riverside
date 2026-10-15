import { afterEach, describe, expect, it, vi } from "vitest";
import { liveApi } from "./live";
import { adaptSignal } from "./adapters";
import { alertSchema, liveSignalSchema } from "./schemas";

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

function mockFetch(status: number, body?: unknown) {
  const fn = vi.fn(async () =>
    new Response(body === undefined ? null : JSON.stringify(body), { status }),
  );
  vi.stubGlobal("fetch", fn);
  return fn;
}

function sentHeaders(fn: ReturnType<typeof mockFetch>, call = 0) {
  const init = fn.mock.calls[call] as unknown as [string, RequestInit];
  return init[1].headers as Record<string, string>;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("live API adapter (docs/api-contract.md §3)", () => {
  it("sends the same UUID v4 X-Sandbox-Id on every request", async () => {
    const fn = mockFetch(200, { items: [] });
    await liveApi.getStores();
    await liveApi.getProducts("santan");
    const first = sentHeaders(fn, 0)["X-Sandbox-Id"];
    expect(first).toMatch(UUID_V4);
    expect(sentHeaders(fn, 1)["X-Sandbox-Id"]).toBe(first);
  });

  it("reads list endpoints from { items }", async () => {
    mockFetch(200, {
      items: [{ storeId: "store_1", name: "Toko 1", city: "Bandung", lat: 0, lng: 0 }],
    });
    const stores = await liveApi.getStores();
    expect(stores).toEqual([
      { id: "store_1", name: "Toko 1", city: "Bandung", lat: 0, lng: 0 },
    ]);
  });

  it("accepts 204 from demo reset", async () => {
    const fn = mockFetch(204);
    await expect(liveApi.resetDemo()).resolves.toBeUndefined();
    expect(fn).toHaveBeenCalledWith("/api/demo/reset", expect.objectContaining({ method: "POST" }));
  });

  it("parses the current backend stubs for kiosk, overview and session", async () => {
    mockFetch(200, { sessionId: "s1" });
    await expect(liveApi.createKioskSession("store_1")).resolves.toEqual({ sessionId: "s1" });

    mockFetch(200, { reply: "ok", products: [], alternatives: [], nearestBranch: null });
    const kiosk = await liveApi.sendKioskMessage({ sessionId: "s1", storeId: "store_1", text: "santan" });
    expect(kiosk.nearestBranch).toBeUndefined();

    mockFetch(200, { storeId: "store_1", kpis: {}, topRisks: [] });
    const overview = await liveApi.getOverview("store_1");
    expect(overview.metrics).toEqual({
      storeId: "store_1",
      lostRevenueToday: 0,
      unmetToday: 0,
      stockoutSkus: 0,
    });
  });

  it("maps camelCase recommendation fields to UI types", async () => {
    mockFetch(200, {
      items: [
        {
          storeId: "store_1",
          sku: "SKU-65ML",
          onHand: 0,
          forecastA7d: 0,
          forecastB7d: 60,
          recommendedQtyA: 0,
          recommendedQtyB: 60,
          riskType: "stockout_risk",
        },
      ],
    });
    const [rec] = await liveApi.getRecommendations("store_1");
    expect(rec).toMatchObject({ forecastA: 0, forecastB: 60, recommendedQty: 60 });
  });
});

describe("Firestore documents (docs/api-contract.md §2)", () => {
  const ts = { toDate: () => new Date("2026-10-14T13:00:00Z") };

  it("converts Firestore Timestamps to ISO strings", () => {
    const alert = alertSchema.parse({
      id: "a1",
      storeId: "store_1",
      type: "stockout_risk",
      title: "Santan habis",
      createdAt: ts,
    });
    expect(alert.createdAt).toBe("2026-10-14T13:00:00.000Z");
  });

  it("drops low_confidence signals from the live feed", () => {
    const raw = liveSignalSchema.parse({
      id: "s1",
      ts,
      requestedText: "santan kecil",
      outcome: "low_confidence",
    });
    expect(adaptSignal("store_1", raw)).toBeNull();
  });
});
