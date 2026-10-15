"use client";

import { useCallback, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Citation } from "@/lib/api/types";

export type AgentMessage =
  | { id: string; role: "user"; text: string; ts: string }
  | {
      id: string;
      role: "assistant";
      text: string;
      ts: string;
      citations: Citation[];
    };

let counter = 0;
function nextId() {
  counter += 1;
  return `chat-${Date.now()}-${counter}`;
}

/** `sku`: the product the chat is about (e.g. from the jury link), sent as context with every message. */
export function useAgentChat(storeId: string, sku?: string) {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionIdRef = useRef<string | undefined>(undefined);

  const send = useCallback(
    async (raw: string) => {
      const message = raw.trim();
      if (!message) return;
      setError(null);
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: "user", text: message, ts: new Date().toISOString() },
      ]);
      setIsSending(true);
      try {
        const res = await api.managerChat({
          storeId,
          sessionId: sessionIdRef.current,
          message,
          sku,
        });
        sessionIdRef.current = res.sessionId;
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            text: res.reply,
            ts: new Date().toISOString(),
            citations: res.citations,
          },
        ]);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Gagal menghubungi agen.",
        );
      } finally {
        setIsSending(false);
      }
    },
    [storeId, sku],
  );

  const reset = useCallback(() => {
    setMessages([]);
    setError(null);
    sessionIdRef.current = undefined;
  }, []);

  return { messages, send, isSending, error, reset };
}
