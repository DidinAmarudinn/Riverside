"use client";

import { MapPin } from "lucide-react";
import { useStores } from "@/hooks/use-data";
import { useStore } from "@/hooks/use-store";

export function StoreSelector() {
  const { data: stores } = useStores();
  const { storeId, setStoreId } = useStore();

  return (
    <div className="flex items-center gap-2 rounded-xl bg-surface-container-lowest px-4 py-2 shadow-sm">
      <MapPin className="h-[18px] w-[18px] text-primary" aria-hidden />
      <label className="sr-only" htmlFor="store-selector">
        Choose store
      </label>
      <select
        id="store-selector"
        value={storeId}
        onChange={(e) => setStoreId(e.target.value)}
        className="cursor-pointer appearance-none bg-transparent py-0.5 pr-1 text-body-medium text-on-surface focus:outline-none"
      >
        {(stores ?? [{ id: storeId, name: storeId, city: "" }]).map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
            {s.city ? ` – ${s.city}` : ""}
          </option>
        ))}
      </select>
    </div>
  );
}
