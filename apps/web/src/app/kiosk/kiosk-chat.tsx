"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import { useKioskSession } from "@/hooks/use-kiosk-session";
import { useStores } from "@/hooks/use-data";
import { useStore } from "@/hooks/use-store";
import { Button } from "@/components/ui/button";
import { AssistantBubble, ShopperBubble } from "@/components/kiosk/chat-bubble";
import { ChatInput } from "@/components/kiosk/chat-input";
import { cn } from "@/lib/utils";
import { ScrollRow } from "@/components/ui/scroll-row";

const QUICK_TAGS = ["Minyak Goreng 2L", "Santan Kotak 65ml", "Beras Pandan Wangi 5kg", "Telur Ayam Negeri", "Gula Pasir 1kg"];

export interface KioskReplyTiming {
  /** ms from sending the message to the agent's reply on screen */
  replyMs: number;
  /** wall-clock time of the reply, to time the signal that follows */
  repliedAt: number;
  text: string;
}

/**
 * The shopper kiosk as one card: header with the store picker, quick tags, the chat, and the input.
 * The /kiosk page shows it alone; /demo shows it next to the signal and the manager's view.
 */
export function KioskPanel({
  quickTags = QUICK_TAGS,
  highlightTag = "Santan Kotak 65ml",
  onSend,
  onReply,
  onNewChat,
  className,
}: {
  quickTags?: readonly string[];
  highlightTag?: string;
  onSend?: (text: string) => void;
  onReply?: (timing: KioskReplyTiming) => void;
  onNewChat?: () => void;
  className?: string;
}) {
  const { storeId, setStoreId } = useStore();
  const { data: stores } = useStores();
  const { messages, isTyping, error, send, retryLast, startNew, sessionStatus } = useKioskSession(storeId);
  const scrollRef = useRef<HTMLDivElement>(null);
  const pending = useRef<{ t0: number; text: string } | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length, isTyping]);

  // Report how long the agent took, once its reply is on screen.
  useEffect(() => {
    const last = messages[messages.length - 1];
    if (pending.current && last?.role === "assistant" && !isTyping) {
      const now = Date.now();
      onReply?.({ replyMs: now - pending.current.t0, repliedAt: now, text: pending.current.text });
      pending.current = null;
    }
  }, [messages, isTyping, onReply]);

  const lastShopperText = useMemo(
    () => [...messages].reverse().find((m) => m.role === "shopper")?.text,
    [messages],
  );

  const sessionReady = sessionStatus === "success";
  const inputDisabled = !sessionReady || isTyping;
  const sendTimed = useCallback(
    (text: string) => {
      pending.current = { t0: performance.timeOrigin + performance.now(), text };
      onSend?.(text);
      send(text);
    },
    [send, onSend],
  );
  const newChat = () => {
    startNew();
    onNewChat?.();
  };

  return (
    <div className={cn("flex min-h-0 flex-col overflow-hidden rounded-2xl bg-surface-container-lowest", className)}>
      <header className="flex flex-shrink-0 flex-wrap items-center justify-between gap-3 border-b border-outline-variant px-4 py-4 sm:px-5">
        <div className="min-w-0">
          <h1 className="text-headline-md text-on-surface">Ask the Store Assistant</h1>
          <p className="text-caption text-on-surface-variant">Stock check, alternatives and nearby branches</p>
        </div>
        <div className="flex min-w-0 items-center gap-2">
          <label className="sr-only" htmlFor="kiosk-store">
            Choose store
          </label>
          <select
            id="kiosk-store"
            value={storeId}
            onChange={(e) => setStoreId(e.target.value)}
            className="select-pill min-w-0 max-w-[12rem] truncate bg-surface-container-low sm:max-w-none"
          >
            {(stores ?? [{ id: storeId, name: storeId, city: "" }]).map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          <Button size="md" onClick={newChat}>
            New chat
          </Button>
        </div>
      </header>

      <div className="flex flex-shrink-0 items-center gap-2 border-b border-outline-variant px-4 py-3 sm:px-5">
        <span className="flex-shrink-0 text-caption text-on-surface-variant">Popular:</span>
        <ScrollRow className="flex-1">
        {quickTags.map((tag) => (
          <button
            key={tag}
            type="button"
            disabled={inputDisabled}
            onClick={() => sendTimed(tag)}
            className={cn(
              "tap-active flex-shrink-0 rounded-full px-3.5 py-2 text-body-default text-on-surface transition disabled:opacity-50",
              tag === highlightTag
                ? "bg-secondary-fixed font-semibold shadow-[inset_0_0_0_1.5px_var(--color-primary-fixed)]"
                : "bg-surface-container-low hover:bg-surface-container-high",
            )}
          >
            {tag}
          </button>
        ))}
        </ScrollRow>
      </div>

      <div ref={scrollRef} className="custom-scrollbar flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto bg-surface-container-low px-4 py-5 sm:px-5">
        {messages.length === 0 ? (
          <div className="flex flex-col gap-3">
            <div className="max-w-[85%] self-start rounded-[20px] rounded-bl-md bg-surface-container-lowest px-4 py-3 text-on-surface">
              Halo! Mau cari barang apa hari ini?
              <span className="mt-1 block text-caption text-on-surface-variant">Hi! What are you looking for today?</span>
            </div>
            <p className="max-w-md text-caption text-on-surface-variant">
              Shoppers here write in everyday Indonesian, typos and all. Try{" "}
              <span className="font-semibold text-on-surface">&ldquo;ada santan kotak kecil?&rdquo;</span> (do you
              have small boxed coconut milk?). All stock and stores are simulated.
            </p>
          </div>
        ) : null}

        {messages.map((message) =>
          message.role === "shopper" ? (
            <ShopperBubble key={message.id} message={message} />
          ) : (
            <AssistantBubble key={message.id} message={message} />
          ),
        )}

        {isTyping ? (
          <div className="flex items-center gap-1.5 self-start rounded-[20px] bg-surface-container-lowest px-4 py-3.5">
            <span className="h-2 w-2 animate-bounce rounded-full bg-outline [animation-delay:-0.3s]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-outline [animation-delay:-0.15s]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-outline" />
          </div>
        ) : null}

        {error ? (
          <div className="flex flex-col items-start gap-2 rounded-xl bg-status-red-bg p-4">
            <p className="text-body-default text-status-red">Sorry, something went wrong: {error}</p>
            {lastShopperText ? (
              <Button variant="outline" size="sm" onClick={() => retryLast(lastShopperText)}>
                Try again
              </Button>
            ) : null}
          </div>
        ) : null}
      </div>

      <footer className="flex-shrink-0 border-t border-outline-variant px-4 py-3.5 sm:px-5">
        <ChatInput disabled={inputDisabled} onSend={sendTimed} />
      </footer>
    </div>
  );
}

export function KioskChat() {
  return <KioskPanel className="mx-auto h-[calc(100dvh-190px)] min-h-[560px] w-full max-w-[880px]" />;
}
