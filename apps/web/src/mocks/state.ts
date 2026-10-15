import type { AlertItem, LiveSignal, Metrics } from "@/lib/api/types";
import { heroAlert, seedAlerts } from "./alerts";
import { heroMetrics, initialMetrics, seedSignals } from "./signals";

/**
 * In-memory, mutable demo state shared by the mock API and the mock realtime
 * emitter. Resetting restores the "Tuesday night" scenario.
 */

type Listener = () => void;

const listeners = new Set<Listener>();

interface MockState {
  heroComputed: boolean;
  scenario: string;
  lastResetAt: string;
  alerts: AlertItem[];
  signals: LiveSignal[];
  metrics: Metrics;
}

function initialState(): MockState {
  return {
    heroComputed: false,
    scenario: "Selasa malam",
    lastResetAt: new Date().toISOString(),
    alerts: seedAlerts.map((a) => ({ ...a })),
    signals: seedSignals.map((s) => ({ ...s })),
    metrics: { ...initialMetrics },
  };
}

let state: MockState = initialState();

function emit() {
  listeners.forEach((l) => l());
}

export function subscribeState(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function getHeroComputed(): boolean {
  return state.heroComputed;
}

export function getMetrics(): Metrics {
  return { ...state.metrics, posRefreshedAt: new Date().toISOString() };
}

export function getAlerts(): AlertItem[] {
  return [...state.alerts].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
}

export function getSignals(): LiveSignal[] {
  return [...state.signals].sort(
    (a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime(),
  );
}

export function getDemoState() {
  return { scenario: state.scenario, lastResetAt: state.lastResetAt };
}

export function resetState() {
  state = initialState();
  emit();
  return getDemoState();
}

/** Recompute the hero scenario ("next morning"). */
export function applyNextMorning() {
  if (state.heroComputed) return getDemoState();
  state.heroComputed = true;
  state.scenario = "Rabu pagi (rekomendasi dihitung ulang)";
  state.lastResetAt = new Date().toISOString();
  state.metrics = { ...heroMetrics, posRefreshedAt: new Date().toISOString() };
  state.alerts = [
    { ...heroAlert, createdAt: new Date().toISOString() },
    ...state.alerts,
  ];
  emit();
  return getDemoState();
}

/** A kiosk question about an out-of-stock item creates a live signal. */
export function recordKioskSignal(signal: LiveSignal) {
  state.signals = [{ ...signal }, ...state.signals];
  state.metrics = {
    ...state.metrics,
    lostRevenueToday: state.metrics.lostRevenueToday + 8_500,
    unmetToday: state.metrics.unmetToday + 1,
    posRefreshedAt: new Date().toISOString(),
  };
  emit();
}
