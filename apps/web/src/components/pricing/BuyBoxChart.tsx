"use client";

import React from "react";
import type { BuyBoxHistoryPoint } from "@/lib/api";

export interface BuyBoxChartProps {
  data: BuyBoxHistoryPoint[];
  currentRate: number;
  targetRate?: number;
}

export function BuyBoxChart({ data, currentRate, targetRate = 85 }: BuyBoxChartProps) {
  // SVG-based area chart for Buy Box win rate
  const width = 500;
  const height = 200;
  const padding = { top: 20, right: 40, bottom: 30, left: 40 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const points = data.length > 0 ? data : generateSampleData();

  const xScale = (i: number) => padding.left + (i / Math.max(points.length - 1, 1)) * chartW;
  const yScale = (v: number) => padding.top + chartH - (v / 100) * chartH;

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xScale(i)} ${yScale(p.winRate)}`)
    .join(" ");

  const areaPath =
    linePath +
    ` L ${xScale(points.length - 1)} ${yScale(0)} L ${xScale(0)} ${yScale(0)} Z`;

  const targetY = yScale(targetRate);

  return (
    <div className="bg-white rounded-2xl shadow-lg p-6" data-testid="buybox-chart">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-display font-bold text-slate-800">
          Buy Box Win Rate (30 Days)
        </h3>
        <span className="px-2.5 py-1 bg-blue-50 text-blue-700 text-sm font-bold rounded-full">
          {currentRate}%
        </span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
        {/* Grid lines */}
        {[0, 25, 50, 75, 100].map((v) => (
          <g key={v}>
            <line
              x1={padding.left}
              y1={yScale(v)}
              x2={width - padding.right}
              y2={yScale(v)}
              stroke="#f1f5f9"
              strokeWidth={1}
            />
            <text
              x={padding.left - 8}
              y={yScale(v) + 4}
              textAnchor="end"
              className="text-[10px] fill-slate-400"
            >
              {v}%
            </text>
          </g>
        ))}

        {/* Target line */}
        <line
          x1={padding.left}
          y1={targetY}
          x2={width - padding.right}
          y2={targetY}
          stroke="#94a3b8"
          strokeWidth={1}
          strokeDasharray="4 4"
        />
        <text
          x={width - padding.right + 4}
          y={targetY + 4}
          className="text-[10px] fill-slate-400"
        >
          Target
        </text>

        {/* Area fill */}
        <path d={areaPath} fill="url(#buybox-gradient)" />

        {/* Line */}
        <path d={linePath} fill="none" stroke="#3b82f6" strokeWidth={2} />

        {/* Gradient definition */}
        <defs>
          <linearGradient id="buybox-gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.2} />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}

function generateSampleData(): BuyBoxHistoryPoint[] {
  const data: BuyBoxHistoryPoint[] = [];
  const now = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    data.push({
      date: d.toISOString().split("T")[0],
      winRate: 80 + Math.random() * 15,
    });
  }
  return data;
}
