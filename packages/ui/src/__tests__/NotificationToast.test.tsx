import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NotificationToast } from "../NotificationToast";

describe("NotificationToast", () => {
  const user = userEvent.setup();

  it("renders title and message", () => {
    render(
      <NotificationToast severity="success" title="Buy Box won!" message="Agent matched competitor." onDismiss={vi.fn()} />
    );
    expect(screen.getByText("Buy Box won!")).toBeInTheDocument();
    expect(screen.getByText("Agent matched competitor.")).toBeInTheDocument();
  });

  it("shows green left border for success", () => {
    const { container } = render(
      <NotificationToast severity="success" title="OK" message="" onDismiss={vi.fn()} />
    );
    expect((container.firstChild as HTMLElement).className).toMatch(/emerald|green/);
    expect((container.firstChild as HTMLElement).className).toMatch(/border-l/);
  });

  it("shows amber left border for warning", () => {
    const { container } = render(
      <NotificationToast severity="warning" title="Low stock" message="" onDismiss={vi.fn()} />
    );
    expect((container.firstChild as HTMLElement).className).toMatch(/amber|yellow/);
  });

  it("shows red left border for error", () => {
    const { container } = render(
      <NotificationToast severity="error" title="Failed" message="" onDismiss={vi.fn()} />
    );
    expect((container.firstChild as HTMLElement).className).toMatch(/rose|red/);
  });

  it("calls onDismiss when close button clicked", async () => {
    const onDismiss = vi.fn();
    render(
      <NotificationToast severity="info" title="Info" message="" onDismiss={onDismiss} />
    );
    await user.click(screen.getByRole("button", { name: /close|dismiss/i }));
    expect(onDismiss).toHaveBeenCalled();
  });
});
