"use client";

import React from "react";

type AgentType =
  | "listing"
  | "inventory"
  | "advertising"
  | "pricing"
  | "analytics"
  | "compliance"
  | "orchestrator";

type AgentStatus = "active" | "idle" | "error" | "awaiting_approval";

export interface AgentStatusBadgeProps {
  agent: AgentType;
  status: AgentStatus;
}

const AGENT_COLORS: Record<AgentType, string> = {
  listing: "bg-blue-500",
  inventory: "bg-emerald-500",
  advertising: "bg-amber-500",
  pricing: "bg-violet-500",
  analytics: "bg-cyan-500",
  compliance: "bg-gray-500",
  orchestrator: "bg-pink-500",
};

function getStatusDotClass(agent: AgentType, status: AgentStatus): string {
  if (status === "error") return "bg-rose-500";
  if (status === "awaiting_approval") return "bg-amber-400";
  return AGENT_COLORS[agent];
}

export function AgentStatusBadge({ agent, status }: AgentStatusBadgeProps) {
  const dotColor = getStatusDotClass(agent, status);
  const isPulsing = status === "active";

  return (
    <div className="inline-flex items-center gap-2 px-3 py-1.5">
      <span
        data-testid="agent-dot"
        className={`w-3 h-3 rounded-full ${dotColor} ${isPulsing ? "animate-pulse" : ""}`}
      />
      <span className="text-sm font-medium text-slate-700 capitalize font-body">
        {agent}
      </span>
    </div>
  );
}
