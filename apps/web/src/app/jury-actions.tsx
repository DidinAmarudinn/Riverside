"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  BarChart3,
  MessageSquareMore,
  RotateCcw,
  Store,
  Sunrise,
} from "lucide-react";
import { useNextMorning, useResetDemo } from "@/hooks/use-data";
import { useDemoState } from "@/hooks/use-realtime";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { formatDateTimeWib } from "@/lib/format";

const JURY_QUESTION = "Why should I order 60 boxes of coconut milk?";

export function JuryActions() {
  const router = useRouter();
  const { toast } = useToast();
  const demoState = useDemoState();
  const resetDemo = useResetDemo();
  const nextMorning = useNextMorning();

  const handleReset = () => {
    if (!window.confirm("Reset demo ke kondisi awal (Selasa malam)?")) return;
    resetDemo.mutate(undefined, {
      onSuccess: () =>
        toast({
          title: "Demo direset",
          description: "Skenario: Selasa malam",
          variant: "success",
        }),
      onError: () =>
        toast({ title: "Gagal reset demo", variant: "error" }),
    });
  };

  const handleNextMorning = () => {
    nextMorning.mutate(undefined, {
      onSuccess: () => {
        toast({
          title: "Next morning dijalankan",
          description: "Santan: A = 0, B = 60.",
          variant: "success",
        });
        router.push("/manager");
      },
      onError: () =>
        toast({ title: "Gagal menjalankan next morning", variant: "error" }),
    });
  };

  return (
    <div className="flex w-full flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <span className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-surface-container-low px-3 py-1.5 text-caption">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
          </span>
          Scenario: {demoState?.scenario ?? "Selasa malam"}
        </span>
        {demoState?.lastResetAt ? (
          <span className="text-caption text-on-surface-variant">
            Last reset: {formatDateTimeWib(demoState.lastResetAt)}
          </span>
        ) : null}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <ScenarioLink
          href="/kiosk"
          icon={Store}
          title="Open Kiosk Shopper"
          description="Ask for a product and watch the assistant handle a stockout."
        />
        <ScenarioLink
          href="/manager"
          icon={BarChart3}
          title="Open Manager Dashboard"
          description="KPIs, ranked recommendations, live feed and alerts."
        />
        <button
          type="button"
          onClick={handleNextMorning}
          disabled={nextMorning.isPending}
          className="flex items-start gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4 text-left shadow-sm transition hover:border-primary/40 hover:shadow disabled:opacity-60"
        >
          <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-secondary-container/30 text-secondary">
            <Sunrise className="h-5 w-5" aria-hidden />
          </span>
          <span>
            <span className="block text-body-medium text-on-surface">
              {nextMorning.isPending
                ? "Running next morning…"
                : "Run “Next morning”"}
            </span>
            <span className="mt-0.5 block text-caption text-on-surface-variant">
              Recompute the hero scenario: Santan A = 0, B = 60.
            </span>
          </span>
        </button>
        <ScenarioLink
          href={`/manager?q=${encodeURIComponent(JURY_QUESTION)}`}
          icon={MessageSquareMore}
          title="Ask the manager agent"
          description="“Why should I order 60 boxes of coconut milk?”"
        />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="danger"
          onClick={handleReset}
          disabled={resetDemo.isPending}
        >
          <RotateCcw className="h-4 w-4" aria-hidden />
          {resetDemo.isPending ? "Mereset…" : "Reset demo"}
        </Button>
        <span className="text-caption text-on-surface-variant">
          Returns the demo to its initial state.
        </span>
      </div>
    </div>
  );
}

function ScenarioLink({
  href,
  icon: Icon,
  title,
  description,
}: {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-start gap-3 rounded-xl border border-outline-variant bg-surface-container-lowest p-4 shadow-sm transition hover:border-primary/40 hover:shadow"
    >
      <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-surface-container-high text-primary-container">
        <Icon className="h-5 w-5" aria-hidden />
      </span>
      <span>
        <span className="block text-body-medium text-on-surface">{title}</span>
        <span className="mt-0.5 block text-caption text-on-surface-variant">
          {description}
        </span>
      </span>
    </Link>
  );
}
