import { env } from "@/lib/env";
import type { ApiClient } from "./contract";
import { liveApi } from "./live";
import { mockApi } from "./mock";

/**
 * The single data entry point for the UI. `NEXT_PUBLIC_DATA_MODE` selects the
 * adapter; components never import mock/live directly.
 */
export const api: ApiClient = env.dataMode === "live" ? liveApi : mockApi;

export type { ApiClient, RealtimeClient, Unsubscribe } from "./contract";
export * from "./types";
