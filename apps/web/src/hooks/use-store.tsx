"use client";

import * as React from "react";
import { env } from "@/lib/env";

interface StoreContextValue {
  storeId: string;
  setStoreId: (id: string) => void;
}

const StoreContext = React.createContext<StoreContextValue | null>(null);

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [storeId, setStoreId] = React.useState(env.defaultStoreId);

  const value = React.useMemo(
    () => ({ storeId, setStoreId }),
    [storeId],
  );

  return (
    <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
  );
}

export function useStore() {
  const ctx = React.useContext(StoreContext);
  if (!ctx) throw new Error("useStore must be used within a StoreProvider");
  return ctx;
}
