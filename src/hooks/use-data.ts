"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { RiskType } from "@/lib/api/types";
import { useStore } from "./use-store";

export function useStores() {
  return useQuery({
    queryKey: ["stores"],
    queryFn: () => api.getStores(),
    staleTime: 5 * 60_000,
  });
}

export function useOverview() {
  const { storeId } = useStore();
  return useQuery({
    queryKey: ["overview", storeId],
    queryFn: () => api.getOverview(storeId),
  });
}

export function useRecommendations(risk?: RiskType) {
  const { storeId } = useStore();
  return useQuery({
    queryKey: ["recommendations", storeId, risk ?? "all"],
    queryFn: () => api.getRecommendations(storeId, risk),
  });
}

export function useSkuDetail(sku: string | null) {
  const { storeId } = useStore();
  return useQuery({
    queryKey: ["sku", storeId, sku],
    queryFn: () => api.getSkuDetail(storeId, sku as string),
    enabled: Boolean(sku),
  });
}

export function useGaps() {
  const { storeId } = useStore();
  return useQuery({
    queryKey: ["gaps", storeId],
    queryFn: () => api.getGaps(storeId),
  });
}

export function useResetDemo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.resetDemo(),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useNextMorning() {
  const { storeId } = useStore();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.nextMorning(storeId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["recommendations"] });
      qc.invalidateQueries({ queryKey: ["overview"] });
      qc.invalidateQueries({ queryKey: ["sku"] });
    },
  });
}
