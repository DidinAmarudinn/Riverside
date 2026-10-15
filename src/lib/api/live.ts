import { z } from "zod";
import { API_BASE } from "@/lib/env";
import { apiFetch } from "./client";
import type { ApiClient } from "./contract";
import {
  adaptAlert,
  adaptDemoState,
  adaptGaps,
  adaptKioskMessage,
  adaptManagerChat,
  adaptOverview,
  adaptProduct,
  adaptRecommendation,
  adaptSignal,
  adaptSkuDetail,
  adaptStore,
} from "./adapters";
import {
  alertSchema,
  demoStateSchema,
  gapsSchema,
  kioskMessageSchema,
  liveSignalSchema,
  managerChatSchema,
  overviewSchema,
  productSchema,
  recommendationSchema,
  sessionSchema,
  skuDetailSchema,
  storeSchema,
} from "./schemas";

/**
 * Live adapter. Calls the FastAPI backend behind the `/api` prefix (build plan
 * §4.3). Responses are validated with zod and mapped to camelCase.
 *
 * NOTE: list endpoints are assumed to return envelopes ({ stores }, { ... }).
 * See docs/fe-decisions.md for the list of assumed endpoints to confirm.
 */

const storeListSchema = z.object({ stores: z.array(storeSchema) });
const productListSchema = z.object({ products: z.array(productSchema) });
const recommendationListSchema = z.object({
  recommendations: z.array(recommendationSchema),
});
const alertListSchema = z.object({ alerts: z.array(alertSchema) });
const signalListSchema = z.object({ signals: z.array(liveSignalSchema) });

export const liveApi: ApiClient = {
  async getStores() {
    const raw = await apiFetch(`${API_BASE}/stores`, {
      schema: storeListSchema,
    });
    return raw.stores.map(adaptStore);
  },

  async getProducts(q) {
    const raw = await apiFetch(
      `${API_BASE}/products?q=${encodeURIComponent(q)}`,
      { schema: productListSchema },
    );
    return raw.products.map(adaptProduct);
  },

  async createKioskSession(storeId) {
    const raw = await apiFetch(`${API_BASE}/kiosk/sessions`, {
      method: "POST",
      body: { storeId },
      schema: sessionSchema,
    });
    return { sessionId: raw.session_id };
  },

  async sendKioskMessage({ sessionId, text }) {
    const raw = await apiFetch(
      `${API_BASE}/kiosk/sessions/${sessionId}/messages`,
      {
        method: "POST",
        body: { text },
        schema: kioskMessageSchema,
      },
    );
    return adaptKioskMessage(raw);
  },

  async getOverview(storeId) {
    const raw = await apiFetch(`${API_BASE}/manager/${storeId}/overview`, {
      schema: overviewSchema,
    });
    return adaptOverview(raw);
  },

  async getRecommendations(storeId, risk) {
    const query = risk ? `?risk=${risk}` : "";
    const raw = await apiFetch(
      `${API_BASE}/manager/${storeId}/recommendations${query}`,
      { schema: recommendationListSchema },
    );
    return raw.recommendations.map(adaptRecommendation);
  },

  async getSkuDetail(storeId, sku) {
    const raw = await apiFetch(
      `${API_BASE}/manager/${storeId}/sku/${encodeURIComponent(sku)}`,
      { schema: skuDetailSchema },
    );
    return adaptSkuDetail(raw);
  },

  async managerChat({ storeId, sessionId, message }) {
    const raw = await apiFetch(`${API_BASE}/manager/${storeId}/chat`, {
      method: "POST",
      body: { sessionId, message },
      schema: managerChatSchema,
    });
    return adaptManagerChat(raw);
  },

  async getGaps(storeId) {
    const raw = await apiFetch(`${API_BASE}/manager/${storeId}/gaps`, {
      schema: gapsSchema,
    });
    return adaptGaps(raw);
  },

  async getDemoState() {
    const raw = await apiFetch(`${API_BASE}/demo/state`, {
      schema: demoStateSchema,
    });
    return adaptDemoState(raw);
  },

  async resetDemo() {
    const raw = await apiFetch(`${API_BASE}/demo/reset`, {
      method: "POST",
      schema: demoStateSchema,
    });
    return adaptDemoState(raw);
  },

  async nextMorning(storeId) {
    const raw = await apiFetch(`${API_BASE}/demo/next-morning`, {
      method: "POST",
      body: { storeId },
      schema: demoStateSchema,
    });
    return adaptDemoState(raw);
  },
};

// Exposed for the realtime polling adapter (no Firestore in this build).
export const liveRealtimeFetchers = {
  async alerts(storeId: string) {
    const raw = await apiFetch(`${API_BASE}/manager/${storeId}/alerts`, {
      schema: alertListSchema,
    });
    return raw.alerts.map(adaptAlert);
  },
  async signals(storeId: string) {
    const raw = await apiFetch(`${API_BASE}/manager/${storeId}/live-signals`, {
      schema: signalListSchema,
    });
    return raw.signals.map(adaptSignal);
  },
};
