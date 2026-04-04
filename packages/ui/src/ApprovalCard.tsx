"use client";

import React, { useState } from "react";

interface ApprovalAction {
  id: string;
  agentType: "listing" | "inventory" | "advertising" | "pricing" | "analytics" | "compliance" | "orchestrator";
  description: string;
  affectedAsins: string[];
  estimatedImpact: string;
  confidence: number;
  reasoning: string;
  priority: "critical" | "high" | "medium" | "low";
  createdAt: string;
}

export interface ApprovalCardProps {
  action: ApprovalAction;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

const AGENT_BORDER_COLORS: Record<string, string> = {
  listing: "border-l-blue-500",
  inventory: "border-l-emerald-500",
  advertising: "border-l-amber-500",
  pricing: "border-l-violet-500",
  analytics: "border-l-cyan-500",
  compliance: "border-l-gray-500",
  orchestrator: "border-l-pink-500",
};

function getRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function ApprovalCard({ action, onApprove, onReject }: ApprovalCardProps) {
  const [showReasoning, setShowReasoning] = useState(false);
  const borderColor = AGENT_BORDER_COLORS[action.agentType] || "border-l-slate-300";

  return (
    <div className={`bg-white rounded-2xl shadow-lg border-l-4 ${borderColor} p-6`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-500 capitalize font-body">
            {action.agentType}
          </span>
          <span className="text-xs text-slate-400">
            {Math.round(action.confidence * 100)}%
          </span>
        </div>
        <span data-testid="approval-time" className="text-xs text-slate-400 font-body">
          {getRelativeTime(action.createdAt)}
        </span>
      </div>

      {/* Description */}
      <p className="text-base text-slate-800 font-body mb-3">{action.description}</p>

      {/* ASINs */}
      <div className="flex flex-wrap gap-2 mb-3">
        {action.affectedAsins.map((asin) => (
          <span
            key={asin}
            className="inline-block px-2 py-1 bg-white border-2 border-dashed border-primary-pop/30 rounded-lg text-primary-pop font-bold text-sm"
          >
            {asin}
          </span>
        ))}
      </div>

      {/* Reasoning toggle */}
      <button
        onClick={() => setShowReasoning(!showReasoning)}
        className="text-sm text-primary-pop hover:underline font-body mb-3"
      >
        {showReasoning ? "Hide reasoning" : "Show reasoning"}
      </button>
      <div
        className={`overflow-hidden transition-all ${showReasoning ? "max-h-96 opacity-100" : "max-h-0 opacity-0"}`}
        style={{ visibility: showReasoning ? "visible" : "hidden" }}
      >
        <p className="text-sm text-slate-600 bg-slate-50 rounded-lg p-3 mb-3 font-body">
          {action.reasoning}
        </p>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 mt-2">
        <button
          onClick={() => onApprove(action.id)}
          className="px-4 py-2 bg-emerald-500 text-white font-whimsical font-bold rounded-xl shadow-[0_4px_0_rgb(21,128,61)] hover:translate-y-[2px] hover:shadow-[0_2px_0_rgb(21,128,61)] transition-all"
          aria-label="Approve"
        >
          Approve
        </button>
        <button
          onClick={() => onReject(action.id)}
          className="px-4 py-2 bg-white border-2 border-slate-200 text-slate-600 font-body rounded-xl hover:bg-slate-50 transition-all"
          aria-label="Reject"
        >
          Reject
        </button>
      </div>
    </div>
  );
}
