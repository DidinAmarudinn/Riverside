"use client";

import { useEffect, useMemo, useRef } from "react";
import { MapPin, Radar, RotateCcw, Zap } from "lucide-react";
import { useKioskSession } from "@/hooks/use-kiosk-session";
import { useStores } from "@/hooks/use-data";
import { useStore } from "@/hooks/use-store";
import { Button } from "@/components/ui/button";
import { AssistantBubble, ShopperBubble } from "@/components/kiosk/chat-bubble";
import { ChatInput } from "@/components/kiosk/chat-input";
import { cn } from "@/lib/utils";

const QUICK_TAGS = [
  "Minyak Goreng 2L",
  "Santan Kotak 65ml",
  "Beras Pandan Wangi 5kg",
  "Telur Ayam Negeri",
  "Gula Pasir 1kg",
];

export function KioskChat() {
  const { storeId, setStoreId } = useStore();
  const { data: stores } = useStores();
  const {
    messages,
    isTyping,
    error,
    send,
    retryLast,
    startNew,
    sessionStatus,
  } = useKioskSession(storeId);

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages.length, isTyping]);

  const lastShopperText = useMemo(() => {
    const lastShopper = [...messages]
      .reverse()
      .find((m) => m.role === "shopper");
    return lastShopper?.text;
  }, [messages]);

  const storeName = stores?.find((s) => s.id === storeId)?.name ?? "Toko 1";
  const sessionReady = sessionStatus === "success";
  const inputDisabled = !sessionReady || isTyping;

  return (
    <div className="flex min-h-screen flex-col bg-kiosk-bg text-slate-800">
      <header className="sticky top-0 z-30 flex-shrink-0 border-b border-slate-200 bg-white px-4 py-4 shadow-sm sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3 sm:gap-4">
          <div className="flex min-w-0 items-center gap-3.5">
            <div className="hidden h-12 w-12 flex-shrink-0 items-center justify-center rounded-2xl border sm:flex border-teal-200 bg-teal-50 text-brand-teal shadow-inner">
              <Radar className="h-6 w-6" aria-hidden />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold leading-tight tracking-tight text-slate-900 sm:text-xl">
                  Tanya Asisten Toko
                </h1>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
                  ONLINE
                </span>
              </div>
              <p className="hidden text-xs text-slate-500 sm:block">
                Layanan mandiri pintar &amp; pencarian stok instan
              </p>
            </div>
          </div>

          <div className="flex min-w-0 items-center gap-2.5">
            <div className="flex min-w-0 items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-100 px-3.5 py-2 text-xs font-semibold text-slate-700">
              <MapPin className="h-4 w-4 text-brand-teal" aria-hidden />
              <label className="sr-only" htmlFor="kiosk-store">
                Pilih toko
              </label>
              <select
                id="kiosk-store"
                value={storeId}
                onChange={(e) => setStoreId(e.target.value)}
                className="min-w-0 max-w-[11rem] cursor-pointer appearance-none truncate bg-transparent focus:outline-none sm:max-w-none"
              >
                {(stores ?? [{ id: storeId, name: storeName, city: "" }]).map(
                  (s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                      {s.city ? ` – ${s.city.split(" ")[0]}` : ""}
                    </option>
                  ),
                )}
              </select>
            </div>
            <button
              type="button"
              onClick={startNew}
              className="tap-active flex flex-shrink-0 items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-bold sm:px-4 text-slate-700 transition hover:bg-slate-100"
            >
              <RotateCcw className="h-4 w-4 text-slate-500" aria-hidden />
              Mulai baru
            </button>
          </div>
        </div>

        <div className="mt-3.5 flex items-center gap-2 overflow-x-auto border-t border-slate-100 pt-3 pb-0.5 no-scrollbar">
          <span className="flex flex-shrink-0 items-center gap-1 text-xs font-medium text-slate-500">
            <Zap className="h-3.5 w-3.5 text-status-amber" aria-hidden />
            Sering dicari:
          </span>
          {QUICK_TAGS.map((tag) => {
            const highlighted = tag === "Santan Kotak 65ml";
            return (
              <button
                key={tag}
                type="button"
                disabled={inputDisabled}
                onClick={() => send(tag)}
                className={cn(
                  "tap-active flex-shrink-0 rounded-lg px-3 py-1.5 text-xs transition disabled:opacity-60",
                  highlighted
                    ? "border border-teal-200 bg-teal-50 font-semibold text-brand-teal"
                    : "border border-slate-200 bg-slate-100 font-medium text-slate-700 hover:bg-slate-200",
                )}
              >
                {tag}
              </button>
            );
          })}
        </div>
      </header>

      <main
        ref={scrollRef}
        className="custom-scrollbar mx-auto w-full max-w-4xl flex-1 space-y-6 overflow-y-auto px-5 py-6"
      >
        <div className="flex justify-center">
          <span className="rounded-full bg-slate-200 px-3.5 py-1 text-[11px] font-semibold tracking-wide text-slate-600">
            Hari ini • sesi kiosk
          </span>
        </div>

        {messages.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-brand-teal shadow-sm">
              <Radar className="h-7 w-7" aria-hidden />
            </div>
            <div>
              <p className="text-base font-semibold text-slate-700">
                Mau cari barang apa hari ini?
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Tulis nama barang atau ketuk salah satu tag di atas.
              </p>
              <p className="mx-auto mt-4 max-w-sm text-xs text-slate-400">
                Shopper kiosk in everyday Indonesian. Try{" "}
                <span className="font-semibold text-slate-500">
                  &ldquo;ada santan kotak kecil?&rdquo;
                </span>{" "}
                (do you have small boxed coconut milk?). All stock and stores are
                simulated.
              </p>
            </div>
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
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl bg-brand-teal text-white shadow-md">
              <Radar className="h-5 w-5" aria-hidden />
            </div>
            <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm border border-slate-200/90 bg-white px-4 py-3.5 shadow-sm">
              <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400" />
            </div>
          </div>
        ) : null}

        {error ? (
          <div className="mx-auto flex max-w-md flex-col items-center gap-2 rounded-2xl border border-status-red-border bg-status-red-bg p-4 text-center">
            <p className="text-sm text-status-red">
              Maaf, ada kendala: {error}
            </p>
            {lastShopperText ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => retryLast(lastShopperText)}
              >
                Coba lagi
              </Button>
            ) : null}
          </div>
        ) : null}
      </main>

      <footer className="sticky bottom-0 z-30 flex-shrink-0 border-t border-slate-200 bg-white px-4 py-4 sm:px-6 sm:py-5 shadow-[0_-8px_20px_rgba(0,0,0,0.04)]">
        <div className="mx-auto w-full max-w-4xl">
          <ChatInput disabled={inputDisabled} onSend={send} />
        </div>
      </footer>
    </div>
  );
}
