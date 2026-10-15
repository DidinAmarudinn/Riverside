import type { RealtimeClient } from "@/lib/api/contract";
import {
  getAlerts,
  getDemoState,
  getMetrics,
  getSignals,
  subscribeState,
} from "@/mocks/state";

/**
 * Mock realtime: emits on any in-memory state change (e.g. a kiosk signal or
 * "next morning"). The emitted field shapes are identical to the live adapter.
 */
export const mockRealtime: RealtimeClient = {
  subscribeAlerts(storeId, cb) {
    const push = () => cb(getAlerts().filter((a) => a.storeId === storeId));
    push();
    return subscribeState(push);
  },

  subscribeLiveSignals(storeId, cb) {
    const push = () => cb(getSignals().filter((s) => s.storeId === storeId));
    push();
    return subscribeState(push);
  },

  subscribeMetrics(storeId, cb) {
    const push = () => cb(getMetrics());
    push();
    return subscribeState(push);
  },

  subscribeDemoState(cb) {
    const push = () => cb(getDemoState());
    push();
    return subscribeState(push);
  },
};
