import type {
  Citation,
  KioskMessageResponse,
  ManagerChatResponse,
} from "@/lib/api/types";

/** Exact sample questions from the build plan §9. */
export const sampleQuestions = [
  "Why should I order 60 boxes of coconut milk?",
  "Which products are most at risk of stocking out this week?",
  "What are shoppers asking for that we don't sell?",
  "How much revenue did we lose to stockouts yesterday?",
] as const;

interface Canned {
  match: RegExp;
  reply: string;
  citations: Citation[];
}

const canned: Canned[] = [
  {
    match: /60|coconut|santan/i,
    reply:
      "38 shoppers asked for Santan Kotak 65 ml over the last 5 days while on-hand was 0. POS shows 0 sales because shelves were empty, not because demand disappeared. Blending kiosk intent raises Forecast B to 60 units, versus 0 for POS-only Forecast A.",
    citations: [
      {
        label: "Santan Kotak 65 ml",
        sku: "SKU-65ML",
        snippet: "ada santen kotak kecil?",
      },
      {
        label: "Evidence · 38 conversations",
        sku: "SKU-65ML",
        snippet: "santan kara 65ml abis ya",
      },
    ],
  },
  {
    match: /risk|stocking out|stockout/i,
    reply:
      "Top risk SKUs this week: Santan Kotak 65 ml (stockout, 0 on-hand, B = 60), Gula Pasir Kristal Putih 1kg (2 units left, 12 unmet hits), and Minyak Goreng Sawit 2L (promo surge, +65 requests). Together they represent Rp 1.052.000 in at-risk revenue.",
    citations: [
      { label: "Santan Kotak 65 ml", sku: "SKU-65ML" },
      { label: "Gula Pasir 1kg", sku: "SKU-GLP1" },
      { label: "Minyak Goreng 2L", sku: "SKU-MG2L" },
    ],
  },
  {
    match: /don't sell|don.?t sell|not sell|not carried|don't carry/i,
    reply:
      "Shoppers logged 142 requests for Oat Milk Barista Edition and 98 for Matcha Powder ceremonial, and we carry neither. Plant-based dairy alternatives make up 45% of uncarried queries — an estimated Rp 32,8 jt monthly revenue exposure.",
    citations: [
      { label: "Oat Milk Barista Edition", snippet: "ada oat milk yang buat kopi ga?" },
      { label: "Assortment gaps · 8 items" },
    ],
  },
  {
    match: /revenue|yesterday|lose|lost/i,
    reply:
      "Verified stockouts cost Rp 1.980.000 yesterday, concentrated in fresh dairy and instant seasoning refills. The single largest contributor was Santan Kotak 65 ml, which alone lost an estimated Rp 323.000.",
    citations: [
      { label: "Santan Kotak 65 ml", sku: "SKU-65ML", date: "yesterday" },
      { label: "Lost revenue ledger" },
    ],
  },
];

const genericReply =
  "I can help with reorder recommendations, stockout risk, assortment gaps and lost revenue. Try one of the suggested questions for a data-backed answer with citations.";

export function managerChatReply(message: string): ManagerChatResponse {
  const found = canned.find((c) => c.match.test(message));
  return {
    sessionId: "mock-manager-session",
    reply: found ? found.reply : genericReply,
    citations: found ? found.citations : [],
  };
}

export function kioskReply(text: string): KioskMessageResponse {
  const q = text.toLowerCase();
  const asksCoconut =
    q.includes("santan") ||
    q.includes("santen") ||
    q.includes("kelapa") ||
    q.includes("65");

  if (asksCoconut) {
    return {
      reply:
        "Maaf kak, santan kotak 65 ml lagi habis. Ada santan sachet merek lain di Lorong 4, atau cabang Toko 2 (2,1 km) masih ada stok.",
      products: [
        {
          sku: "SKU-65ML",
          name: "Santan Kotak 65 ml",
          subtitle: "Kemasan Tetra Pak • Rasa Original Gurih",
          priceIdr: 8500,
          inStock: false,
          aisle: "Lorong 3, Rak B2",
          stockQty: 0,
        },
      ],
      alternatives: [
        {
          sku: "SKU-2J4K",
          name: "Santan Bubuk Sachet 50g",
          subtitle: "Merek Kelapa Asli",
          priceIdr: 3800,
          inStock: true,
          aisle: "Lorong 4",
          stockQty: 18,
        },
        {
          sku: "SKU-8QX1",
          name: "Santan Kental Cair 200ml",
          subtitle: "Merek Santan Segar",
          priceIdr: 8500,
          inStock: true,
          aisle: "Lorong 4",
          stockQty: 12,
        },
      ],
      nearestBranch: {
        storeId: "store_2",
        name: "Toko 2",
        distanceKm: 2.1,
        stockQty: 24,
      },
    };
  }

  if (q.includes("minyak")) {
    return {
      reply:
        "Minyak goreng sawit 2L tersedia di Lorong 5, stok masih 14 pouch kak.",
      products: [
        {
          sku: "SKU-MG2L",
          name: "Minyak Goreng Sawit 2L",
          subtitle: "Pouch 2 liter",
          priceIdr: 35000,
          inStock: true,
          aisle: "Lorong 5",
          stockQty: 14,
        },
      ],
      alternatives: [],
    };
  }

  if (q.includes("gula")) {
    return {
      reply:
        "Gula pasir kristal putih 1kg tinggal 2 pcs ya kak, ada alternatif gula batu di Lorong 6.",
      products: [
        {
          sku: "SKU-GLP1",
          name: "Gula Pasir Kristal Putih 1kg",
          subtitle: "Kemasan 1 kg",
          priceIdr: 17000,
          inStock: true,
          aisle: "Lorong 6",
          stockQty: 2,
        },
      ],
      alternatives: [],
    };
  }

  return {
    reply:
      "Maaf kak, aku belum menemukan produk itu. Coba tulis nama atau merek lain ya, contohnya \"santan kotak\" atau \"minyak goreng 2L\".",
    products: [],
    alternatives: [],
  };
}
