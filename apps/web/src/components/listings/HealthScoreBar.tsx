"use client";

import React from "react";

export interface HealthScoreBarProps {
  score: number;
  asin: string;
}

function getColorClass(score: number): string {
  if (score >= 70) return "bg-emerald-500";
  if (score >= 40) return "bg-amber-500";
  return "bg-rose-500";
}

export function HealthScoreBar({ score, asin }: HealthScoreBarProps) {
  const colorClass = getColorClass(score);
  const clampedScore = Math.max(0, Math.min(100, score));

  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-2 bg-slate-200 rounded-full overflow-hidden">
        <div
          data-testid={`health-bar-${asin}`}
          className={`h-full rounded-full ${colorClass}`}
          style={{ width: `${clampedScore}%` }}
        />
      </div>
      <span className="text-sm font-body tabular-nums text-slate-700">{score}</span>
    </div>
  );
}
