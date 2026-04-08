"use client";

import React, { useEffect, useState } from "react";
import {
  pricingApi,
  type PricingStats,
  type PricedProduct,
  type BuyBoxHistoryPoint,
  type CompetitorPoint,
} from "@/lib/api";
import { BuyBoxChart } from "./BuyBoxChart";
import { CompetitorMap } from "./CompetitorMap";
import { PriceTable } from "./PriceTable";

function TrendBadge({
  value,
  testId,
  suffix = "%",
}: {
  value: number;
  testId: string;
  suffix?: string;
}) {
  const isPositive = value > 0;
  const colorClass = isPositive ? "text-emerald-600" : "text-amber-600";
  const arrow = isPositive ? "\u2191" : "\u2193";
  return (
    <span data-testid={testId} className={`text-sm font-body font-medium ${colorClass}`}>
      {arrow} {Math.abs(value)}
      {suffix}
    </span>
  );
}

export function PricingDashboard() {
  const [stats, setStats] = useState<PricingStats | null>(null);
  const [products, setProducts] = useState<PricedProduct[]>([]);
  const [total, setTotal] = useState(0);
  const [buyBoxHistory, setBuyBoxHistory] = useState<BuyBoxHistoryPoint[]>([]);
  const [competitorData, setCompetitorData] = useState<CompetitorPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      pricingApi.getStats(),
      pricingApi.getProducts(),
      pricingApi.getBuyBoxHistory(30),
      pricingApi.getCompetitorMap(),
    ])
      .then(([s, p, h, c]) => {
        setStats(s);
        setProducts(p.items);
        setTotal(p.total);
        setBuyBoxHistory(h);
        setCompetitorData(c);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleReprice = (asin: string) => {
    pricingApi.reprice(asin);
  };

  if (loading || !stats) {
    return (
      <div className="animate-pulse p-8">
        <div className="h-8 bg-slate-200 rounded w-56 mb-6" />
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-28 bg-slate-100 rounded-2xl" />
          ))}
        </div>
        <div className="grid grid-cols-2 gap-6 mb-6">
          <div className="h-72 bg-slate-100 rounded-2xl" />
          <div className="h-72 bg-slate-100 rounded-2xl" />
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-display font-bold text-slate-800">
            Pricing Dashboard
          </h1>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-violet-50 rounded-full">
            <span className="w-2.5 h-2.5 rounded-full bg-violet-500 animate-pulse" />
            <span className="text-xs font-medium text-violet-700">
              Pricing Agent
            </span>
            <span className="text-xs text-violet-500">Active</span>
          </div>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {/* Buy Box Win Rate */}
        <div className="bg-white rounded-2xl shadow-lg p-5">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-body">
              Buy Box Win Rate
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-display font-bold text-slate-800">
              {stats.buyBoxWinRate}%
            </span>
            <TrendBadge value={stats.buyBoxTrend} testId="trend-buy-box" />
          </div>
        </div>

        {/* Avg Margin */}
        <div className="bg-white rounded-2xl shadow-lg p-5">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-body">
              Avg Margin
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-display font-bold text-slate-800">
              {stats.avgMargin}%
            </span>
            <TrendBadge value={stats.marginTrend} testId="trend-margin" />
          </div>
        </div>

        {/* Price Changes Today */}
        <div className="bg-white rounded-2xl shadow-lg p-5">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-body">
              Price Changes Today
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-display font-bold text-slate-800">
              {stats.priceChangesToday}
            </span>
            <TrendBadge value={stats.changesTrend} testId="trend-changes" suffix="" />
          </div>
        </div>

        {/* Revenue Impact */}
        <div className="bg-white rounded-2xl shadow-lg p-5">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-body">
              Revenue Impact
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-display font-bold text-slate-800">
              +${stats.revenueImpact.toLocaleString()}
            </span>
            <span className="text-xs text-slate-400 font-body">last 7 days</span>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        <BuyBoxChart data={buyBoxHistory} currentRate={stats.buyBoxWinRate} />
        <CompetitorMap data={competitorData} />
      </div>

      {/* Price Table */}
      <PriceTable products={products} total={total} onReprice={handleReprice} />
    </div>
  );
}
