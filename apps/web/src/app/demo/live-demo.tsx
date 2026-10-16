"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { RotateCcw } from "lucide-react";
import { KioskPanel, type KioskReplyTiming } from "@/app/kiosk/kiosk-chat";
import { useResetDemo, useSkuDetail } from "@/hooks/use-data";
import { useLiveSignals } from "@/hooks/use-realtime";
import { Button } from "@/components/ui/button";
import { StatusTag } from "@/components/ui/status-tag";
import { OutcomePill, OUTCOME_LABEL } from "@/components/manager/outcome-pill";
import { useToast } from "@/components/ui/toast";
import { formatNumber, formatTimeWib } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { LiveSignal } from "@/lib/api/types";

const HERO_SKU = "SKU-0001"; // Santan Kotak Kara 65 ml
const DEMO_TAGS = ["ada santan kotak kecil?", "kak ad santen kotak yg kcil gk?", "ada oat milk?"] as const;

type HopState = "idle" | "on" | "done";
interface Run {
  sentAt: number;
  replyMs?: number;
  repliedAt?: number;
  signal?: LiveSignal;
  signalMs?: number;
}

const signalKey = (s: LiveSignal) => `${s.id}|${s.requestedText}|${s.outcome}`;
const UNMET = new Set(["out_of_stock", "not_carried"]);
// What the shopper asked for: the product, or the words when the store does not sell it.
const askKey = (s: LiveSignal) => s.sku ?? s.requestedText.trim().toLowerCase();

/**
 * Split screen for judges: the real kiosk on the left, the path of the message in the middle, and the
 * manager's view on the right, fed by the same Firestore listener as the dashboard. The manager card
 * follows the product of the visitor's latest signal (the hero product until there is one). Times are
 * measured in this browser: the agent's reply, then the signal's arrival after the reply.
 */
