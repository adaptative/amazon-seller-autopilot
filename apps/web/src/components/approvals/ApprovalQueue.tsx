"use client";

import React, { useEffect, useState, useCallback } from "react";
import type { ApprovalAction } from "@/lib/api";
import { approvalsApi } from "@/lib/api";

type AgentFilter = "all" | string;
type SortField = "priority" | "confidence" | "date";

const PRIORITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const AGENT_COLORS: Record<string, string> = {
  listing: "border-l-blue-500",
  pricing: "border-l-violet-500",
  inventory: "border-l-emerald-500",
  advertising: "border-l-amber-500",
};

function sortActions(actions: ApprovalAction[], sortBy: SortField): ApprovalAction[] {
  return [...actions].sort((a, b) => {
    if (sortBy === "priority") {
      return (PRIORITY_ORDER[a.priority] ?? 9) - (PRIORITY_ORDER[b.priority] ?? 9);
    }
    if (sortBy === "confidence") {
      return b.confidenceScore - a.confidenceScore;
    }
    // date — newest first
    return (b.createdAt ?? "").localeCompare(a.createdAt ?? "");
  });
}

export function ApprovalQueue() {
  const [actions, setActions] = useState<ApprovalAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [agentFilter, setAgentFilter] = useState<AgentFilter>("all");
  const [sortBy, setSortBy] = useState<SortField>("priority");
  const [bulkThreshold, setBulkThreshold] = useState(0.85);

  const fetchActions = useCallback(async () => {
    try {
      const data = await approvalsApi.listPending();
      setActions(data.actions);
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchActions();
  }, [fetchActions]);

  const handleApprove = async (id: string) => {
    await approvalsApi.approve(id);
    setActions((prev) => prev.filter((a) => a.id !== id));
  };

  const handleReject = async (id: string) => {
    await approvalsApi.reject(id);
    setActions((prev) => prev.filter((a) => a.id !== id));
  };

  const handleBulkApprove = async () => {
    const result = await approvalsApi.bulkApprove(bulkThreshold);
    if (result.approved_count > 0) {
      await fetchActions();
    }
  };

  // Derive agent types for filter
  const agentTypes = [...new Set(actions.map((a) => a.agentType))];

  // Apply filter + sort
  const filtered = agentFilter === "all" ? actions : actions.filter((a) => a.agentType === agentFilter);
  const sorted = sortActions(filtered, sortBy);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-pop" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-display font-bold text-slate-800">
            Approval Queue
          </h2>
          <p className="text-sm font-body text-slate-500 mt-1">
            {actions.length} action{actions.length !== 1 ? "s" : ""} awaiting review
          </p>
        </div>

        {/* Bulk approve */}
        <div className="flex items-center gap-3">
          <label className="text-sm font-body text-slate-600">
            Min confidence:
            <input
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={bulkThreshold}
              onChange={(e) => setBulkThreshold(Number(e.target.value))}
              className="ml-2 w-16 px-2 py-1 border rounded-lg text-sm"
              data-testid="bulk-threshold"
            />
          </label>
          <button
            onClick={handleBulkApprove}
            className="px-4 py-2 bg-primary-pop text-white font-body font-medium rounded-xl hover:bg-primary-pop/90 transition-colors"
            data-testid="bulk-approve-btn"
          >
            Bulk Approve
          </button>
        </div>
      </div>

      {/* Filters & Sort */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-body text-slate-500">Agent:</span>
          <select
            value={agentFilter}
            onChange={(e) => setAgentFilter(e.target.value)}
            className="px-3 py-1.5 border rounded-lg text-sm font-body"
            data-testid="agent-filter"
          >
            <option value="all">All agents</option>
            {agentTypes.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-body text-slate-500">Sort:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortField)}
            className="px-3 py-1.5 border rounded-lg text-sm font-body"
            data-testid="sort-select"
          >
            <option value="priority">Priority</option>
            <option value="confidence">Confidence</option>
            <option value="date">Newest</option>
          </select>
        </div>
      </div>

      {/* Empty state */}
      {sorted.length === 0 ? (
        <div className="text-center py-16" data-testid="empty-state">
          <div className="text-5xl mb-4">&#127881;</div>
          <h3 className="text-xl font-display font-bold text-slate-700 mb-2">
            All caught up!
          </h3>
          <p className="text-sm font-body text-slate-500 max-w-md mx-auto">
            No actions awaiting your review. Your AI agents are working hard
            &mdash; new proposals will appear here when they&apos;re ready.
          </p>
        </div>
      ) : (
        <div className="space-y-4" data-testid="approval-list">
          {sorted.map((action) => {
            const borderColor = AGENT_COLORS[action.agentType] || "border-l-slate-300";
            const confidencePct = Math.round(action.confidenceScore * 100);

            return (
              <div
                key={action.id}
                className={`bg-white rounded-2xl shadow-lg border-l-4 ${borderColor} p-6`}
                data-testid="approval-card"
              >
                {/* Card header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-slate-500 capitalize font-body">
                      {action.agentType}
                    </span>
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-xs font-body font-medium ${
                        action.priority === "critical"
                          ? "bg-rose-100 text-rose-700"
                          : action.priority === "high"
                          ? "bg-amber-100 text-amber-700"
                          : action.priority === "medium"
                          ? "bg-sky-100 text-sky-700"
                          : "bg-slate-100 text-slate-600"
                      }`}
                      data-testid="priority-badge"
                    >
                      {action.priority}
                    </span>
                    <span className="text-xs text-slate-400 tabular-nums">
                      {confidencePct}% confidence
                    </span>
                  </div>
                  {action.expiresAt && (
                    <span className="text-xs text-amber-500 font-body" data-testid="expires-badge">
                      Expires {new Date(action.expiresAt).toLocaleString()}
                    </span>
                  )}
                </div>

                {/* Action type & ASIN */}
                <p className="text-base text-slate-800 font-body mb-2">
                  {action.actionType.replace(/_/g, " ")}
                </p>
                {action.targetAsin && (
                  <span className="inline-block px-2 py-1 bg-white border-2 border-dashed border-primary-pop/30 rounded-lg text-primary-pop font-bold text-sm mb-3">
                    {action.targetAsin}
                  </span>
                )}

                {/* Reasoning */}
                {action.reasoning && (
                  <p className="text-sm text-slate-600 bg-slate-50 rounded-lg p-3 mb-3 font-body">
                    {action.reasoning}
                  </p>
                )}

                {/* Actions */}
                <div className="flex items-center gap-3 mt-2">
                  <button
                    onClick={() => handleApprove(action.id)}
                    className="px-4 py-2 bg-emerald-500 text-white font-body font-bold rounded-xl shadow-[0_4px_0_rgb(21,128,61)] hover:translate-y-[2px] hover:shadow-[0_2px_0_rgb(21,128,61)] transition-all"
                    aria-label="Approve"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => handleReject(action.id)}
                    className="px-4 py-2 bg-white border-2 border-slate-200 text-slate-600 font-body rounded-xl hover:bg-slate-50 transition-all"
                    aria-label="Reject"
                  >
                    Reject
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
