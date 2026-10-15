import type { RealtimeClient } from "@/lib/api/contract";
import { liveApi, liveRealtimeFetchers } from "@/lib/api/live";

/**
 * Live realtime implemented with HTTP polling (this build has no Firestore).
 * Swap this module for Firestore `onSnapshot` later behind the same interface;
 * components are unaffected. See docs/fe-decisions.md.
 */
const POLL_MS = 5_000;

function poll<T>(
  fetcher: () => Promise<T>,
  cb: (value: T) => void,
): () => void {
  let active = true;

  const tick = async () => {
    try {
      const value = await fetcher();
      if (active) cb(value);
    } catch (err) {
      console.error("[realtime] poll failed", err);
    }
  };

  void tick();
  const id = setInterval(tick, POLL_MS);
  return () => {
    active = false;
    clearInterval(id);
  };
}

export const liveRealtime: RealtimeClient = {
  subscribeAlerts(storeId, cb) {
    return poll(() => liveRealtimeFetchers.alerts(storeId), cb);
  },

  subscribeLiveSignals(storeId, cb) {
    return poll(() => liveRealtimeFetchers.signals(storeId), cb);
  },

  subscribeMetrics(storeId, cb) {
    return poll(
      () => liveApi.getOverview(storeId).then((o) => o.metrics),
      cb,
    );
  },

  subscribeDemoState(cb) {
    return poll(() => liveApi.getDemoState(), cb);
  },
};
