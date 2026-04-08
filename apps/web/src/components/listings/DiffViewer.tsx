"use client";

import React from "react";

export interface DiffViewerProps {
  oldText: string;
  newText: string;
  added?: string[];
  removed?: string[];
}

export function DiffViewer({ oldText, newText, added, removed }: DiffViewerProps) {
  if (added || removed) {
    return (
      <span>
        {removed?.map((text, i) => (
          <span
            key={`rm-${i}`}
            data-testid="diff-removed"
            className="bg-rose-50 text-rose-500 line-through"
          >
            {text}
          </span>
        ))}
        {removed && added && " "}
        {added?.map((text, i) => (
          <span
            key={`add-${i}`}
            data-testid="diff-added"
            className="bg-emerald-50 text-emerald-700 underline"
          >
            {text}
          </span>
        ))}
      </span>
    );
  }

  // Simple text comparison fallback
  if (oldText === newText) {
    return <span>{newText}</span>;
  }

  return (
    <span>
      <span data-testid="diff-removed" className="bg-rose-50 text-rose-500 line-through">
        {oldText}
      </span>{" "}
      <span data-testid="diff-added" className="bg-emerald-50 text-emerald-700 underline">
        {newText}
      </span>
    </span>
  );
}
