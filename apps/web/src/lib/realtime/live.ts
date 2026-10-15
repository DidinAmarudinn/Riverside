import {
  collection,
  doc,
  limit,
  onSnapshot,
  orderBy,
  query,
  type DocumentData,
} from "firebase/firestore";
import type { z } from "zod";
import type { RealtimeClient, Unsubscribe } from "@/lib/api/contract";
import { liveApi } from "@/lib/api/live";
import {
  adaptAlert,
  adaptDemoState,
  adaptMetrics,
  adaptSignal,
} from "@/lib/api/adapters";
import {
  alertSchema,
  demoStateSchema,
  liveSignalSchema,
  metricsSchema,
} from "@/lib/api/schemas";
import type { LiveSignal } from "@/lib/api/types";
import { firestore } from "@/lib/firebase";
import { sandboxId } from "@/lib/sandbox";

/**
 * Live realtime: read-only Firestore listeners (docs/api-contract.md §2).
 * Base data is shared; demo activity lives under `sandboxes/{sandboxId}`.
 * Without Firebase config, only the KPI row loads (once, from the API).
 */
const FEED_LIMIT = 20;

function parse<T extends z.ZodType>(
  schema: T,
  data: DocumentData | undefined,
  where: string,
): z.infer<T> | null {
  const parsed = schema.safeParse(data ?? {});
  if (parsed.success) return parsed.data;
  console.error("[realtime] document failed validation", {
    where,
    issues: parsed.error.issues,
  });
  return null;
}

const onError = (where: string) => (err: Error) =>
  console.error(`[realtime] ${where} listener failed`, err);

function listenLatest(
  name: "alerts" | "liveSignals",
  orderField: string,
  cb: (docs: DocumentData[]) => void,
): Unsubscribe {
  const db = firestore();
  if (!db) return () => {};
  const q = query(
    collection(db, "sandboxes", sandboxId(), name),
    orderBy(orderField, "desc"),
    limit(FEED_LIMIT),
  );
  return onSnapshot(
    q,
    (snap) => cb(snap.docs.map((d) => ({ id: d.id, ...d.data() }))),
    onError(name),
  );
}

export const liveRealtime: RealtimeClient = {
  subscribeAlerts(storeId, cb) {
    return listenLatest("alerts", "createdAt", (docs) =>
      cb(
        docs
          .map((d) => parse(alertSchema, d, "alerts"))
          .filter((a) => a !== null)
          .map(adaptAlert)
          .filter((a) => a.storeId === storeId),
      ),
    );
  },

  subscribeLiveSignals(storeId, cb) {
    return listenLatest("liveSignals", "ts", (docs) =>
      cb(
        docs
          .map((d) => parse(liveSignalSchema, d, "liveSignals"))
          .filter((s) => s !== null)
          .map((s) => adaptSignal(storeId, s))
          .filter((s): s is LiveSignal => s !== null && s.storeId === storeId),
      ),
    );
  },

  /** KPI row = baseline `metrics/{storeId}` + this visitor's delta. */
  subscribeMetrics(storeId, cb) {
    const db = firestore();
    if (!db) {
      let active = true;
      liveApi
        .getOverview(storeId)
        .then((o) => active && cb(o.metrics))
        .catch((err) => console.error("[realtime] overview failed", err));
      return () => {
        active = false;
      };
    }

    const empty = parse(metricsSchema, {}, "metrics")!;
    let base = empty;
    let delta = empty;
    let baseLoaded = false;
    // Wait for the baseline so the KPI row never flashes delta-only numbers.
    const emit = () =>
      baseLoaded &&
      cb(
        adaptMetrics(storeId, {
          lostRevenueToday: base.lostRevenueToday + delta.lostRevenueToday,
          unmetToday: base.unmetToday + delta.unmetToday,
          stockoutSkus: base.stockoutSkus + delta.stockoutSkus,
          posRefreshedAt: base.posRefreshedAt,
        }),
      );

    const offBase = onSnapshot(
      doc(db, "metrics", storeId),
      (s) => {
        base = parse(metricsSchema, s.data(), "metrics") ?? empty;
        baseLoaded = true;
        emit();
      },
      onError("metrics"),
    );
    const offDelta = onSnapshot(
      doc(db, "sandboxes", sandboxId(), "metrics", storeId),
      (s) => {
        delta = parse(metricsSchema, s.data(), "sandbox metrics") ?? empty;
        emit();
      },
      onError("sandbox metrics"),
    );
    return () => {
      offBase();
      offDelta();
    };
  },

  /** `sandboxes/{sandboxId}`; a missing doc means a fresh (or reset) demo. */
  subscribeDemoState(cb) {
    const db = firestore();
    if (!db) return () => {};
    return onSnapshot(
      doc(db, "sandboxes", sandboxId()),
      (s) => {
        const raw = parse(demoStateSchema, s.data(), "sandbox");
        if (raw) cb(adaptDemoState(raw));
      },
      onError("sandbox"),
    );
  },
};
