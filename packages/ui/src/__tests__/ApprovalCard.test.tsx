import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApprovalCard } from "../ApprovalCard";

const mockAction = {
  id: "action-1",
  agentType: "pricing" as const,
  description: "Reduce price on B08XYZ to $24.99 to match competitor",
  affectedAsins: ["B08XYZ"],
  estimatedImpact: "+15% Buy Box win rate",
  confidence: 0.87,
  reasoning: "Competitor A dropped price by 8%. Current Buy Box at $24.99. Matching maintains 22% margin.",
  priority: "high" as const,
  createdAt: "2026-03-20T10:00:00Z",
};

describe("ApprovalCard", () => {
  const user = userEvent.setup();

  it("renders the action description", () => {
    render(<ApprovalCard action={mockAction} onApprove={vi.fn()} onReject={vi.fn()} />);
    expect(screen.getByText(/Reduce price on B08XYZ/)).toBeInTheDocument();
  });

  it("shows agent type with colored indicator", () => {
    render(<ApprovalCard action={mockAction} onApprove={vi.fn()} onReject={vi.fn()} />);
    expect(screen.getByText(/pricing/i)).toBeInTheDocument();
  });

  it("displays confidence as percentage", () => {
    render(<ApprovalCard action={mockAction} onApprove={vi.fn()} onReject={vi.fn()} />);
    expect(screen.getByText("87%")).toBeInTheDocument();
  });

  it("calls onApprove with action id on click", async () => {
    const onApprove = vi.fn();
    render(<ApprovalCard action={mockAction} onApprove={onApprove} onReject={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: /approve/i }));
    expect(onApprove).toHaveBeenCalledWith("action-1");
  });

  it("calls onReject with action id on click", async () => {
    const onReject = vi.fn();
    render(<ApprovalCard action={mockAction} onApprove={vi.fn()} onReject={onReject} />);
    await user.click(screen.getByRole("button", { name: /reject/i }));
    expect(onReject).toHaveBeenCalledWith("action-1");
  });

  it("toggles reasoning section visibility", async () => {
    render(<ApprovalCard action={mockAction} onApprove={vi.fn()} onReject={vi.fn()} />);
    const toggle = screen.getByText(/show reasoning/i);
    expect(screen.queryByText(/Competitor A dropped/)).not.toBeVisible();
    await user.click(toggle);
    expect(screen.getByText(/Competitor A dropped/)).toBeVisible();
  });

  it("shows ASIN in data badge format", () => {
    render(<ApprovalCard action={mockAction} onApprove={vi.fn()} onReject={vi.fn()} />);
    const badge = screen.getByText("B08XYZ");
    expect(badge.className).toMatch(/border-dashed|primary-pop|font-bold/);
  });

  it("has colored left border matching agent type", () => {
    const { container } = render(
      <ApprovalCard action={mockAction} onApprove={vi.fn()} onReject={vi.fn()} />
    );
    expect((container.firstChild as HTMLElement).className).toMatch(/border-l/);
  });

  it("approve button has 3D push style", () => {
    render(<ApprovalCard action={mockAction} onApprove={vi.fn()} onReject={vi.fn()} />);
    const btn = screen.getByRole("button", { name: /approve/i });
    expect(btn.className).toMatch(/shadow/);
    expect(btn.className).toMatch(/emerald|green/);
  });

  it("shows relative time for createdAt", () => {
    render(<ApprovalCard action={mockAction} onApprove={vi.fn()} onReject={vi.fn()} />);
    expect(screen.getByTestId("approval-time")).toBeInTheDocument();
  });
});
