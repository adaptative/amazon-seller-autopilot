"use client";

import React, { useEffect, useState, useCallback } from "react";
import { dashboardApi } from "@/lib/api";
import type {
  DashboardData,
  AgentStatus,
  DashboardPendingApproval,
  ActivityItem,
} from "@/lib/api";

/* ── Agent dot colour map ──────────────────────────────────────── */
const AGENT_DOT: Record<string, string> = {
  listing: "bg-blue-500",
  pricing: "bg-violet-500",
  advertising: "bg-amber-500",
  inventory: "bg-emerald-500",
  analytics: "bg-cyan-500",
  compliance: "bg-slate-400",
  orchestrator: "bg-pink-500",
};

const AGENT_BORDER: Record<string, string> = {
  listing: "border-l-blue-500",
  pricing: "border-l-violet-500",
  advertising: "border-l-amber-500",
  inventory: "border-l-emerald-500",
  analytics: "border-l-cyan-500",
  compliance: "border-l-slate-400",
  orchestrator: "border-l-pink-500",
};

const AGENT_LABELS: Record<string, string> = {
  listing: "Listing Agent",
  pricing: "Pricing Agent",
  advertising: "Advertising Agent",
  inventory: "Inventory Agent",
  analytics: "Analytics Agent",
  compliance: "Compliance Agent",
  orchestrator: "Orchestrator",
};

/* ── Time-of-day greeting ──────────────────────────────────────── */
function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

/* ── Trend Badge ──────────────────────────────────────────────── */
function TrendBadge({ value, invertColor }: { value: number; invertColor?: boolean }) {
  const positive = invertColor ? value < 0 : value > 0;
  const cls = positive ? "text-emerald-600" : "text-amber-600";
  const arrow = value > 0 ? "\u2191" : "\u2193";
  return (
    <span className={`text-sm font-body font-medium ${cls}`}>
      {arrow} {Math.abs(value)}%
    </span>
  );
}

/* ── Mini Sparkline (pure SVG) ─────────────────────────────────── */
function Sparkline() {
  // Decorative mini sparkline
  const points = [8, 6, 9, 5, 7, 10, 8, 12, 9, 14];
  const max = Math.max(...points);
  const step = 48 / (points.length - 1);
  const path = points
    .map((v, i) => `${i === 0 ? "M" : "L"}${i * step},${24 - (v / max) * 20}`)
    .join(" ");

  return (
    <svg width={48} height={24} className="text-blue-500">
      <path d={path} fill="none" stroke="currentColor" strokeWidth={1.5} />
    </svg>
  );
}

/* ── Main Dashboard ────────────────────────────────────────────── */
interface DashboardProps {
  userName?: string;
}

