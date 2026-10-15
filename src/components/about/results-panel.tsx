"use client";

import { useEffect, useState } from "react";
import { CardSkeleton, ErrorState } from "@/components/common/states";

interface Results {
  wapeA: number;
  wapeB: number;
  stockoutDaysA: number;
  stockoutDaysB: number;
  overstockUnitsA: number;
  overstockUnitsB: number;
  horizonDays: number;
  note?: string;
}

function Stat({
  label,
  a,
  b,
  format = (v: number) => String(v),
}: {
  label: string;
  a: number;
  b: number;
  format?: (v: number) => string;
}) {
  return (
    <div className="rounded-xl bg-surface-container-low p-4">
      <span className="font-microcopy-caps uppercase tracking-wider text-on-surface-variant">
        {label}
      </span>
      <div className="mt-2 grid grid-cols-2 gap-2">
        <div>
          <span className="block text-caption text-outline">Forecast A</span>
          <span className="text-headline-md text-on-surface">
            {format(a)}
          </span>
        </div>
        <div>
          <span className="block text-caption text-primary">Forecast B</span>
          <span className="text-headline-md text-primary-container">
            {format(b)}
          </span>
        </div>
      </div>
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
        title="Hasil eksperimen tidak tersedia"
        description="File public/results.json tidak ditemukan atau tidak valid."
      />
    );
  }

  if (!results) return <CardSkeleton rows={3} />;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat
          label={`WAPE (${results.horizonDays}d)`}
          a={results.wapeA}
          b={results.wapeB}
          format={(v) => `${Math.round(v * 100)}%`}
        />
        <Stat
          label="Stockout days"
          a={results.stockoutDaysA}
          b={results.stockoutDaysB}
        />
        <Stat
          label="Overstock units"
          a={results.overstockUnitsA}
          b={results.overstockUnitsB}
        />
      </div>
      {results.note ? (
        <p className="text-caption text-on-surface-variant">{results.note}</p>
      ) : null}
    </div>
  );
}
