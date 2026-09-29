"use client";

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { formatCompactCurrency } from "@/lib/format";

interface Point {
  ts: string;
  equity: number;
}

export default function EquityCurveChart({ data, height = 280 }: { data: Point[]; height?: number }) {
  const positive = data.length > 1 ? data[data.length - 1].equity >= data[0].equity : true;
  const color = positive ? "#D8B36C" : "#E5555C";

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.35} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis
          dataKey="ts"
          tickFormatter={(v) => new Date(v).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
          stroke="rgba(255,255,255,0.15)"
          tick={{ fill: "#5D6674", fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          minTickGap={40}
        />
        <YAxis
          stroke="rgba(255,255,255,0.15)"
          tick={{ fill: "#5D6674", fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => formatCompactCurrency(v)}
          width={70}
          domain={["auto", "auto"]}
        />
        <Tooltip
          contentStyle={{
            background: "rgba(10,14,20,0.95)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 8,
            fontSize: 12,
          }}
          labelFormatter={(v) => new Date(v as string).toLocaleString()}
          formatter={(v) => [formatCompactCurrency(Number(v)), "Equity"]}
        />
        <Area type="monotone" dataKey="equity" stroke={color} strokeWidth={1.8} fill="url(#equityFill)" isAnimationActive />
      </AreaChart>
    </ResponsiveContainer>
  );
}
