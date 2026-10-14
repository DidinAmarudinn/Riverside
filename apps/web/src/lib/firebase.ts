// Read-only Firestore listeners (contract: docs/api-contract.md §2). Base data is shared; live demo data lives
// under sandboxes/{sandboxId}. Falls back to no-ops when Firebase is not configured.
import { initializeApp } from "firebase/app";
import { collection, doc, getFirestore, limit, onSnapshot, orderBy, query } from "firebase/firestore";

import { sandboxId } from "./api";

const config = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

export const firebaseEnabled = Boolean(config.projectId && config.apiKey);
const db = firebaseEnabled ? getFirestore(initializeApp(config)) : null;

type Docs = (data: Record<string, unknown>[]) => void;

function listen(path: string[], onData: Docs, orderField: string, n: number): () => void {
  if (!db) return () => {};
  const q = query(collection(db, path.join("/")), orderBy(orderField, "desc"), limit(n));
  return onSnapshot(q, (snap) => onData(snap.docs.map((d) => ({ id: d.id, ...d.data() }))));
}

/** "What shoppers ask for now" feed for this visitor. */
export const listenToLiveSignals = (onData: Docs, n = 20) =>
  listen(["sandboxes", sandboxId(), "liveSignals"], onData, "ts", n);

/** Real-time alerts raised during this visitor's demo. */
export const listenToAlerts = (onData: Docs, n = 20) =>
  listen(["sandboxes", sandboxId(), "alerts"], onData, "createdAt", n);

/** KPI row = baseline metrics/{storeId} + this visitor's delta. */
export function listenToMetrics(storeId: string, onData: (base: unknown, delta: unknown) => void): () => void {
  if (!db) return () => {};
  let base: unknown = null;
  let delta: unknown = null;
  const off1 = onSnapshot(doc(db, "metrics", storeId), (s) => onData((base = s.data() ?? null), delta));
  const off2 = onSnapshot(doc(db, "sandboxes", sandboxId(), "metrics", storeId), (s) =>
    onData(base, (delta = s.data() ?? null)),
  );
  return () => {
    off1();
    off2();
  };
}
