"use client";

import React, { useEffect, useState } from "react";
import { listingsApi, type ListingDetail, type ListingSuggestion } from "@/lib/api";
import { DiffViewer } from "./DiffViewer";

export interface ListingEditorProps {
  asin: string;
  onBack?: () => void;
}

export function ListingEditor({ asin, onBack }: ListingEditorProps) {
  const [current, setCurrent] = useState<ListingDetail | null>(null);
  const [suggestion, setSuggestion] = useState<ListingSuggestion | null>(null);
  const [loading, setLoading] = useState(true);
  const [reasoningOpen, setReasoningOpen] = useState(false);

  const fetchData = () => {
    setLoading(true);
    Promise.all([listingsApi.get(asin), listingsApi.getSuggestion(asin)])
      .then(([detail, sugg]) => {
        setCurrent(detail);
        setSuggestion(sugg);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();
  }, [asin]);

  const handleApplyAll = () => {
    if (!suggestion) return;
    listingsApi.applySuggestion(asin, suggestion);
  };

  const handleRegenerate = () => {
    listingsApi.getSuggestion(asin).then(setSuggestion);
  };

  if (loading || !current || !suggestion) {
    return (
      <div className="animate-pulse p-8">
        <div className="h-8 bg-slate-200 rounded w-64 mb-6" />
        <div className="grid grid-cols-2 gap-6">
          <div className="h-96 bg-slate-100 rounded-2xl" />
          <div className="h-96 bg-slate-100 rounded-2xl" />
        </div>
      </div>
    );
  }

  const confidencePercent = Math.round(suggestion.confidence * 100);

  return (
    <div className="flex flex-col h-full">
      {/* Top Bar */}
      <div className="flex items-center gap-4 mb-6">
        {onBack && (
          <button
            onClick={onBack}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            aria-label="Go back"
          >
            <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        )}
        <span className="inline-block px-2 py-1 bg-white border-2 border-dashed border-primary-pop/30 rounded-lg text-primary-pop font-bold text-sm">
          {asin}
        </span>
        <span className="font-body font-bold text-slate-800">{current.title}</span>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-sm text-slate-500 font-body">Listing Health</span>
          <div className="w-20 h-2 bg-slate-200 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${
                current.healthScore >= 70
                  ? "bg-emerald-500"
                  : current.healthScore >= 40
                  ? "bg-amber-500"
                  : "bg-rose-500"
              }`}
              style={{ width: `${current.healthScore}%` }}
            />
          </div>
          <span className="text-sm font-bold font-body tabular-nums">{current.healthScore}/100</span>
        </div>
      </div>

      {/* Agent indicator */}
      <div className="flex items-center gap-2 mb-4">
        <span className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse" />
        <span className="text-sm text-blue-600 font-body">Listing Agent optimizing...</span>
      </div>

      {/* Split Panel */}
      <div className="grid grid-cols-2 gap-6 flex-1 min-h-0">
        {/* Left Panel — Current Listing */}
        <div className="bg-white rounded-2xl shadow-lg p-6 overflow-y-auto">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-display font-bold text-slate-800">Current Listing</h2>
            <span className="text-xs text-slate-400 font-body">
              Last synced {current.lastSyncedAt || "3 min ago"}
            </span>
          </div>

          {/* Title */}
          <div className="mb-4">
            <h3 className="text-xs uppercase tracking-wider text-slate-400 font-body mb-1">Title</h3>
            <p className="text-sm font-body text-slate-800">{current.title}</p>
          </div>

          <hr className="border-slate-100 my-3" />

          {/* Bullet Points */}
          <div className="mb-4">
            <h3 className="text-xs uppercase tracking-wider text-slate-400 font-body mb-2">Bullet Points</h3>
            {current.bullets.map((bullet, i) => (
              <div key={i} className="flex items-start gap-2 mb-2">
                <span className="text-xs font-bold text-slate-400 mt-0.5 w-4">{i + 1}.</span>
                <div className="flex-1">
                  <p className="text-sm font-body text-slate-700">{bullet}</p>
                  <span
                    data-testid={`char-count-bullet-${i}`}
                    className="text-xs text-slate-400 font-body"
                  >
                    {bullet.length}/500
                  </span>
                </div>
              </div>
            ))}
          </div>

          <hr className="border-slate-100 my-3" />

          {/* Description */}
          <div className="mb-4">
            <h3 className="text-xs uppercase tracking-wider text-slate-400 font-body mb-1">Description</h3>
            <p className="text-sm font-body text-slate-700">{current.description}</p>
          </div>

          <hr className="border-slate-100 my-3" />

          {/* Search Terms */}
          <div>
            <h3 className="text-xs uppercase tracking-wider text-slate-400 font-body mb-1">Search Terms</h3>
            <div className="bg-slate-50 rounded-lg px-3 py-2 font-mono text-sm text-slate-700">
              {current.searchTerms}
            </div>
          </div>
        </div>

        {/* Right Panel — AI Suggestion */}
        <div className="bg-white rounded-2xl shadow-lg p-6 border-l-4 border-primary-pop overflow-y-auto">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-display font-bold text-slate-800">AI Suggestion</h2>
              <svg className="w-5 h-5 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            </div>
            <span className="px-2.5 py-1 bg-emerald-100 text-emerald-700 text-xs font-bold rounded-full">
              {confidencePercent}%
            </span>
          </div>

          {/* Title with diff */}
          <div className="mb-4">
            <h3 className="text-xs uppercase tracking-wider text-slate-400 font-body mb-1">Title</h3>
            {suggestion.diff.title ? (
              <DiffViewer
                oldText={current.title}
                newText={suggestion.title}
                added={suggestion.diff.title.added}
                removed={suggestion.diff.title.removed}
              />
            ) : (
              <p className="text-sm font-body text-slate-800">{suggestion.title}</p>
            )}
          </div>

          <hr className="border-slate-100 my-3" />

          {/* Bullet Points */}
          <div className="mb-4">
            <h3 className="text-xs uppercase tracking-wider text-slate-400 font-body mb-2">Bullet Points</h3>
            {suggestion.bullets.map((bullet, i) => {
              const bulletDiff = suggestion.diff.bullets?.find((d) => d.index === i);
              return (
                <div key={i} className="flex items-start gap-2 mb-2">
                  <span className="text-xs font-bold text-slate-400 mt-0.5 w-4">{i + 1}.</span>
                  <div className="flex-1">
                    {bulletDiff ? (
                      <DiffViewer oldText={bulletDiff.old} newText={bulletDiff.new} />
                    ) : (
                      <p className="text-sm font-body text-slate-700">{bullet}</p>
                    )}
                    <span
                      data-testid={`char-count-suggestion-bullet-${i}`}
                      className="text-xs text-slate-400 font-body"
                    >
                      {bullet.length}/500
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          <hr className="border-slate-100 my-3" />

          {/* Description */}
          <div className="mb-4">
            <h3 className="text-xs uppercase tracking-wider text-slate-400 font-body mb-1">Description</h3>
            {suggestion.diff.description ? (
              <DiffViewer
                oldText={suggestion.diff.description.old}
                newText={suggestion.diff.description.new}
              />
            ) : (
              <p className="text-sm font-body text-slate-700">{suggestion.description}</p>
            )}
          </div>

          <hr className="border-slate-100 my-3" />

          {/* Search Terms */}
          <div className="mb-4">
            <h3 className="text-xs uppercase tracking-wider text-slate-400 font-body mb-1">Search Terms</h3>
            <div className="bg-slate-50 rounded-lg px-3 py-2 font-mono text-sm text-slate-700">
              {suggestion.searchTerms}
            </div>
          </div>

          {/* Reasoning */}
          <div className="mt-4">
            <button
              onClick={() => setReasoningOpen(!reasoningOpen)}
              className="flex items-center gap-1 text-sm text-slate-600 font-body hover:text-slate-800"
            >
              <svg
                className={`w-4 h-4 transition-transform ${reasoningOpen ? "rotate-90" : ""}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              Reasoning
            </button>
            {reasoningOpen && (
              <p className="mt-2 text-sm font-body text-slate-500 italic pl-5">
                {suggestion.reasoning}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Action Bar */}
      <div className="sticky bottom-0 bg-white shadow-[0_-4px_12px_rgba(0,0,0,0.05)] mt-6 -mx-6 px-6 py-4 flex items-center gap-3">
        <button
          onClick={handleApplyAll}
          className="px-5 py-2.5 bg-primary-pop text-white font-display font-bold rounded-xl shadow-[0_4px_0_rgb(30,58,138)] hover:shadow-[0_2px_0_rgb(30,58,138)] hover:translate-y-0.5 transition-all"
        >
          Apply All Changes
        </button>
        <button className="px-5 py-2.5 bg-slate-100 text-slate-700 font-display font-medium rounded-xl hover:bg-slate-200 transition-colors">
          Apply Selected
        </button>
        <button className="px-5 py-2.5 border-2 border-slate-200 text-slate-600 font-display font-medium rounded-xl hover:bg-slate-50 transition-colors">
          Reject
        </button>
        <button
          onClick={handleRegenerate}
          className="ml-auto px-5 py-2.5 text-slate-600 font-body font-medium hover:text-slate-800 flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Regenerate
        </button>
      </div>
    </div>
  );
}
