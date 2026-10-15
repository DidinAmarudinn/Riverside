import type { Product } from "@/lib/api/types";

/**
 * Product master subset used by the demo. `sku` ids are stable so the SKU
 * detail route (`/manager/sku?code=...`) resolves at runtime in mock mode.
 */
export const products: Product[] = [
  {
    sku: "SKU-65ML",
    name: "Santan Kotak 65 ml",
    brand: "Kelapa Utama",
    category: "Cooking Essentials / Dairy & Coconut",
    packSize: "65 ml",
    unit: "pcs",
    priceIdr: 8500,
    aisle: "Lorong 3, Rak B2",
    synonyms: ["santan kotak kecil", "santen", "santan kara kecil", "kelapa kotak"],
    isCarried: true,
    inStock: false,
    stockQty: 0,
  },
  {
    sku: "SKU-2J4K",
    name: "Santan Bubuk Sachet 50g",
    brand: "Kelapa Asli",
    category: "Cooking Essentials / Dairy & Coconut",
    packSize: "50 g",
    unit: "pcs",
    priceIdr: 3800,
    aisle: "Lorong 4",
    synonyms: ["santan bubuk", "santen bubuk"],
    isCarried: true,
    inStock: true,
    stockQty: 18,
  },
  {
    sku: "SKU-8QX1",
    name: "Santan Kental Cair 200ml",
    brand: "Santan Segar",
    category: "Cooking Essentials / Dairy & Coconut",
    packSize: "200 ml",
    unit: "pcs",
    priceIdr: 8500,
    aisle: "Lorong 4",
    synonyms: ["santan cair", "santan kental"],
    isCarried: true,
    inStock: true,
    stockQty: 12,
  },
  {
    sku: "SKU-MG2L",
    name: "Minyak Goreng Sawit 2L",
    brand: "Sawit Prima",
    category: "Oils & Seasoning",
    packSize: "2 L",
    unit: "pouch",
    priceIdr: 35000,
    aisle: "Lorong 5",
    synonyms: ["minyak goreng 2 liter", "minyak 2l"],
    isCarried: true,
    inStock: true,
    stockQty: 14,
  },
  {
    sku: "SKU-BRS5",
    name: "Beras Pandan Wangi 5kg",
    brand: "Pandan Wangi",
    category: "Grains & Rice",
    packSize: "5 kg",
    unit: "sack",
    priceIdr: 72000,
    aisle: "Lorong 7",
    synonyms: ["beras pandan wangi", "beras 5kg"],
    isCarried: true,
    inStock: true,
    stockQty: 8,
  },
  {
    sku: "SKU-GLP1",
    name: "Gula Pasir Kristal Putih 1kg",
    brand: "Gula Nusantara",
    category: "Baking & Sugar",
    packSize: "1 kg",
    unit: "pcs",
    priceIdr: 17000,
    aisle: "Lorong 6",
    synonyms: ["gula pasir", "gula 1kg", "gula curah"],
    isCarried: true,
    inStock: true,
    stockQty: 2,
  },
  {
    sku: "SKU-KCP5",
    name: "Kecap Manis Refill 550ml",
    brand: "Sari Manis",
    category: "Condiments",
    packSize: "550 ml",
    unit: "pouch",
    priceIdr: 21000,
    aisle: "Lorong 5",
    synonyms: ["kecap manis", "kecap refill"],
    isCarried: true,
    inStock: true,
    stockQty: 84,
  },
  {
    sku: "SKU-TLR1",
    name: "Telur Ayam Negeri 1kg",
    brand: "Fresh Farm",
    category: "Fresh",
    packSize: "1 kg",
    unit: "pack",
    priceIdr: 30000,
    aisle: "Lorong 1",
    synonyms: ["telur", "telor ayam"],
    isCarried: true,
    inStock: true,
    stockQty: 10,
  },
];

export function findProduct(sku: string): Product | undefined {
  return products.find((p) => p.sku === sku);
}

export function searchProducts(q: string): Product[] {
  const needle = q.trim().toLowerCase();
  if (!needle) return [];
  return products.filter((p) => {
    const haystack = [p.sku, p.name, p.brand, ...(p.synonyms ?? [])]
      .join(" ")
      .toLowerCase();
    return haystack.includes(needle);
  });
}
