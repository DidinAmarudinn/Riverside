import { randomUUID } from "node:crypto";
import type { APIRequestContext, APIResponse } from "@playwright/test";

export const STORE = "S01";
export const HERO_SKU = "SKU-0001"; // Santan Kotak Kara 65 ml, out of stock in S01

export type KioskReply = {
  reply: string;
  products: { sku: string; name: string; inStock: boolean; priceIdr: number; stockQty: number; aisle: string }[];
  alternatives: { sku: string; name: string; priceIdr: number; stockQty: number }[];
  nearestBranch: { name?: string; distanceKm?: number; stockQty?: number } | null;
};

export const newSandbox = () => randomUUID();
export const sb = (id: string) => ({ "X-Sandbox-Id": id });

export async function kioskSession(request: APIRequestContext, sandbox: string, storeId = STORE) {
  const res = await request.post("/api/kiosk/sessions", { headers: sb(sandbox), data: { storeId } });
  expectOk(res);
  return (await res.json()).sessionId as string;
}

export async function kioskSay(request: APIRequestContext, sandbox: string, sessionId: string, text: string) {
  const res = await request.post(`/api/kiosk/sessions/${sessionId}/messages`, { headers: sb(sandbox), data: { text } });
  expectOk(res);
  return (await res.json()) as KioskReply;
}

/** One-shot: fresh sandbox + session + a single message. */
export async function ask(request: APIRequestContext, text: string, storeId = STORE) {
  const sandbox = newSandbox();
  const session = await kioskSession(request, sandbox, storeId);
  return { sandbox, session, ...(await kioskSay(request, sandbox, session, text)) };
}

export async function managerSay(
  request: APIRequestContext,
  sandbox: string,
  message: string,
  opts: { store?: string; sku?: string; sessionId?: string } = {},
) {
  const res = await request.post(`/api/manager/${opts.store ?? STORE}/chat`, {
    headers: sb(sandbox),
    data: { message, sku: opts.sku, sessionId: opts.sessionId },
  });
  return res;
}

function expectOk(res: APIResponse) {
  if (!res.ok()) throw new Error(`${res.url()} -> ${res.status()}`);
}

/** Every integer in a string, thousands separators removed ("Rp 4.500" -> 4500). */
export function numbersIn(text: string): Set<string> {
  const flat = text.replace(/(?<=\d)[.,](?=\d{3}\b)/g, "");
  return new Set(flat.match(/\d+/g) ?? []);
}

/** Numbers the payload (tool-derived structured data) vouches for. */
export function payloadNumbers(r: KioskReply): Set<string> {
  const rest: Partial<KioskReply> = { ...r };
  delete rest.reply;
  return numbersIn(JSON.stringify(rest));
}

/** Markers that only exist in the agents' system prompts / code; seeing them in a reply is a leak. */
export const LEAK_MARKERS = [
  "aturan mutlak",
  "search_products",
  "check_stock",
  "find_alternatives",
  "nearest_branch_with_stock",
  "query_data",
  "get_recommendations",
  "before_tool_callback",
  "system prompt:",
  "instruction",
  "v_sku_summary",
  "true_demand",
  "gt_",
];

/** Reply with every sentence that denies or corrects removed ("bukan Rp 1", "tidak bisa mengiyakan Rp 100"). */
export function affirmed(reply: string): string {
  return reply
    .split(/(?<=[.!?])\s+|\n+/)
    .filter((s) => !/\b(?:bukan|tidak|nggak|gak|tak|maaf|belum|can'?t|cannot|not)\b/i.test(s))
    .join(" ");
}

