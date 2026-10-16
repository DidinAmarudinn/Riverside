import type { z } from "zod";
import { sandboxId } from "@/lib/sandbox";

export const REQUEST_TIMEOUT_MS = 20_000;

export class ApiError extends Error {
  code: string;
  status: number;
  isRateLimited: boolean;

  constructor(message: string, opts: { code?: string; status?: number } = {}) {
    super(message);
    this.name = "ApiError";
    this.code = opts.code ?? "unknown";
    this.status = opts.status ?? 0;
    this.isRateLimited = this.status === 429;
  }
}

interface FetchOptions<T> {
  method?: "GET" | "POST";
  body?: unknown;
  schema?: z.ZodType<T>;
  signal?: AbortSignal;
}

function parseErrorMessage(payload: unknown): string {
  if (payload && typeof payload === "object" && "error" in payload) {
    const err = (payload as { error?: { message?: string } }).error;
    if (err?.message) return err.message;
  }
  return "Terjadi kesalahan saat menghubungi server.";
}

async function rawFetch<T>(
  path: string,
  { method = "GET", body, schema, signal }: FetchOptions<T>,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const onAbort = () => controller.abort();
  signal?.addEventListener("abort", onAbort);

  try {
    const res = await fetch(path, {
      method,
      headers: {
        "X-Sandbox-Id": sandboxId(),
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    const text = await res.text();
    const json = text ? JSON.parse(text) : null;

    if (!res.ok) {
      const message = res.status === 429
        ? "Terlalu cepat, coba lagi sebentar."
        : parseErrorMessage(json);
      throw new ApiError(message, {
        code: `http_${res.status}`,
        status: res.status,
      });
    }

    if (res.status === 204) return undefined as T;

    if (schema) {
      const parsed = schema.safeParse(json);
      if (!parsed.success) {
        console.error("[api] response failed validation", {
          path,
          issues: parsed.error.issues,
        });
        throw new ApiError("Unexpected response from the server.", {
          code: "invalid_response",
          status: res.status,
        });
      }
      return parsed.data;
    }

    return json as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError("Permintaan melebihi batas waktu 20 detik.", {
        code: "timeout",
      });
    }
    throw new ApiError(
      err instanceof Error ? err.message : "Could not reach the server.",
      { code: "network" },
    );
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener("abort", onAbort);
  }
}

export async function apiFetch<T>(
  path: string,
  options: FetchOptions<T> = {},
): Promise<T> {
  const isGet = (options.method ?? "GET") === "GET";
  try {
    return await rawFetch(path, options);
  } catch (err) {
    if (isGet && err instanceof ApiError && err.status !== 429) {
      return rawFetch(path, options);
    }
    throw err;
  }
}
