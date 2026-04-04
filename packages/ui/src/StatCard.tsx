"use client";

import React from "react";

interface TrendData {
  value: number;
  direction: "up" | "down";
}

export interface StatCardProps {
  label: string;
  value: string;
  trend?: TrendData;
  loading?: boolean;
}

export function StatCard({ label, value, trend, loading }: StatCardProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-lg p-6" data-testid="stat-skeleton">
        <div className="animate-pulse space-y-3">
          <div className="h-3 w-24 bg-slate-200 rounded" />
          <div className="h-10 w-32 bg-slate-200 rounded" />
          <div className="h-4 w-16 bg-slate-200 rounded" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg p-6">
      <p className="text-xs uppercase tracking-wider text-slate-400 font-body">
        {label.toUpperCase()}
      </p>
      <p className="font-whimsical text-4xl font-bold text-slate-900 mt-1">
        {value}
      </p>
      {trend && (
        <span
          data-testid="trend-indicator"
          className={`inline-flex items-center text-sm font-medium mt-2 ${
            trend.direction === "up"
              ? "text-emerald-500"
              : "text-rose-500"
          }`}
        >
          {trend.direction === "up" ? "↑" : "↓"} {trend.value}%
        </span>
      )}
    </div>
  );
}
