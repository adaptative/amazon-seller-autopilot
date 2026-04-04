"use client";

import React, { useMemo, useState } from "react";

interface Column {
  accessorKey: string;
  header: string;
  isDataId?: boolean;
  align?: "left" | "right" | "center";
}

export interface DataTableProps {
  columns: Column[];
  data: Record<string, any>[];
  searchable?: boolean;
  loading?: boolean;
  emptyMessage?: string;
  selectable?: boolean;
  onSelectionChange?: (selectedRows: Record<string, any>[]) => void;
}

export function DataTable({
  columns,
  data,
  searchable,
  loading,
  emptyMessage,
  selectable,
  onSelectionChange,
}: DataTableProps) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<number>>(new Set());

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const filteredData = useMemo(() => {
    if (!search) return data;
    const lower = search.toLowerCase();
    return data.filter((row) =>
      Object.values(row).some((v) =>
        String(v).toLowerCase().includes(lower)
      )
    );
  }, [data, search]);

  const sortedData = useMemo(() => {
    if (!sortKey) return filteredData;
    return [...filteredData].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDir === "asc" ? aVal - bVal : bVal - aVal;
      }
      return sortDir === "asc"
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal));
    });
  }, [filteredData, sortKey, sortDir]);

  const toggleRow = (idx: number) => {
    const next = new Set(selected);
    if (next.has(idx)) next.delete(idx);
    else next.add(idx);
    setSelected(next);
    onSelectionChange?.(sortedData.filter((_, i) => next.has(i)));
  };

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50">
              {columns.map((col) => (
                <th key={col.accessorKey} className="px-4 py-3 text-xs uppercase tracking-wider text-slate-400 font-body text-left">
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[0, 1, 2].map((i) => (
              <tr key={i} data-testid="skeleton-row" className="border-b border-slate-100">
                {columns.map((col) => (
                  <td key={col.accessorKey} className="px-4 py-3">
                    <div className="h-4 bg-slate-200 rounded animate-pulse w-24" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
      {searchable && (
        <div className="p-4 border-b border-slate-100">
          <input
            type="text"
            placeholder="Search..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3 py-2 border-2 border-slate-200 rounded-xl text-sm font-body focus:border-primary-pop focus:outline-none"
          />
        </div>
      )}
      <table className="w-full">
        <thead>
          <tr className="bg-slate-50">
            {selectable && (
              <th className="px-4 py-3 w-10">
                <input type="checkbox" aria-label="Select all" onChange={() => {}} />
              </th>
            )}
            {columns.map((col) => (
              <th
                key={col.accessorKey}
                onClick={() => handleSort(col.accessorKey)}
                className={`px-4 py-3 text-xs uppercase tracking-wider text-slate-400 font-body cursor-pointer hover:text-slate-600 ${
                  col.align === "right" ? "text-right" : "text-left"
                }`}
              >
                {col.header}
                {sortKey === col.accessorKey && (sortDir === "asc" ? " ↑" : " ↓")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.length === 0 && emptyMessage ? (
            <tr>
              <td colSpan={columns.length + (selectable ? 1 : 0)} className="px-4 py-8 text-center text-slate-400 font-body">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sortedData.map((row, idx) => (
              <tr key={idx} className="border-b border-slate-100 hover:bg-sky-50 transition-colors">
                {selectable && (
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selected.has(idx)}
                      onChange={() => toggleRow(idx)}
                      aria-label={`Select row ${idx}`}
                    />
                  </td>
                )}
                {columns.map((col) => (
                  <td
                    key={col.accessorKey}
                    className={`px-4 py-3 text-sm font-body ${
                      col.align === "right" ? "text-right tabular-nums" : ""
                    }`}
                  >
                    {col.isDataId ? (
                      <span className="inline-block px-2 py-1 bg-white border-2 border-dashed border-primary-pop/30 rounded-lg text-primary-pop font-bold text-sm">
                        {row[col.accessorKey]}
                      </span>
                    ) : (
                      row[col.accessorKey]
                    )}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
