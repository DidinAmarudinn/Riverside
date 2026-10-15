import { z } from "zod";
import { API_BASE } from "@/lib/env";
import { apiFetch } from "./client";
import type { ApiClient } from "./contract";
import {
  adaptGaps,
  adaptKioskMessage,
  adaptManagerChat,
  adaptOverview,
  adaptProduct,
  adaptRecommendation,
  adaptSkuDetail,
  adaptStore,
} from "./adapters";
import {
  gapsSchema,
  kioskMessageSchema,
  managerChatSchema,
  overviewSchema,
  productSchema,
  recommendationSchema,
  sessionSchema,
  skuDetailSchema,
  storeSchema,
} from "./schemas";

/**
 * Live adapter. Calls the FastAPI backend behind the `/api` prefix
 * (docs/api-contract.md §3). Every request carries `X-Sandbox-Id` (client.ts).
 * Responses are validated with zod; list endpoints return `{ items }`.
 * Alerts, live signals, KPI deltas and demo state come from Firestore
 * (src/lib/realtime/live.ts), not from this adapter.
 */

const items = <T extends z.ZodType>(schema: T) =>
  z.object({ items: z.array(schema) });

export const liveApi: ApiClient = {
  async getStores() {
    const raw = await apiFetch(`${API_BASE}/stores`, {
      schema: items(storeSchema),
    });
    return raw.items.map(adaptStore);
  },

  async getProducts(q) {
    const raw = await apiFetch(
      `${API_BASE}/products?q=${encodeURIComponent(q)}`,
      { schema: items(productSchema) },
    );
    return raw.items.map(adaptProduct);
  },

  async createKioskSession(storeId) {
    return apiFetch(`${API_BASE}/kiosk/sessions`, {
      method: "POST",
      body: { storeId },
      schema: sessionSchema,
    });
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
      { schema: items(recommendationSchema) },
    );
    return raw.items.map(adaptRecommendation);
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

  async resetDemo() {
    await apiFetch(`${API_BASE}/demo/reset`, { method: "POST" });
  },

  async nextMorning(storeId) {
    await apiFetch(`${API_BASE}/demo/next-morning`, {
      method: "POST",
      body: { storeId },
    });
  },
};