export function LiveDemo() {
  const signals = useLiveSignals();
  const resetDemo = useResetDemo();
  const { toast } = useToast();
  const [run, setRun] = useState<Run | null>(null);
  const [focus, setFocus] = useState<LiveSignal | null>(null);
  const [yourAsks, setYourAsks] = useState<Record<string, number>>({});
  const seen = useRef<Set<string> | null>(null);
  const counted = useRef<Set<string>>(new Set()); // signal ids already counted as an unmet ask

  // Remember what was already in the feed, so only signals from this visit light up the path.
  useEffect(() => {
    if (!signals) return;
    if (seen.current === null) {
      seen.current = new Set(signals.map(signalKey));
      signals.forEach((s) => UNMET.has(s.outcome) && counted.current.add(s.id));
      return;
    }
    const fresh = signals.filter((s) => !seen.current!.has(signalKey(s)));
    fresh.forEach((s) => seen.current!.add(signalKey(s)));
    const latest = fresh[0];
    if (!latest) return;
    setFocus(latest);
    // count a shopper once per product, the first time their ask goes unmet
    const newlyUnmet = fresh.filter((s) => UNMET.has(s.outcome) && !counted.current.has(s.id));
    newlyUnmet.forEach((s) => counted.current.add(s.id));
    if (newlyUnmet.length)
      setYourAsks((c) => {
        const next = { ...c };
        newlyUnmet.forEach((s) => (next[askKey(s)] = (next[askKey(s)] ?? 0) + 1));
        return next;
      });
    setRun((r) => {
      if (!r || r.signal) return r;
      const now = Date.now();
      return { ...r, signal: latest, signalMs: r.repliedAt ? Math.max(0, now - r.repliedAt) : undefined };
    });
  }, [signals]);

  const onSend = useCallback(() => setRun({ sentAt: Date.now() }), []);
  const onReply = useCallback(
    (t: KioskReplyTiming) => setRun((r) => (r ? { ...r, replyMs: t.replyMs, repliedAt: t.repliedAt } : r)),
    [],
  );

  const hop1: HopState = !run ? "idle" : run.replyMs == null ? "on" : "done";
  const hopLater: HopState = !run || run.replyMs == null ? "idle" : run.signal ? "done" : "on";

  const reset = () => {
    resetDemo.mutate(undefined, {
      onSuccess: () => {
        setRun(null);
        setFocus(null);
        setYourAsks({});
        // the sandbox is empty now; a null baseline would swallow the next signal when no empty snapshot follows
        seen.current = new Set();
        counted.current = new Set();
        toast({ title: "Demo reset", description: "Your sandbox is back to the start.", variant: "success" });
      },
      onError: () => toast({ title: "Could not reset the demo", variant: "error" }),
    });
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3 pt-2">
        <div>
          <h1 className="text-[30px] font-medium leading-tight tracking-[-0.03em] text-on-surface sm:text-[36px]">
            Live demo
          </h1>
          <p className="text-body-default text-on-surface-variant">
            Ask the kiosk for something sold out and follow it to the manager.
          </p>
        </div>
        <Button variant="outline" onClick={reset} disabled={resetDemo.isPending}>
          <RotateCcw className="h-4 w-4" aria-hidden />
          {resetDemo.isPending ? "Resetting…" : "Reset demo"}
        </Button>
      </div>

      <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.75fr)_minmax(0,1fr)]">
        <KioskPanel
          quickTags={DEMO_TAGS}
          highlightTag={DEMO_TAGS[0]}
          onSend={onSend}
          onReply={onReply}
          onNewChat={() => setRun(null)}
          className="h-[640px]"
        />

        <section aria-label="What happens to the message" className="flex flex-col gap-2">
          <span className="px-1 text-caption text-on-surface-variant">What happens to the message</span>
          <Hop n={1} state={hop1} title="Shopper agent" body="ADK + Gemini checks stock and answers" time={run?.replyMs != null ? `${(run.replyMs / 1000).toFixed(1)} s` : undefined} />
          <Hop n={2} state={hopLater} title="Pub/Sub" body="the chat is pushed to the extractor, OIDC-verified" />
          <Hop
            n={3}
            state={hopLater}
            title="Signal extraction"
            body={
              run?.signal
                ? `${run.signal.matchedName ?? run.signal.sku ?? "not in the range"} · ${OUTCOME_LABEL[run.signal.outcome] ?? run.signal.outcome}`
                : "product · outcome; rules first, Gemini when unsure"
            }
          />
          <Hop
            n={4}
            state={hopLater}
            title="Firestore"
            body="the manager's feed, live"
            time={run?.signalMs != null ? `+${(run.signalMs / 1000).toFixed(1)} s` : undefined}
          />
          <p className="px-1 text-caption text-on-surface-variant">
            Times are measured in your browser: the agent&apos;s reply, then the signal&apos;s arrival after the reply.
          </p>
        </section>

        <section className="flex min-w-0 flex-col gap-3 rounded-xl bg-surface-container-lowest p-5">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-headline-md text-on-surface">Manager</h2>
            <StatusTag tone="green">Live</StatusTag>
          </div>
          <ManagerFocus focus={focus} yourAsks={focus ? (yourAsks[askKey(focus)] ?? 0) : 0} />

          <span className="mt-1 text-caption text-on-surface-variant">Live demand feed</span>
          <div className="flex max-h-[360px] flex-col gap-2 overflow-y-auto">
            {signals === null ? (
              <div className="h-20 animate-pulse rounded-xl bg-surface-container-low" />
            ) : signals.length === 0 ? (
              <p className="rounded-xl bg-surface-container-low p-4 text-caption text-on-surface-variant">
                No signals yet. Tap a suggestion on the kiosk.
              </p>
            ) : (
              signals.slice(0, 12).map((s) => (
                <div
                  key={s.id}
                  className={cn(
                    "flex flex-col gap-1 rounded-xl p-3 transition-colors duration-1000",
                    run?.signal?.id === s.id ? "bg-secondary-fixed" : "bg-surface-container-low",
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-body-default italic text-on-surface">“{s.requestedText}”</span>
                    <OutcomePill outcome={s.outcome} />
                  </div>
                  <span className="text-caption text-on-surface-variant">
                    {formatTimeWib(s.ts)} WIB · {s.matchedName ?? s.sku ?? "not in the range"}
                  </span>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

/** The manager's view of what the visitor just asked about: the hero product until their first signal. */
function ManagerFocus({ focus, yourAsks }: { focus: LiveSignal | null; yourAsks: number }) {
  const sku = focus ? (focus.sku ?? null) : HERO_SKU;
  const { data: detail } = useSkuDetail(sku);
  const caption = focus ? "From your last question" : "Hero product · ask about another one and this follows it";
  const badge = yourAsks ? (
    <span className="ml-1 rounded-full bg-primary-fixed px-2 py-0.5 font-semibold text-on-primary-fixed">
      +{yourAsks} from you just now
    </span>
  ) : null;

  if (focus && !focus.sku) {
    return (
      <div className="flex flex-col gap-2">
        <FocusTitle caption={caption} name={`“${focus.requestedText}”`} focus={focus} />
        <p className="rounded-lg bg-surface-container-low p-3.5 text-caption text-on-surface-variant">
          This store does not sell it, so there is no forecast to change. Each ask lands on the Gaps list: products
          shoppers want that the store could start carrying{badge}.{" "}
          <Link href="/manager/gaps" className="font-semibold text-primary-container hover:underline">
            See gaps →
          </Link>
        </p>
      </div>
    );
  }

  if (!detail || detail.sku !== sku) {
    return (
      <div className="flex flex-col gap-2">
        <FocusTitle caption={caption} name={focus?.matchedName ?? ""} focus={focus} />
        <div className="h-28 animate-pulse rounded-lg bg-surface-container-low" />
      </div>
    );
  }

  const { kpis, recommendation: rec } = detail;
  const ranOut = kpis.stockoutDays > 0 || kpis.unmetRequests > 0;
  return (
    <div className="flex flex-col gap-3">
      <FocusTitle caption={caption} name={detail.name} focus={focus} />
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-surface-container-low p-3.5">
          <span className="block text-caption text-on-surface">Sales only</span>
          <span className="text-[34px] font-medium leading-tight tracking-[-0.03em] tabular-nums text-on-surface">
            {rec.recommendedQtyA}
          </span>
        </div>
        <div className="rounded-lg bg-primary-fixed p-3.5 text-on-primary-fixed">
          <span className="block text-caption">Demand Radar</span>
          <span className="text-[34px] font-medium leading-tight tracking-[-0.03em] tabular-nums">
            {rec.recommendedQty}
          </span>
        </div>
      </div>
      <p className="text-caption text-on-surface-variant">
        {ranOut ? (
          <>
            <span className="font-semibold text-on-surface">{formatNumber(kpis.unmetRequests)}</span> shoppers asked
            for it during the {kpis.stockoutDays}-day stockout
          </>
        ) : (
          <>It has not run out, so no asks went unmet and both orders agree</>
        )}
        {badge}.{" "}
        <Link href={`/manager/sku?code=${detail.sku}`} className="font-semibold text-primary-container hover:underline">
          See why →
        </Link>
      </p>
    </div>
  );
}

function FocusTitle({ caption, name, focus }: { caption: string; name: string; focus: LiveSignal | null }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <span className="min-w-0">
        <span className="block text-caption text-on-surface-variant">{caption}</span>
        <span className="block truncate text-body-medium font-semibold text-on-surface">{name}</span>
      </span>
      {focus ? <OutcomePill outcome={focus.outcome} /> : null}
    </div>
  );
}

function Hop({ n, state, title, body, time }: { n: number; state: HopState; title: string; body: string; time?: string }) {
  return (
    <div
      className={cn(
        "grid grid-cols-[32px_minmax(0,1fr)_auto] items-center gap-3 rounded-xl p-3.5 transition-colors",
        state === "on" ? "bg-secondary-fixed" : "bg-surface-container-lowest",
      )}
    >
      <span
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-full text-caption font-semibold",
          state === "done" ? "bg-primary text-primary-fixed" : "bg-surface-container-low text-on-surface",
          state === "on" && "animate-pulse",
        )}
      >
        {n}
      </span>
      <span className="min-w-0">
        <span className="block text-body-medium font-semibold text-on-surface">{title}</span>
        <span className="block text-caption text-on-surface-variant">{body}</span>
      </span>
      <span className={cn("text-caption tabular-nums", state === "done" ? "font-semibold text-primary-container" : "text-on-surface-variant")}>
        {time ?? (state === "on" ? "…" : "—")}
      </span>
    </div>
  );
}
