"use client";

import React from "react";
import type { PricedProduct } from "@/lib/api";

export interface PriceTableProps {
  products: PricedProduct[];
  total: number;
  onReprice?: (asin: string) => void;
}

export function PriceTable({ products, total, onReprice }: PriceTableProps) {
  return (
    <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100">
        <h3 className="text-lg font-display font-bold text-slate-800">
          Price History
        </h3>
      </div>
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
              Our Price
            </th>
            <th className="px-4 py-3 text-xs uppercase tracking-wider text-slate-400 font-body text-right">
              Buy Box Price
            </th>
            <th className="px-4 py-3 text-xs uppercase tracking-wider text-slate-400 font-body text-center">
              Competitors
            </th>
            <th className="px-4 py-3 text-xs uppercase tracking-wider text-slate-400 font-body text-center">
              Buy Box
            </th>
            <th className="px-4 py-3 text-xs uppercase tracking-wider text-slate-400 font-body text-left">
              Last Change
            </th>
            <th className="px-4 py-3 text-xs uppercase tracking-wider text-slate-400 font-body text-center">
              Action
            </th>
          </tr>
        </thead>
        <tbody>
          {products.map((product) => {
            const priceDiff = product.ourPrice - product.buyBoxPrice;
            const priceCompareColor =
              priceDiff < 0
                ? "text-emerald-600"
                : priceDiff > 0
                ? "text-rose-600"
                : "text-slate-600";
            const priceArrow = priceDiff < 0 ? "\u2193" : priceDiff > 0 ? "\u2191" : "";

            return (
              <tr
                key={product.asin}
                className="border-b border-slate-100 hover:bg-sky-50 transition-colors"
              >
                {/* Product */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    {product.imageUrl && (
                      <img
                        src={product.imageUrl}
                        alt={product.title}
                        className="w-10 h-10 rounded-lg object-cover bg-slate-100"
                      />
                    )}
                    <span className="text-sm font-body text-slate-800 line-clamp-2 max-w-xs">
                      {product.title}
                    </span>
                  </div>
                </td>

                {/* ASIN */}
                <td className="px-4 py-3">
                  <span className="inline-block px-2 py-1 bg-white border-2 border-dashed border-primary-pop/30 rounded-lg text-primary-pop font-bold text-sm">
                    {product.asin}
                  </span>
                </td>

                {/* Our Price */}
                <td className="px-4 py-3 text-right">
                  <span className="font-display font-bold text-slate-800 tabular-nums">
                    ${product.ourPrice.toFixed(2)}
                  </span>
                </td>

                {/* Buy Box Price */}
                <td className="px-4 py-3 text-right">
                  <span className={`text-sm font-body tabular-nums ${priceCompareColor}`}>
                    ${product.buyBoxPrice.toFixed(2)} {priceArrow}
                  </span>
                </td>

                {/* Competitors */}
                <td className="px-4 py-3 text-center">
                  <span className="inline-block px-2 py-0.5 bg-slate-100 rounded-full text-xs font-body text-slate-600">
                    {product.competitorCount} sellers
                  </span>
                </td>

                {/* Buy Box Status */}
                <td className="px-4 py-3 text-center">
                  {product.weOwnBuyBox ? (
                    <span
                      data-testid="buybox-status"
                      className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 text-emerald-600"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </span>
                  ) : (
                    <span
                      data-testid="buybox-status"
                      className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-rose-100 text-rose-600"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </span>
                  )}
                </td>

                {/* Last Change */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1">
                    <span className="text-sm font-body text-slate-600">
                      {product.lastChange}
                    </span>
                    {product.lastChangeDir === "down" && (
                      <span className="text-emerald-500 text-xs">{"\u2193"}</span>
                    )}
                    {product.lastChangeDir === "up" && (
                      <span className="text-rose-500 text-xs">{"\u2191"}</span>
                    )}
                  </div>
                </td>

                {/* Action */}
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={() => onReprice?.(product.asin)}
                    className="px-3 py-1.5 text-sm font-body font-medium text-primary-pop border-2 border-primary-pop/30 rounded-lg hover:bg-primary-pop/5 transition-colors"
                  >
                    Reprice
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-slate-100 text-sm text-slate-500 font-body flex items-center justify-between">
        <span>
          Showing 1-{products.length} of {total} tracked products
        </span>
        <div className="flex gap-1">
          <button className="px-3 py-1 rounded-lg hover:bg-slate-100">&laquo;</button>
          <button className="px-3 py-1 rounded-lg hover:bg-slate-100">&raquo;</button>
        </div>
      </div>
    </div>
  );
}
