/**
 * Centralized access to public environment configuration.
 * Only NEXT_PUBLIC_* values are exposed to the browser.
 */

export type DataMode = "mock" | "live";

function readMode(): DataMode {
  const raw = process.env.NEXT_PUBLIC_DATA_MODE;
  return raw === "live" ? "live" : "mock";
}

export const env = {
  dataMode: readMode(),
  defaultStoreId: process.env.NEXT_PUBLIC_DEFAULT_STORE_ID ?? "store_1",
  apiProxyTarget: process.env.NEXT_PUBLIC_API_PROXY_TARGET ?? "",
  featureMultimodal: process.env.NEXT_PUBLIC_FEATURE_MULTIMODAL === "true",
  videoUrl: process.env.NEXT_PUBLIC_VIDEO_URL ?? "",
  githubUrl: process.env.NEXT_PUBLIC_GITHUB_URL ?? "",
  firebase: {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY ?? "",
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID ?? "",
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID ?? "",
  },
} as const;

/**
 * Base path for the public API. Kept relative ("/api") so the same build works
 * behind Firebase Hosting rewrites or the Next dev proxy without CORS.
 */
export const API_BASE = "/api";
