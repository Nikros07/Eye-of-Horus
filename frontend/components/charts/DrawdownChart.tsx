"use client";

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

interface Point {
  ts: string;
  equity: number;
}

export default function DrawdownChart({ data, height = 140 }: { data: Point[]; height?: number }) {
  let peak = data[0]?.equity ?? 0;
  const drawdown = data.map((p) => {
    peak = Math.max(peak, p.equity);
    const dd = peak > 0 ? (p.equity - peak) / peak : 0;
    return { ts: p.ts, dd: dd * 100 };
  });

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={drawdown} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="ddFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#E5555C" stopOpacity={0} />
            <stop offset="100%" stopColor="#E5555C" stopOpacity={0.4} />
          </linearGradient>
        </defs>
        <XAxis dataKey="ts" hide />
        <YAxis
          stroke="rgba(255,255,255,0.15)"
          tick={{ fill: "#5D6674", fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `${v.toFixed(0)}%`}
          width={40}
        />
        <Tooltip
          contentStyle={{
            background: "rgba(10,14,20,0.95)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(v) => [`${Number(v).toFixed(2)}%`, "Drawdown"]}
        />
        <Area type="monotone" dataKey="dd" stroke="#E5555C" strokeWidth={1.5} fill="url(#ddFill)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
