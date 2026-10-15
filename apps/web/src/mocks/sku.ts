import type {
  EvidenceItem,
  ForecastPoint,
  RiskType,
  SkuDetail,
  UnmetPoint,
} from "@/lib/api/types";
import { findProduct } from "./products";
import {
  baseRecommendations,
  heroAfter,
  heroBefore,
} from "./recommendations";

const DAY_MS = 24 * 60 * 60 * 1000;

function isoDaysAgo(days: number): string {
  return new Date(Date.now() - days * DAY_MS).toISOString();
}

const heroPos = [
  13, 14, 12, 15, 16, 14, 13, 15, 17, 16, 14, 12, 15, 16, 17, 15, 14, 13, 15,
  16, 14, 13, 11, 9, 5, 0, 0, 0, 0, 0,
];

const heroForecastA = [
  13, 14, 13, 15, 16, 15, 14, 15, 16, 15, 14, 13, 15, 16, 16, 15, 14, 14, 15,
  15, 14, 13, 12, 10, 6, 2, 0, 0, 0, 0,
];

const heroForecastB = [
  13, 14, 13, 15, 17, 16, 14, 15, 17, 16, 15, 13, 16, 16, 18, 16, 15, 14, 16,
  16, 15, 15, 14, 13, 12, 12, 13, 12, 13, 12,
];

const heroUnmet = [
  0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0,
  6, 8, 7, 9, 8,
];

function buildSeries(): ForecastPoint[] {
  const total = heroPos.length;
  return heroPos.map((pos, i) => {
    const isStockout = i >= 25;
    const a = heroForecastA[i];
    const b = heroForecastB[i];
    return {
      date: isoDaysAgo(total - 1 - i),
      posSales: pos,
      forecastA: a,
      forecastALower: Math.max(0, a - 3),
      forecastAUpper: a + 3,
      forecastB: b,
      forecastBLower: Math.max(0, b - 2),
      forecastBUpper: b + 2,
      isStockout,
    };
  });
}

function buildUnmet(): UnmetPoint[] {
  const total = heroUnmet.length;
  return heroUnmet.map((count, i) => ({
    date: isoDaysAgo(total - 1 - i),
    count,
  }));
}

const heroEvidenceTexts: Array<{
  text: string;
  confidence: number;
  channel: string;
  intent: string;
}> = [
  {
    text: "ada santen kotak kecil?",
    confidence: 0.98,
    channel: "Voice Kiosk #02",
    intent: "Asking for small packaged coconut milk",
  },
  {
    text: "santan kara 65ml abis ya",
    confidence: 0.99,
    channel: "Voice Kiosk #01",
    intent: "Brand name synonym query",
  },
  {
    text: "santen coklat ada ga mbak",
    confidence: 0.94,
    channel: "Staff Barcode Assist",
    intent: "Substitute inquiry",
  },
  {
    text: "kelapa kotak kecil buat masak opor",
    confidence: 0.91,
    channel: "Voice Kiosk #02",
    intent: "Cooking category usage query",
  },
  {
    text: "santan 65 ml promo ada?",
    confidence: 0.96,
    channel: "Terminal #03",
    intent: "Promotion price check inquiry",
  },
  {
    text: "ada santan kotak ga",
    confidence: 0.97,
    channel: "Kiosk Search #04",
    intent: "Availability query",
  },
  {
    text: "santen kara kecil masih ada",
    confidence: 0.95,
    channel: "Voice Kiosk #01",
    intent: "Availability query",
  },
  {
    text: "santan buat kari ada kah",
    confidence: 0.9,
    channel: "Voice Kiosk #03",
    intent: "Cooking category usage query",
  },
];

function buildHeroEvidence(highlightId?: string): {
  total: number;
  items: EvidenceItem[];
} {
  const items = heroEvidenceTexts.map((t, i) => ({
    id: `ev-${i + 1}`,
    ts: isoDaysAgo(Math.floor(i / 3)),
    channel: t.channel,
    text: t.text,
    matchedName: "Santan Kotak 65 ml",
    outcome: (i === 2 ? "substituted" : "out_of_stock") as EvidenceItem["outcome"],
    confidence: t.confidence,
    intent: t.intent,
    highlight: highlightId === `ev-${i + 1}`,
  }));
  return { total: 38, items };
}

