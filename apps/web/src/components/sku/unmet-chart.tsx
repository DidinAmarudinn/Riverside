"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { UnmetPoint } from "@/lib/api/types";
import { formatDateWib } from "@/lib/format";

export default function UnmetChart({ data }: { data: UnmetPoint[] }) {
  const rows = data.map((p) => ({
    label: formatDateWib(p.date),
    count: p.count,
  }));

  return (
    <div className="h-[180px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 10, right: 10, bottom: 0, left: -22 }}>
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
            allowDecimals={false}
          />
          <Tooltip
            cursor={{ fill: "#eff4ff" }}
            contentStyle={{
              borderRadius: 8,
              border: "1px solid #e5eeff",
              fontSize: 12,
            }}
          />
          <Bar dataKey="count" radius={[3, 3, 0, 0]}>
            {rows.map((row, i) => (
              <Cell key={i} fill={row.count >= 6 ? "#fea619" : "#cbd5e1"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
