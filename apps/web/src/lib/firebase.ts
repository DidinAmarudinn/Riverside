// Read-only Firestore listener for live demand signals. Falls back to null when
// Firebase is not configured (the UI then polls /api/signals/recent instead).
import { initializeApp } from "firebase/app";
import { collection, getFirestore, limit, onSnapshot, orderBy, query } from "firebase/firestore";

const config = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

export const firebaseEnabled = Boolean(config.projectId && config.apiKey);
const db = firebaseEnabled ? getFirestore(initializeApp(config)) : null;

export function listenToSignals(onData: (docs: Record<string, unknown>[]) => void, n = 20): () => void {
  if (!db) return () => {};
  const q = query(collection(db, "signals_live"), orderBy("ts", "desc"), limit(n));
  return onSnapshot(q, (snap) => onData(snap.docs.map((d) => ({ id: d.id, ...d.data() }))));
}
