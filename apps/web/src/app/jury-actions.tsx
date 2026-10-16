"use client";

import Link from "next/link";
import { RotateCcw } from "lucide-react";
import { useResetDemo } from "@/hooks/use-data";
import { useDemoState } from "@/hooks/use-realtime";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { formatDateTimeWib } from "@/lib/format";

const JURY_QUESTION = "Why should I order 64 boxes of coconut milk?";
const HERO_SKU = "SKU-0001"; // Santan Kotak Kara 65 ml (data/seed_scenarios.yaml hero_santan)

const STEPS = [
  {
    href: "/demo",
    title: "Ask the kiosk",
    body: "Ask for small boxed coconut milk. It is sold out; the agent offers an alternative and a nearby branch.",
    go: "Open the live demo",
  },
  {
    href: "/manager",
    title: "See it on the dashboard",
    body: "The request reaches the manager's feed in about two seconds, and the coconut milk tops the reorder list.",
    go: "Open the manager dashboard",
  },
  {
    href: `/manager?q=${encodeURIComponent(JURY_QUESTION)}&sku=${HERO_SKU}`,
    title: "Ask why 64",
    body: "The manager agent answers with the numbers and the shoppers' own words. A sales-only forecast would order 10.",
    go: "Ask the manager agent",
  },
] as const;

export function JuryActions() {
  const { toast } = useToast();
  const demoState = useDemoState();
  const resetDemo = useResetDemo();

  const handleReset = () => {
    if (!window.confirm("Reset the demo to its starting point (Tuesday evening)?")) return;
    resetDemo.mutate(undefined, {
      onSuccess: () =>
        toast({ title: "Demo reset", description: "Scenario: Tuesday evening", variant: "success" }),
      onError: () => toast({ title: "Could not reset the demo", variant: "error" }),
    });
  };

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-headline-lg text-on-surface">Try the demo</h2>
          <p className="text-caption text-on-surface-variant">
            Three steps through the full loop, in your own private sandbox. Other visitors are not affected.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-status-green-bg px-3 py-1.5 text-caption font-semibold text-status-green">
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            Scenario: {scenarioLabel(demoState?.scenario)}
          </span>
          {demoState?.lastResetAt ? (
            <span className="text-caption text-on-surface-variant">
              Last reset {formatDateTimeWib(demoState.lastResetAt)}
            </span>
          ) : null}
          <Button variant="outline" onClick={handleReset} disabled={resetDemo.isPending}>
            <RotateCcw className="h-4 w-4" aria-hidden />
            {resetDemo.isPending ? "Resetting…" : "Reset demo"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        {STEPS.map((step, i) => (
          <Link
            key={step.title}
            href={step.href}
            className="flex flex-col gap-2.5 rounded-xl bg-surface-container-lowest p-5 transition-transform hover:-translate-y-0.5"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary font-semibold text-primary-fixed">
              {i + 1}
            </span>
            <span className="text-headline-md text-on-surface">{step.title}</span>
            <span className="text-caption text-on-surface-variant">{step.body}</span>
            <span className="text-caption font-semibold text-primary-container">{step.go} →</span>
          </Link>
        ))}
      </div>
    </section>
  );
}

// The API stores the scenario name in Indonesian; the jury page is in English.
function scenarioLabel(scenario: string | undefined): string {
  if (!scenario || scenario === "Selasa malam") return "Tuesday evening";
  return scenario;
}
