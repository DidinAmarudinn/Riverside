import type { Store } from "@/lib/api/types";

export const stores: Store[] = [
  {
    id: "store_1",
    name: "Toko 1",
    city: "Jakarta Selatan (SCBD)",
    lat: -6.2241,
    lng: 106.8089,
  },
  {
    id: "store_2",
    name: "Toko 2",
    city: "Jakarta Barat (Puri Indah)",
    lat: -6.1866,
    lng: 106.7406,
  },
  {
    id: "store_3",
    name: "Toko 3",
    city: "Tangerang Selatan (BSD)",
    lat: -6.3016,
    lng: 106.6531,
  },
];

export function findStore(id: string): Store | undefined {
  return stores.find((s) => s.id === id);
}
