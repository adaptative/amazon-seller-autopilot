"use client";

import React, { useEffect, useMemo, useState } from "react";
import { listingsApi, type Listing } from "@/lib/api";
import { HealthScoreBar } from "./HealthScoreBar";

export interface CatalogViewProps {
  onOptimize?: (asin: string) => void;
}

export function CatalogView({ onOptimize }: CatalogViewProps) {
  const [listings, setListings] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    listingsApi
      .list()
      .then((res) => {
        setListings(res.items);
        setTotal(res.total);
      })
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    let result = listings;
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (l) =>
          l.title.toLowerCase().includes(q) ||
          l.asin.toLowerCase().includes(q)
      );
    }
    if (statusFilter !== "all") {
      result = result.filter((l) => l.status === statusFilter);
    }
    return result;
  }, [listings, search, statusFilter]);

  if (loading) {
    return (
      <div className="animate-pulse p-8">
        <div className="h-8 bg-slate-200 rounded w-48 mb-6" />
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-12 bg-slate-100 rounded" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-display font-bold text-slate-800">
            Listing Management
          </h1>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 rounded-full">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse" />
            <span className="text-xs font-medium text-blue-700">
              Listing Agent
            </span>
            <span className="text-xs text-blue-500">Active</span>
          </div>
        </div>
        <button className="px-5 py-2.5 bg-primary-pop text-white font-display font-bold rounded-xl shadow-[0_4px_0_rgb(30,58,138)] hover:shadow-[0_2px_0_rgb(30,58,138)] hover:translate-y-0.5 transition-all">
          Optimize All
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-md">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            placeholder="Search by title or ASIN..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border-2 border-slate-200 rounded-xl text-sm font-body focus:border-primary-pop focus:outline-none"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2.5 border-2 border-slate-200 rounded-xl text-sm font-body focus:border-primary-pop focus:outline-none"
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="suppressed">Suppressed</option>
        </select>
      </div>

      {/* Data Table */}
      <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50">
              <th className="px-4 py-3 text-xs uppercase tracking-wider text-slate-400 font-body text-left">
                Product
              </th>
              <th className="px-4 py-3 text-xs uppercase tracking-wider text-slate-400 font-body text-left">
                ASIN
              </th>
              <th className="px-4 py-3 text-xs uppercase tracking-wider text-slate-400 font-body text-right">
                Price
              </th>
              <th className="px-4 py-3 text-xs uppercase tracking-wider text-slate-400 font-body text-right">
                BSR
              </th>
              <th className="px-4 py-3 text-xs uppercase tracking-wider text-slate-400 font-body text-left">
                Health Score
              </th>
              <th className="px-4 py-3 text-xs uppercase tracking-wider text-slate-400 font-body text-center">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((listing) => (
              <tr
                key={listing.asin}
                className="border-b border-slate-100 hover:bg-sky-50 transition-colors"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <img
                      src={listing.imageUrl}
                      alt={listing.title}
                      className="w-12 h-12 rounded-lg object-cover bg-slate-100"
                    />
                    <span className="text-sm font-body text-slate-800 line-clamp-2 max-w-xs">
                      {listing.title}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="inline-block px-2 py-1 bg-white border-2 border-dashed border-primary-pop/30 rounded-lg text-primary-pop font-bold text-sm">
                    {listing.asin}
                  </span>
                </td>
                <td className="px-4 py-3 text-right text-sm font-body tabular-nums">
                  ${listing.price.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-right text-sm font-body tabular-nums">
                  {listing.bsr.toLocaleString()}
                </td>
                <td className="px-4 py-3">
                  <HealthScoreBar score={listing.healthScore} asin={listing.asin} />
                </td>
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={() => onOptimize?.(listing.asin)}
                    className="px-3 py-1.5 text-sm font-body font-medium text-primary-pop border-2 border-primary-pop/30 rounded-lg hover:bg-primary-pop/5 transition-colors"
                  >
                    Optimize
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-4 py-3 border-t border-slate-100 text-sm text-slate-500 font-body flex items-center justify-between">
          <span>
            Showing 1-{filtered.length} of {total} listings
          </span>
          <div className="flex gap-1">
            <button className="px-3 py-1 rounded-lg hover:bg-slate-100">&laquo;</button>
            <button className="px-3 py-1 rounded-lg hover:bg-slate-100">&raquo;</button>
          </div>
        </div>
      </div>
    </div>
  );
}
