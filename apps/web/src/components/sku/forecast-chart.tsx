"use client";

import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ForecastPoint } from "@/lib/api/types";
import { formatDateWib } from "@/lib/format";

interface Row {
  date: string;
  label: string;
  posSales: number;
  forecastA: number | null;
  forecastB: number;
  bandBase: number;
  bandRange: number;
}

function buildRows(data: ForecastPoint[]): Row[] {
  return data.map((p) => {
    const lower = p.forecastBLower ?? p.forecastB;
    const upper = p.forecastBUpper ?? p.forecastB;
    return {
      date: p.date,
      label: formatDateWib(p.date),
      posSales: p.posSales,
      forecastA: p.forecastA,
      forecastB: p.forecastB,
      bandBase: Math.max(0, lower),
      bandRange: Math.max(0, upper - lower),
    };
  });
}

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ payload: Row }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-lg border border-surface-container bg-surface-container-lowest px-3 py-2 text-caption shadow-md">
      <p className="mb-1 font-medium text-on-surface">{label}</p>
      <p className="text-on-surface-variant">POS sales: {row.posSales}</p>
      <p className="text-outline">Forecast A: {row.forecastA ?? "—"}</p>
      <p className="font-medium text-primary">Forecast B: {row.forecastB}</p>
    </div>
  );
}

export default function ForecastChart({ data }: { data: ForecastPoint[] }) {
  const rows = buildRows(data);
  const stockout = data.filter((p) => p.isStockout);
  const x1 = stockout.length ? formatDateWib(stockout[0].date) : undefined;
  const x2 = stockout.length
    ? formatDateWib(stockout[stockout.length - 1].date)
    : undefined;

  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 10, right: 10, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="#eff4ff" vertical={false} />
          <XAxis
            dataKey="label"
            axisLine={false}
            tickLine={false}
            interval={Math.max(0, Math.floor(rows.length / 6) - 1)}
            tick={{ fill: "#6e7977", fontSize: 11 }}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#6e7977", fontSize: 11 }}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: "#eff4ff" }} />
          {x1 && x2 ? (
            <ReferenceArea
              x1={x1}
              x2={x2}
              fill="#ba1a1a"
              fillOpacity={0.07}
              stroke="#ba1a1a"
              strokeOpacity={0.3}
              strokeDasharray="4 3"
            />
          ) : null}
          <Area
            dataKey="bandBase"
            stackId="band"
            stroke="none"
            fill="transparent"
            isAnimationActive={false}
          />
          <Area
            dataKey="bandRange"
            stackId="band"
            stroke="none"
            fill="#0f766e"
            fillOpacity={0.14}
            isAnimationActive={false}
          />
          <Bar dataKey="posSales" fill="#dce9ff" radius={[2, 2, 0, 0]} barSize={14} />
          <Line
            dataKey="forecastA"
            stroke="#6e7977"
            strokeDasharray="5 4"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            dataKey="forecastB"
            stroke="#0f766e"
            strokeWidth={3}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