export function Dashboard({ userName = "there" }: DashboardProps) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [notifCount, setNotifCount] = useState(0);

  const fetchData = useCallback(async () => {
    try {
      const result = await dashboardApi.getData();
      setData(result);
      setNotifCount(result.notificationCount ?? 0);
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading || !data) {
    return (
      <div className="animate-pulse p-8">
        <div className="h-8 bg-slate-200 rounded w-56 mb-6" />
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-28 bg-slate-100 rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  const { stats, agents, pendingApprovals, recentActivity } = data;

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#f0f9ff] to-white">
      {/* Top Bar */}
      <header className="bg-white border-b border-slate-100 h-16 flex items-center justify-between px-6">
        <div>
          <h1 className="text-xl font-display font-bold text-slate-800">
            {getGreeting()}, {userName}!
          </h1>
          <p className="text-sm font-body text-slate-500">
            Your AI crew handled {stats.ordersToday} actions while you were away
          </p>
        </div>

        {/* Search */}
        <div className="hidden md:flex">
          <input
            type="text"
            placeholder="Search anything... \u2318K"
            className="w-96 px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm font-body focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            readOnly
          />
        </div>

        {/* Notifications */}
        <div className="flex items-center gap-3">
          <button className="relative p-2" aria-label="Notifications">
            <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            {notifCount > 0 && (
              <span
                data-testid="notification-badge"
                className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center"
              >
                {notifCount}
              </span>
            )}
          </button>
          <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-xs text-white font-bold">
            {userName.charAt(0).toUpperCase()}
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="p-6 space-y-6">
        {/* ROW 1: Stat Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Revenue */}
          <div className="bg-white rounded-2xl shadow-lg p-5">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-body">
              Total Revenue
            </span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-4xl font-display font-bold text-slate-800">
                ${stats.totalRevenue.toLocaleString()}
              </span>
              <Sparkline />
            </div>
            <TrendBadge value={stats.revenueTrend} />
          </div>

          {/* Orders Today */}
          <div className="bg-white rounded-2xl shadow-lg p-5">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-body">
              Orders Today
            </span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-4xl font-display font-bold text-slate-800">
                {stats.ordersToday}
              </span>
              <Sparkline />
            </div>
            <TrendBadge value={stats.ordersTrend} />
          </div>

          {/* Buy Box Win Rate */}
          <div className="bg-white rounded-2xl shadow-lg p-5">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-body">
              Buy Box Win Rate
            </span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-4xl font-display font-bold text-slate-800">
                {stats.buyBoxWinRate}%
              </span>
              <Sparkline />
            </div>
            <TrendBadge value={stats.buyBoxTrend} />
          </div>

          {/* ACoS */}
          <div className="bg-white rounded-2xl shadow-lg p-5">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-body">
              ACoS
            </span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-4xl font-display font-bold text-slate-800">
                {stats.acos}%
              </span>
              <Sparkline />
            </div>
            <TrendBadge value={stats.acosTrend} invertColor />
          </div>
        </div>

        {/* ROW 2: Agent Activity + Pending Approvals */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Agent Activity */}
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <h2 className="text-lg font-display font-bold text-slate-800 mb-4">
              Agent Activity
            </h2>
            <div className="space-y-3">
              {agents.map((agent: AgentStatus) => (
                <div key={agent.type} className="flex items-center gap-3">
                  <span
                    data-testid={`agent-dot-${agent.type}`}
                    className={`w-3 h-3 rounded-full flex-shrink-0 ${
                      AGENT_DOT[agent.type] || "bg-slate-400"
                    } ${agent.status === "active" ? "animate-pulse" : ""}`}
                  />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-body font-semibold text-slate-700">
                      {AGENT_LABELS[agent.type] || agent.type}
                    </span>
                    <p className="text-xs text-slate-400 font-body truncate">
                      {agent.lastAction}
                    </p>
                  </div>
                  <span className="text-xs text-slate-400 font-body flex-shrink-0">
                    {agent.lastActionAt}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Pending Approvals */}
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <h2 className="text-lg font-display font-bold text-slate-800">
                Pending Approvals
              </h2>
              <span
                data-testid="pending-count"
                className="inline-flex items-center justify-center w-6 h-6 text-xs font-bold text-white bg-amber-500 rounded-full"
              >
                {pendingApprovals.length}
              </span>
            </div>
            <div className="space-y-3">
              {pendingApprovals.map((item: DashboardPendingApproval) => (
                <div
                  key={item.id}
                  className={`border-l-4 ${
                    AGENT_BORDER[item.agentType] || "border-l-slate-300"
                  } bg-slate-50 rounded-xl p-3`}
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-body text-slate-700">
                      {item.description}
                    </p>
                    <span className="text-xs text-slate-400 tabular-nums">
                      {Math.round(item.confidence * 100)}%
                    </span>
                  </div>
                  <span className="text-xs text-slate-400 font-body">
                    {item.createdAt}
                  </span>
                </div>
              ))}
              {pendingApprovals.length > 0 && (
                <a
                  href="/approvals"
                  className="block text-sm text-blue-500 font-body hover:underline mt-2"
                >
                  View all approvals &rarr;
                </a>
              )}
            </div>
          </div>
        </div>

        {/* ROW 3: Activity Feed */}
        <div className="bg-white rounded-2xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-display font-bold text-slate-800">
              Recent Activity
            </h2>
            <div className="flex items-center gap-1.5" data-testid="live-indicator">
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              <span className="text-xs font-body font-medium text-emerald-600">
                Live
              </span>
            </div>
          </div>
          <div className="space-y-3">
            {recentActivity.map((event: ActivityItem) => (
              <div key={event.id} className="flex items-center gap-3">
                <span className="text-xs text-slate-400 font-body tabular-nums w-16 flex-shrink-0">
                  {event.time}
                </span>
                <span
                  className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                    AGENT_DOT[event.agentType] || "bg-slate-400"
                  }`}
                />
                <span className="text-sm font-body text-slate-600">
                  {AGENT_LABELS[event.agentType] || event.agentType}
                </span>
                <span className="text-sm font-body text-slate-500">
                  {event.action}
                </span>
                {event.asin && (
                  <span className="inline-block px-2 py-0.5 bg-white border-2 border-dashed border-blue-500/30 rounded-lg text-blue-500 font-bold text-xs">
                    {event.asin}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
