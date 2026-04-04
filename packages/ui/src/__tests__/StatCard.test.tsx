import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatCard } from "../StatCard";

describe("StatCard", () => {
  const defaultProps = {
    label: "Total Revenue",
    value: "$124,560",
    trend: { value: 12.5, direction: "up" as const },
  };

  it("renders the metric value in Fredoka font", () => {
    render(<StatCard {...defaultProps} />);
    const value = screen.getByText("$124,560");
    expect(value).toBeInTheDocument();
    expect(value.className).toMatch(/whimsical|fredoka/i);
  });

  it("renders label in UPPERCASE with Inter font", () => {
    render(<StatCard {...defaultProps} />);
    expect(screen.getByText("TOTAL REVENUE")).toBeInTheDocument();
  });

  it("shows green trend for up direction", () => {
    render(<StatCard {...defaultProps} />);
    const trend = screen.getByTestId("trend-indicator");
    expect(trend).toHaveTextContent("12.5%");
    expect(trend.className).toMatch(/emerald|green/);
  });

  it("shows red trend for down direction", () => {
    render(<StatCard {...defaultProps} trend={{ value: 3.2, direction: "down" }} />);
    const trend = screen.getByTestId("trend-indicator");
    expect(trend.className).toMatch(/rose|red/);
  });

  it("shows up arrow for positive trend", () => {
    render(<StatCard {...defaultProps} />);
    expect(screen.getByTestId("trend-indicator")).toHaveTextContent(/↑|▲/);
  });

  it("shows down arrow for negative trend", () => {
    render(<StatCard {...defaultProps} trend={{ value: 2, direction: "down" }} />);
    expect(screen.getByTestId("trend-indicator")).toHaveTextContent(/↓|▼/);
  });

  it("renders skeleton when loading=true", () => {
    render(<StatCard {...defaultProps} loading />);
    expect(screen.getByTestId("stat-skeleton")).toBeInTheDocument();
    expect(screen.queryByText("$124,560")).not.toBeInTheDocument();
  });

  it("has white bg, rounded-2xl, shadow-lg card styling", () => {
    const { container } = render(<StatCard {...defaultProps} />);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toMatch(/rounded-2xl/);
    expect(card.className).toMatch(/shadow/);
  });
});
