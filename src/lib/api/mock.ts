import type { ApiClient } from "./contract";
import type {
  Outcome,
  Recommendation,
  RiskType,
} from "./types";
import { stores } from "@/mocks/stores";
import { searchProducts } from "@/mocks/products";
import { kioskReply, managerChatReply } from "@/mocks/chat";
import { gaps } from "@/mocks/gaps";
import { getSkuDetail } from "@/mocks/sku";
import {
  baseRecommendations,
  heroAfter,
  heroBefore,
} from "@/mocks/recommendations";
import {
  applyNextMorning,
  getDemoState,
  getHeroComputed,
  getMetrics,
  recordKioskSignal,
  resetState,
} from "@/mocks/state";

const riskOrder: Record<RiskType, number> = {
  stockout_risk: 0,
  unmet_spike: 1,
  reorder: 2,
  overstock: 3,
};

/** Simulated latency so loading states are visible in the demo. */
function delay(): Promise<void> {
  const ms = 300 + Math.random() * 900;
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function allRecommendations(): Recommendation[] {
  const hero = getHeroComputed() ? heroAfter : heroBefore;
  return [...baseRecommendations, hero].sort(
    (a, b) => riskOrder[a.riskType] - riskOrder[b.riskType],
  );
}

let sessionCounter = 0;

export const mockApi: ApiClient = {
  async getStores() {
    await delay();
    return stores;
  },

  async getProducts(q) {
    await delay();
    return searchProducts(q);
  },

  async createKioskSession(storeId) {
    await delay();
    sessionCounter += 1;
    return { sessionId: `mock-${storeId}-${Date.now()}-${sessionCounter}` };
  },

  async sendKioskMessage({ sessionId, storeId, text }) {
    await delay();
    const response = kioskReply(text);
    const primary = response.products[0];

    let outcome: Outcome = "not_carried";
    if (primary) {
      outcome = primary.inStock ? "purchased" : "out_of_stock";
    }

    recordKioskSignal({
      id: `sig-live-${Date.now()}`,
      storeId,
      ts: new Date().toISOString(),
      requestedText: text,
      sku: primary?.sku,
      matchedName: primary?.name,
      substituteName: response.alternatives[0]?.name,
      outcome,
      source: `Kiosk ${sessionId.slice(-4)}`,
    });

    return response;
  },

  async getOverview() {
    await delay();
    return {
      metrics: getMetrics(),
      topRisks: allRecommendations().slice(0, 3),
    };
  },

  async getRecommendations(_storeId, risk) {
    await delay();
    const list = allRecommendations();
    return risk ? list.filter((r) => r.riskType === risk) : list;
  },

  async getSkuDetail(_storeId, sku) {
    await delay();
    const detail = getSkuDetail(sku, getHeroComputed());
    if (!detail) {
      throw new Error(`SKU ${sku} tidak ditemukan`);
    }
    return detail;
  },

  async managerChat({ message }) {
    await delay();
    return managerChatReply(message);
  },

  async getGaps() {
    await delay();
    return gaps;
  },

  async getDemoState() {
    await delay();
    return getDemoState();
  },

  async resetDemo() {
    await delay();
    return resetState();
  },

  async nextMorning() {
    await delay();
    return applyNextMorning();
  },
};
