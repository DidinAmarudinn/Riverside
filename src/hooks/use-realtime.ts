"use client";

import { useEffect, useState } from "react";
import { realtime } from "@/lib/realtime";
import type { AlertItem, DemoState, LiveSignal, Metrics } from "@/lib/api/types";
import { useStore } from "./use-store";

export function useMetrics(): Metrics | null {
  const { storeId } = useStore();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  useEffect(
    () => realtime.subscribeMetrics(storeId, setMetrics),
    [storeId],
  );
  return metrics;
}

export function useAlerts(): AlertItem[] | null {
  const { storeId } = useStore();
  const [alerts, setAlerts] = useState<AlertItem[] | null>(null);
  useEffect(() => realtime.subscribeAlerts(storeId, setAlerts), [storeId]);
  return alerts;
}

export function useLiveSignals(): LiveSignal[] | null {
  const { storeId } = useStore();
  const [signals, setSignals] = useState<LiveSignal[] | null>(null);
  useEffect(
    () => realtime.subscribeLiveSignals(storeId, setSignals),
    [storeId],
  );
  return signals;
}

export function useDemoState(): DemoState | null {
  const [state, setState] = useState<DemoState | null>(null);
  useEffect(() => realtime.subscribeDemoState(setState), []);
  return state;
}
