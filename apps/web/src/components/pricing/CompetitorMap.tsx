"use client";

import React from "react";
import type { CompetitorPoint } from "@/lib/api";

export interface CompetitorMapProps {
  data: CompetitorPoint[];
}

export function CompetitorMap({ data }: CompetitorMapProps) {
  const width = 500;
  const height = 200;
  const padding = { top: 20, right: 20, bottom: 30, left: 50 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const points = data.length > 0 ? data : generateSampleData();

  // Scales
  const ratings = points.map((p) => p.rating);
  const prices = points.map((p) => p.price);
  const minRating = Math.min(...ratings, 3.0);
  const maxRating = Math.max(...ratings, 5.0);
  const minPrice = Math.min(...prices) * 0.9;
  const maxPrice = Math.max(...prices) * 1.1;

  const xScale = (rating: number) =>
    padding.left + ((rating - minRating) / (maxRating - minRating)) * chartW;
  const yScale = (price: number) =>
    padding.top + chartH - ((price - minPrice) / (maxPrice - minPrice)) * chartH;

  return (
    <div className="bg-white rounded-2xl shadow-lg p-6" data-testid="competitor-chart">
      <h3 className="text-lg font-display font-bold text-slate-800 mb-4">
        Competitor Price Map
      </h3>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
        {/* Y-axis label */}
        <text
          x={12}
          y={height / 2}
          transform={`rotate(-90 12 ${height / 2})`}
          className="text-[10px] fill-slate-400"
          textAnchor="middle"
        >
          Price ($)
        </text>

        {/* X-axis label */}
        <text
          x={width / 2}
          y={height - 4}
          className="text-[10px] fill-slate-400"
          textAnchor="middle"
        >
          Seller Rating
        </text>

        {/* Grid lines */}
        {[3.0, 3.5, 4.0, 4.5, 5.0].map((r) => (
          <line
            key={r}
            x1={xScale(r)}
            y1={padding.top}
            x2={xScale(r)}
            y2={height - padding.bottom}
            stroke="#f1f5f9"
            strokeWidth={1}
          />
        ))}

        {/* Data points */}
        {points.map((p, i) => (
          <g key={i}>
            {/* Buy Box winner ring */}
            {p.isBuyBoxWinner && (
              <circle
                cx={xScale(p.rating)}
                cy={yScale(p.price)}
                r={p.isOurs ? 16 : 12}
                fill="none"
                stroke="#22c55e"
                strokeWidth={2}
              />
            )}
            {/* Dot */}
            <circle
              cx={xScale(p.rating)}
              cy={yScale(p.price)}
              r={p.isOurs ? 6 : 4}
              fill={p.isOurs ? "#3b82f6" : "#94a3b8"}
              className="cursor-pointer"
            >
              <title>
                {p.sellerName}: ${p.price.toFixed(2)} ({p.rating.toFixed(1)} stars)
              </title>
            </circle>
          </g>
        ))}
      </svg>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-3 text-xs font-body text-slate-500">
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-blue-500" />
          Our Products
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-slate-400" />
          Competitors
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full border-2 border-green-500" />
          Buy Box Winner
        </div>
      </div>
    </div>
  );
}

function generateSampleData(): CompetitorPoint[] {
  return [
    { sellerId: "US", sellerName: "Our Store", price: 24.99, rating: 4.6, isOurs: true, isBuyBoxWinner: true },
    { sellerId: "C1", sellerName: "Seller Alpha", price: 26.50, rating: 4.2, isOurs: false, isBuyBoxWinner: false },
    { sellerId: "C2", sellerName: "Seller Beta", price: 25.99, rating: 4.4, isOurs: false, isBuyBoxWinner: false },
    { sellerId: "C3", sellerName: "Seller Gamma", price: 28.00, rating: 3.8, isOurs: false, isBuyBoxWinner: false },
    { sellerId: "US2", sellerName: "Our Store (B)", price: 19.99, rating: 4.6, isOurs: true, isBuyBoxWinner: false },
    { sellerId: "C4", sellerName: "Seller Delta", price: 22.50, rating: 4.0, isOurs: false, isBuyBoxWinner: false },
  ];
}
