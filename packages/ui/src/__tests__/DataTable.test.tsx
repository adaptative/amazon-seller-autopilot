import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DataTable } from "../DataTable";

const columns = [
  { accessorKey: "asin", header: "ASIN", isDataId: true },
  { accessorKey: "title", header: "Title" },
  { accessorKey: "price", header: "Price", align: "right" as const },
  { accessorKey: "status", header: "Status" },
];
const data = [
  { asin: "B08ABC", title: "Wireless Earbuds", price: 29.99, status: "active" },
  { asin: "B08DEF", title: "Phone Case", price: 14.99, status: "inactive" },
  { asin: "B08GHI", title: "USB Cable", price: 9.99, status: "active" },
];

describe("DataTable", () => {
  const user = userEvent.setup();

  it("renders all data rows plus header", () => {
    render(<DataTable columns={columns} data={data} />);
    expect(screen.getAllByRole("row")).toHaveLength(4);
  });

  it("renders column headers in uppercase", () => {
    render(<DataTable columns={columns} data={data} />);
    // Headers use CSS uppercase class, so DOM text is as-provided
    expect(screen.getByText("ASIN")).toBeInTheDocument();
    expect(screen.getByText("Title")).toBeInTheDocument();
    // Verify uppercase CSS class is applied
    const headerCells = screen.getAllByRole("columnheader");
    expect(headerCells[0].className).toMatch(/uppercase/);
  });

  it("sorts ascending on first header click", async () => {
    render(<DataTable columns={columns} data={data} />);
    await user.click(screen.getByText("Price"));
    const rows = screen.getAllByRole("row");
    expect(rows[1]).toHaveTextContent("9.99");
  });

  it("sorts descending on second click", async () => {
    render(<DataTable columns={columns} data={data} />);
    await user.click(screen.getByText("Price"));
    await user.click(screen.getByText(/Price/));
    const rows = screen.getAllByRole("row");
    expect(rows[1]).toHaveTextContent("29.99");
  });

  it("filters with search input when searchable", async () => {
    render(<DataTable columns={columns} data={data} searchable />);
    await user.type(screen.getByPlaceholderText(/search/i), "Earbuds");
    await waitFor(() => expect(screen.getAllByRole("row")).toHaveLength(2));
  });

  it("shows empty state when no data", () => {
    render(<DataTable columns={columns} data={[]} emptyMessage="Nothing here yet" />);
    expect(screen.getByText(/nothing here yet/i)).toBeInTheDocument();
  });

  it("shows skeleton rows when loading", () => {
    render(<DataTable columns={columns} data={[]} loading />);
    expect(screen.getAllByTestId("skeleton-row").length).toBeGreaterThanOrEqual(3);
  });

  it("renders ASIN columns in data badge format", () => {
    render(<DataTable columns={columns} data={data} />);
    const asin = screen.getByText("B08ABC");
    expect(asin.className).toMatch(/primary-pop|border-dashed|font-bold/);
  });

  it("supports row selection when selectable", async () => {
    const onSelect = vi.fn();
    render(<DataTable columns={columns} data={data} selectable onSelectionChange={onSelect} />);
    const checkboxes = screen.getAllByRole("checkbox");
    await user.click(checkboxes[1]);
    expect(onSelect).toHaveBeenCalled();
  });

  it("header row has bg-slate-50 styling", () => {
    render(<DataTable columns={columns} data={data} />);
    const headerRow = screen.getAllByRole("row")[0];
    expect(headerRow.className).toMatch(/slate-50/);
  });
});
