"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { realtime } from "@/lib/realtime";
import type { KioskMessageResponse } from "@/lib/api/types";

export type KioskMessage =
  | { id: string; role: "shopper"; text: string; ts: string }
  | {
      id: string;
      role: "assistant";
      text: string;
      ts: string;
      response: KioskMessageResponse;
    };

let counter = 0;
function nextId() {
  counter += 1;
  return `msg-${Date.now()}-${counter}`;
}

export function useKioskSession(storeId: string) {
  const [sessionEpoch, setSessionEpoch] = useState(0);
  const sessionQuery = useQuery({
    queryKey: ["kiosk-session", storeId, sessionEpoch],
    queryFn: () => api.createKioskSession(storeId),
    staleTime: Infinity,
    refetchOnMount: false,
  });
  const sessionId = sessionQuery.data?.sessionId ?? null;

  const [messages, setMessages] = useState<KioskMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback(
    async (raw: string) => {
      const text = raw.trim();
      if (!text || !sessionId) return;

      setError(null);
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: "shopper", text, ts: new Date().toISOString() },
      ]);
      setIsTyping(true);
      try {
        const response = await api.sendKioskMessage({
          sessionId,
          storeId,
          text,
        });
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            text: response.reply,
            ts: new Date().toISOString(),
            response,
          },
        ]);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Gagal mengirim pesan.",
        );
      } finally {
        setIsTyping(false);
      }
    },
    [storeId, sessionId],
  );

  const retryLast = useCallback(
    (text: string) => {
      setMessages((prev) => {
        const copy = [...prev];
        if (copy.length && copy[copy.length - 1]?.role === "shopper") {
          copy.pop();
        }
        return copy;
      });
      void send(text);
    },
    [send],
  );

  const startNew = useCallback(() => {
    setMessages([]);
    setError(null);
    setSessionEpoch((e) => e + 1);
  }, []);

  // "Reset demo" (often clicked in another tab) deletes this sandbox's kiosk chats on the server, so the
  // old session would 404. Start a fresh chat when a reset is newer than the current session.
  const sessionCreatedAt = useRef(0);
  useEffect(() => {
    sessionCreatedAt.current = sessionQuery.dataUpdatedAt;
  }, [sessionQuery.dataUpdatedAt]);
  useEffect(() => {
    let handled: string | undefined;
    return realtime.subscribeDemoState((state) => {
      const resetAt = state.lastResetAt;
      if (!resetAt || resetAt === handled) return;
      // no session yet: the next one is created after this reset anyway
      if (sessionCreatedAt.current && Date.parse(resetAt) > sessionCreatedAt.current) {
        handled = resetAt;
        startNew();
      }
    });
  }, [startNew]);

  return {
    sessionId,
    sessionStatus: sessionQuery.status,
    sessionError: sessionQuery.error,
    refetchSession: sessionQuery.refetch,
    messages,
    isTyping,
    error,
    send,
    retryLast,
    startNew,
  };
}
