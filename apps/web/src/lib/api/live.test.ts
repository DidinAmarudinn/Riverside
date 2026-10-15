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
      items: [{ storeId: "S01", name: "Toko 1", city: "Bandung", lat: 0, lng: 0 }],
    });
    const stores = await liveApi.getStores();
    expect(stores).toEqual([
      { id: "S01", name: "Toko 1", city: "Bandung", lat: 0, lng: 0 },
    ]);
  });

  it("accepts 204 from demo reset", async () => {
    const fn = mockFetch(204);
    await expect(liveApi.resetDemo()).resolves.toBeUndefined();
    expect(fn).toHaveBeenCalledWith("/api/demo/reset", expect.objectContaining({ method: "POST" }));
  });

  it("parses the current backend stubs for kiosk, overview and session", async () => {
    mockFetch(200, { sessionId: "s1" });
    await expect(liveApi.createKioskSession("S01")).resolves.toEqual({ sessionId: "s1" });

    mockFetch(200, { reply: "ok", products: [], alternatives: [], nearestBranch: null });
    const kiosk = await liveApi.sendKioskMessage({ sessionId: "s1", storeId: "S01", text: "santan" });
    expect(kiosk.nearestBranch).toBeUndefined();

    mockFetch(200, { storeId: "S01", kpis: {}, topRisks: [] });
    const overview = await liveApi.getOverview("S01");
    expect(overview.metrics).toEqual({
      storeId: "S01",
      lostRevenueToday: 0,
      unmetToday: 0,
      stockoutSkus: 0,
    });
  });

  it("maps camelCase recommendation fields to UI types", async () => {
    mockFetch(200, {
      items: [
        {
          storeId: "S01",
          sku: "SKU-0001",
          onHand: 0,
          forecastA7d: 0,
          forecastB7d: 60,
          recommendedQtyA: 0,
          recommendedQtyB: 60,
          riskType: "stockout_risk",
        },
      ],
    });
    const [rec] = await liveApi.getRecommendations("S01");
    expect(rec).toMatchObject({ forecastA: 0, forecastB: 60, recommendedQty: 60 });
  });
});

describe("manager responses (docs/api-contract.md §3.1)", () => {
  it("merges SkuDetail sales and forecast series by date", async () => {
    mockFetch(200, {
      storeId: "S01",
      sku: "SKU-0001",
      product: { name: "Santan Kotak Kara 65 ml", brand: "Kara", category: "Cooking Essentials", packSize: "65 ml", priceIdr: 4500, aisle: "A1-2" },
      riskType: "stockout_risk",
      kpis: { onHand: 0, lostRevenueIdr: 171000, lostRevenueUnits: 38, unmetRequests: 38, stockoutDays: 5 },
      sales: [{ date: "2026-10-12", qty: 0, isStockout: true }],
      forecastA: [
        { date: "2026-10-12", qty: 1 },
        { date: "2026-10-13", qty: 0, lower: 0, upper: 2 },
      ],
      forecastB: [{ date: "2026-10-13", qty: 9, lower: 7, upper: 11 }],
      unmetDaily: [{ date: "2026-10-12", count: 8 }],
      evidence: {
        total: 1,
        items: [{ id: "c1", ts: "2026-10-12T19:02:00+07:00", channel: "kiosk", quote: "ada santen kotak kecil?", outcome: "out_of_stock", confidence: 0.93 }],
      },
      reason: { recommendedQtyA: 0, recommendedQtyB: 60, reasonText: "38 shoppers asked during 5 stockout days." },
    });
    const detail = await liveApi.getSkuDetail("S01", "SKU-0001");
    expect(detail.series).toEqual([
      { date: "2026-10-12", posSales: 0, forecastA: 1, forecastALower: undefined, forecastAUpper: undefined, forecastB: null, isStockout: true },
      { date: "2026-10-13", posSales: null, forecastA: 0, forecastALower: 0, forecastAUpper: 2, forecastB: 9, forecastBLower: 7, forecastBUpper: 11, isStockout: false },
    ]);
    expect(detail.recommendation).toMatchObject({ recommendedQty: 60, recommendedQtyA: 0, urgency: "high" });
    expect(detail.evidence.items[0].text).toBe("ada santen kotak kecil?");
  });

  it("ranks gap items and builds the category summary", async () => {
    mockFetch(200, {
      storeId: "S01",
      items: [
        { name: "Sambal Ijo", category: "Condiments", requests: 40, daily: [1, 2], trend7dPct: -5.4 },
        { name: "Oat Milk", category: "Beverages", requests: 142, daily: [8, 12], trend7dPct: 64.2, quote: "ada oat milk?", estRevenueIdr: 1000 },
        { name: "Cold Brew", category: "Beverages", requests: 18, daily: [], trend7dPct: 0 },
      ],
    });
    const gaps = await liveApi.getGaps("S01");
    expect(gaps.items.map((g) => [g.rank, g.name, g.trend7d, g.trendDirection])).toEqual([
      [1, "Oat Milk", "+64%", "up"],
      [2, "Sambal Ijo", "-5%", "down"],
      [3, "Cold Brew", "0%", "flat"],
    ]);
    expect(gaps.summary).toEqual({
      totalRequests: 200,
      lostRevenueExposureIdr: 1000,
      categories: [
        { name: "Beverages", count: 160, percent: 0.8 },
        { name: "Condiments", count: 40, percent: 0.2 },
      ],
    });
  });

  it("parses the current backend stubs for sku and gaps", async () => {
    mockFetch(200, {
      storeId: "S01", sku: "SKU-0001",
      product: { name: "SKU-0001", brand: "", category: "", packSize: "", priceIdr: 0, aisle: "" },
      riskType: "reorder",
      kpis: { onHand: 0, lostRevenueIdr: 0, lostRevenueUnits: 0, unmetRequests: 0, stockoutDays: 0 },
      sales: [], forecastA: [], forecastB: [], unmetDaily: [],
      evidence: { total: 0, items: [] },
      reason: { recommendedQtyA: 0, recommendedQtyB: 0, reasonText: "" },
    });
    await expect(liveApi.getSkuDetail("S01", "SKU-0001")).resolves.toMatchObject({ series: [] });
    mockFetch(200, { storeId: "S01", items: [] });
    await expect(liveApi.getGaps("S01")).resolves.toMatchObject({ items: [] });
  });

  it("maps chat citations with null fields", async () => {
    mockFetch(200, {
      reply: "Order 60.",
      sessionId: "m1",
      citations: [{ label: "Santan Kotak Kara 65 ml", sku: "SKU-0001", date: null, quote: "ada santen?" }],
    });
    const chat = await liveApi.managerChat({ storeId: "S01", message: "Why 60?" });
    expect(chat.citations).toEqual([
      { label: "Santan Kotak Kara 65 ml", sku: "SKU-0001", date: undefined, quote: "ada santen?" },
    ]);
  });
});

describe("Firestore documents (docs/api-contract.md §2)", () => {
  const ts = { toDate: () => new Date("2026-10-14T13:00:00Z") };

  it("converts Firestore Timestamps to ISO strings", () => {
    const alert = alertSchema.parse({
      id: "a1",
      storeId: "S01",
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
    expect(adaptSignal("S01", raw)).toBeNull();
  });
});
