import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgentStatusBadge } from "../AgentStatusBadge";

describe("AgentStatusBadge", () => {
  it("renders agent name", () => {
    render(<AgentStatusBadge agent="listing" status="active" />);
    expect(screen.getByText(/listing/i)).toBeInTheDocument();
  });

  it("shows status dot with agent-specific color", () => {
    render(<AgentStatusBadge agent="listing" status="active" />);
    const dot = screen.getByTestId("agent-dot");
    expect(dot).toBeInTheDocument();
    expect(dot.className).toMatch(/blue|primary/);
  });

  it("pulses when active", () => {
    render(<AgentStatusBadge agent="listing" status="active" />);
    expect(screen.getByTestId("agent-dot").className).toMatch(/pulse|animate/);
  });

  it("does NOT pulse when idle", () => {
    render(<AgentStatusBadge agent="inventory" status="idle" />);
    expect(screen.getByTestId("agent-dot").className).not.toMatch(/pulse/);
  });

  it("shows red dot for error status", () => {
    render(<AgentStatusBadge agent="orchestrator" status="error" />);
    expect(screen.getByTestId("agent-dot").className).toMatch(/rose|red/);
  });

  it("shows amber dot for awaiting_approval", () => {
    render(<AgentStatusBadge agent="pricing" status="awaiting_approval" />);
    expect(screen.getByTestId("agent-dot").className).toMatch(/amber|yellow/);
  });

  it("renders correct color for each agent type", () => {
    const agents = [
      { agent: "listing", color: /blue|primary/ },
      { agent: "inventory", color: /emerald|green/ },
      { agent: "advertising", color: /amber|yellow/ },
      { agent: "pricing", color: /violet|purple/ },
      { agent: "analytics", color: /cyan|teal/ },
      { agent: "compliance", color: /gray|slate/ },
      { agent: "orchestrator", color: /pink|accent/ },
    ];
    for (const { agent, color } of agents) {
      const { unmount } = render(
        <AgentStatusBadge agent={agent as any} status="idle" />
      );
      const dot = screen.getByTestId("agent-dot");
      expect(dot.className).toMatch(color);
      unmount();
    }
  });
});
