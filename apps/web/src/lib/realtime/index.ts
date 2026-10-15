import type { RealtimeClient } from "@/lib/api/contract";
import { env } from "@/lib/env";
import { liveRealtime } from "./live";
import { mockRealtime } from "./mock";

/**
 * Realtime entry point. `NEXT_PUBLIC_DATA_MODE` selects the adapter.
 * Mock = in-memory emitter, live = API polling (no Firestore in this build).
 */
export const realtime: RealtimeClient =
  env.dataMode === "live" ? liveRealtime : mockRealtime;
