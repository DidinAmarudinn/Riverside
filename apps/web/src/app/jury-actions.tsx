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
const HERO_SKU = "SKU-0001"; // Santan Kotak Kara 65 ml (data/seed_scenarios.yaml hero_santan)

export function JuryActions() {
  const router = useRouter();
  const { toast } = useToast();
  const demoState = useDemoState();
  const resetDemo = useResetDemo();
  const nextMorning = useNextMorning();

  const handleReset = () => {
    if (!window.confirm("Reset the demo to its starting point (Tuesday evening)?")) return;
    resetDemo.mutate(undefined, {
      onSuccess: () =>
        toast({
          title: "Demo reset",
          description: "Scenario: Tuesday evening",
          variant: "success",
        }),
      onError: () =>
        toast({ title: "Could not reset the demo", variant: "error" }),
    });
  };

  const handleNextMorning = () => {
    nextMorning.mutate(undefined, {
      onSuccess: () => {
        toast({
          title: "Next morning done",
          description: "Santan: A = 0, B = 60.",
          variant: "success",
        });
        router.push("/manager");
      },
      onError: () =>
        toast({ title: "Could not run next morning", variant: "error" }),
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
          Scenario: {scenarioLabel(demoState?.scenario)}
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
          title="1 · Ask the shopper kiosk"
          description="Ask for small boxed coconut milk. It is sold out; the agent offers an alternative and a nearby branch."
        />
        <ScenarioLink
          href="/manager"
          icon={BarChart3}
          title="2 · See it on the manager dashboard"
          description="The unmet request appears in the live feed within seconds."
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
                : "3 · Run “Next morning”"}
            </span>
            <span className="mt-0.5 block text-caption text-on-surface-variant">
              Recompute the hero scenario: Santan A = 0, B = 60.
            </span>
          </span>
        </button>
        <ScenarioLink
          href={`/manager?q=${encodeURIComponent(JURY_QUESTION)}&sku=${HERO_SKU}`}
          icon={MessageSquareMore}
          title="4 · Ask the manager agent why"
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
          {resetDemo.isPending ? "Resetting…" : "Reset demo"}
        </Button>
        <span className="text-caption text-on-surface-variant">
          Clears your private sandbox. Other visitors are not affected.
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

// The API stores the scenario name in Indonesian; the jury page is in English.
function scenarioLabel(scenario: string | undefined): string {
  if (!scenario || scenario === "Selasa malam") return "Tuesday evening";
  return scenario;
}
