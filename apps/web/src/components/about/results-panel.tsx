"use client";

import { useEffect, useState } from "react";
import { CardSkeleton, ErrorState } from "@/components/common/states";

/** One row of public/results.json, copied from docs/results.md (make experiment). */
interface ResultGroup {
  key: string;
  title: string;
  detail: string;
  metric: "WAPE" | "Bias" | "Accuracy";
  labelA?: string;
  labelB?: string;
  a: number;
  b: number;
  verdict: string;
}

interface Results {
  source: string;
  groups: ResultGroup[];
  note?: string;
}

function formatMetric(metric: ResultGroup["metric"], value: number): string {
  const pct = (value * 100).toFixed(1);
  return metric === "Bias" && value > 0 ? `+${pct}%` : `${pct}%`;
}

/** B wins when its error is smaller (WAPE, |bias|) or its accuracy higher; the winner gets the lime tile. */
function bWins(g: ResultGroup): boolean {
  if (g.metric === "Accuracy") return g.b > g.a;
  return Math.abs(g.b) < Math.abs(g.a) - 1e-9;
}

function Group({ group }: { group: ResultGroup }) {
  const win = bWins(group);
  return (
    <div className="flex flex-col gap-3 rounded-xl bg-surface-container-lowest p-5">
      <div>
        <span className="block text-headline-md text-on-surface">{group.title}</span>
        <span className="text-caption text-on-surface-variant">{group.detail}</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-surface-container-low p-3">
          <span className="block text-caption text-on-surface-variant">{group.labelA ?? `${group.metric} · A`}</span>
          <span className="text-[28px] font-medium tracking-[-0.03em] tabular-nums text-on-surface">
            {formatMetric(group.metric, group.a)}
          </span>
        </div>
        <div className={win ? "rounded-lg bg-primary-fixed p-3 text-on-primary-fixed" : "rounded-lg bg-surface-container-low p-3"}>
          <span className="block text-caption">{group.labelB ?? `${group.metric} · B`}</span>
          <span className="text-[28px] font-medium tracking-[-0.03em] tabular-nums text-on-surface">
            {formatMetric(group.metric, group.b)}
          </span>
        </div>
      </div>
      <p className="text-caption leading-relaxed text-on-surface-variant">
        {group.verdict}
      </p>
    </div>
  );
}

export function ResultsPanel() {
  const [results, setResults] = useState<Results | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    fetch("/results.json")
      .then((res) => {
        if (!res.ok) throw new Error("failed");
        return res.json();
      })
      .then((json: Results) => {
        if (active) setResults(json);
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return (
      <ErrorState
        title="Experiment results are not available"
        description="public/results.json is missing or invalid."
      />
    );
  }

  if (!results) return <CardSkeleton rows={3} />;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {results.groups.map((group) => (
          <Group key={group.key} group={group} />
        ))}
      </div>
      {results.note ? (
        <p className="text-caption text-on-surface-variant">{results.note}</p>
      ) : null}
      <p className="text-caption text-on-surface-variant">
        Full report with every table:{" "}
        <code className="rounded bg-surface-container-low px-1 py-0.5 font-label-mono">
          docs/results.md
        </code>
      </p>
    </div>
  );
}
