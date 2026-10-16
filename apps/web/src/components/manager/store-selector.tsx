"use client";

import { useStores } from "@/hooks/use-data";
import { useStore } from "@/hooks/use-store";

export function StoreSelector() {
  const { data: stores } = useStores();
  const { storeId, setStoreId } = useStore();

  return (
    <>
      <label className="sr-only" htmlFor="store-selector">
        Choose store
      </label>
      <select
        id="store-selector"
        value={storeId}
        onChange={(e) => setStoreId(e.target.value)}
        className="select-pill bg-surface-container-lowest"
      >
        {(stores ?? [{ id: storeId, name: storeId, city: "" }]).map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>
    </>
  );
}