function genericSeries(forecastB: number, stockout = false): ForecastPoint[] {
  const total = 30;
  return Array.from({ length: total }, (_, i) => {
    const isStockout = stockout && i >= 25;
    const a = isStockout ? 0 : Math.round(forecastB * 0.35 + (i % 3));
    const b = isStockout ? Math.round(forecastB * 0.9) : forecastB + (i % 4);
    return {
      date: isoDaysAgo(total - 1 - i),
      posSales: isStockout ? 0 : Math.round(a * 0.95),
      forecastA: a,
      forecastALower: Math.max(0, a - 2),
      forecastAUpper: a + 2,
      forecastB: b,
      forecastBLower: Math.max(0, b - 2),
      forecastBUpper: b + 2,
      isStockout,
    };
  });
}

function genericUnmet(totalRequests: number): UnmetPoint[] {
  const total = 30;
  const perDay = totalRequests / 5;
  return Array.from({ length: total }, (_, i) => ({
    date: isoDaysAgo(total - 1 - i),
    count: i >= 25 ? Math.round(perDay) : i % 9 === 0 ? 1 : 0,
  }));
}

export function getSkuDetail(
  sku: string,
  heroComputed: boolean,
  highlightId?: string,
): SkuDetail | undefined {
  const product = findProduct(sku);
  if (!product) return undefined;

  if (sku === "SKU-0001") {
    const rec = heroComputed ? heroAfter : heroBefore;
    return {
      sku,
      name: product.name,
      brand: product.brand,
      category: product.category,
      barcode: "899238810231",
      priceIdr: product.priceIdr,
      riskType: heroComputed ? "stockout_risk" : "reorder",
      kpis: {
        onHand: 0,
        onHandNote: `${product.aisle} empty`,
        lostRevenueIdr: 1530000,
        lostRevenueUnits: 180,
        unmetRequests: 38,
        stockoutDays: 5,
        stockoutSince: isoDaysAgo(5),
      },
      series: buildSeries(),
      dailyUnmet: buildUnmet(),
      recommendation: {
        recommendedQty: rec.recommendedQty,
        recommendedQtyA: rec.recommendedQtyA,
        reasonText: rec.reasonText,
        vendor: "PT Sumber Kelapa Nusantara",
        leadTimeDays: 1,
        urgency: heroComputed ? "high" : "low",
      },
      evidence: buildHeroEvidence(highlightId),
    };
  }

  const rec =
    baseRecommendations.find((r) => r.sku === sku) ?? heroBefore;
  const riskType: RiskType = rec.riskType;
  const isOverstock = riskType === "overstock";
  return {
    sku,
    name: product.name,
    brand: product.brand,
    category: product.category,
    barcode: "8991000000000",
    priceIdr: product.priceIdr,
    riskType,
    kpis: {
      onHand: rec.onHand,
      onHandNote: product.aisle,
      lostRevenueIdr: rec.lostRevenueIdr * 5,
      lostRevenueUnits: Math.round((rec.lostRevenueIdr * 5) / product.priceIdr),
      unmetRequests: rec.unmet7d,
      stockoutDays: rec.onHand === 0 ? 5 : 0,
      stockoutSince: rec.onHand === 0 ? isoDaysAgo(5) : undefined,
    },
    series: genericSeries(rec.forecastB, rec.onHand === 0 && !isOverstock),
    dailyUnmet: genericUnmet(rec.unmet7d),
    recommendation: {
      recommendedQty: rec.recommendedQty,
      recommendedQtyA: rec.recommendedQtyA,
      reasonText: rec.reasonText,
      vendor: "PT Distribusi Nusantara",
      leadTimeDays: 1,
      urgency:
        rec.riskType === "stockout_risk"
          ? "high"
          : rec.riskType === "unmet_spike"
            ? "medium"
            : "low",
    },
    evidence: {
      total: Math.max(rec.unmet7d, 3),
      items: heroEvidenceTexts.slice(0, 5).map((t, i) => ({
        id: `ev-${i + 1}`,
        ts: isoDaysAgo(Math.floor(i / 2) + 1),
        channel: t.channel,
        text: t.text,
        matchedName: product.name,
        outcome: "out_of_stock" as const,
        confidence: t.confidence,
        intent: t.intent,
      })),
    },
  };
}
