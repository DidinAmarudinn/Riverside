import { getApps, initializeApp } from "firebase/app";
import { getFirestore, type Firestore } from "firebase/firestore";
import { env } from "@/lib/env";

/**
 * Lazily initialised Firestore client for live realtime (read-only; rules in
 * infra/firestore.rules). Returns null during static prerender or when the
 * NEXT_PUBLIC_FIREBASE_* config is missing.
 */
let db: Firestore | null | undefined;

export function firestore(): Firestore | null {
  if (db !== undefined) return db;
  if (typeof window === "undefined") return null;
  const { apiKey, projectId, appId } = env.firebase;
  if (!apiKey || !projectId) {
    console.warn("[realtime] Firebase is not configured; live updates are off.");
    db = null;
    return db;
  }
  const app = getApps()[0] ?? initializeApp({ apiKey, projectId, appId });
  db = getFirestore(app);
  return db;
}
