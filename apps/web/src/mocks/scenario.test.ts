import { beforeEach, describe, expect, it } from "vitest";
import {
  applyNextMorning,
  getDemoState,
  getHeroComputed,
  getMetrics,
  recordKioskSignal,
  resetState,
} from "./state";
import { getSkuDetail } from "./sku";
import { gaps } from "./gaps";

describe("hero scenario (Santan Kotak 65 ml)", () => {
  beforeEach(() => {
    resetState();
  });

  it("starts on Tuesday night with the hero not yet high risk", () => {
    expect(getHeroComputed()).toBe(false);
    expect(getDemoState().scenario).toBe("Selasa malam");
    const detail = getSkuDetail("SKU-0001", false);
    expect(detail?.riskType).toBe("reorder");
    expect(detail?.recommendation.recommendedQty).toBe(6);
  });

  it("after next morning returns A = 0, B = 60 and 38 unmet", () => {
    applyNextMorning();
    expect(getHeroComputed()).toBe(true);
    const detail = getSkuDetail("SKU-0001", true);
    expect(detail?.riskType).toBe("stockout_risk");
    expect(detail?.recommendation.recommendedQty).toBe(60);
    expect(detail?.kpis.unmetRequests).toBe(38);
    const stockoutDays = detail?.series.filter((p) => p.isStockout) ?? [];
    expect(stockoutDays).toHaveLength(5);
    const last5Unmet = (detail?.dailyUnmet ?? [])
      .slice(-5)
      .reduce((sum, p) => sum + p.count, 0);
    expect(last5Unmet).toBe(38);
  });

  it("a kiosk signal increments unmet requests", () => {
    const before = getMetrics().unmetToday;
    recordKioskSignal({
      id: "test-signal",
      storeId: "S01",
      ts: new Date().toISOString(),
      requestedText: "ada santan kotak kecil?",
      sku: "SKU-0001",
      matchedName: "Santan Kotak 65 ml",
      outcome: "out_of_stock",
    });
    expect(getMetrics().unmetToday).toBe(before + 1);
  });

  it("reset restores the initial metrics", () => {
    applyNextMorning();
    resetState();
    expect(getHeroComputed()).toBe(false);
    expect(getMetrics().stockoutSkus).toBe(6);
  });
});

describe("assortment gaps", () => {
  it("has 8 rows and oat milk at rank 1 with 142 requests", () => {
    expect(gaps.items.length).toBeGreaterThanOrEqual(8);
    expect(gaps.items[0].name).toContain("Oat Milk");
    expect(gaps.items[0].requests).toBe(142);
  });
});
