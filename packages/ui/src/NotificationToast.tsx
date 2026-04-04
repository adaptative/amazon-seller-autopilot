"use client";

import React from "react";

type Severity = "success" | "warning" | "error" | "info";

export interface NotificationToastProps {
  severity: Severity;
  title: string;
  message: string;
  onDismiss: () => void;
}

const SEVERITY_STYLES: Record<Severity, { border: string; icon: string; iconBg: string }> = {
  success: { border: "border-l-emerald-500", icon: "text-emerald-500", iconBg: "bg-emerald-50" },
  warning: { border: "border-l-amber-500", icon: "text-amber-500", iconBg: "bg-amber-50" },
  error: { border: "border-l-rose-500", icon: "text-rose-500", iconBg: "bg-rose-50" },
  info: { border: "border-l-cyan-500", icon: "text-cyan-500", iconBg: "bg-cyan-50" },
};

const SEVERITY_ICONS: Record<Severity, string> = {
  success: "\u2713",
  warning: "\u26A0",
  error: "\u2717",
  info: "\u2139",
};

export function NotificationToast({ severity, title, message, onDismiss }: NotificationToastProps) {
  const styles = SEVERITY_STYLES[severity];

  return (
    <div className={`bg-white rounded-xl shadow-xl border-l-4 ${styles.border} p-4 flex items-start gap-3 max-w-sm`}>
      <span className={`flex-shrink-0 w-8 h-8 rounded-full ${styles.iconBg} ${styles.icon} flex items-center justify-center text-lg`}>
        {SEVERITY_ICONS[severity]}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-bold text-slate-800 font-body">{title}</p>
        {message && <p className="text-xs text-slate-500 mt-0.5 font-body">{message}</p>}
      </div>
      <button
        onClick={onDismiss}
        aria-label="Close"
        className="flex-shrink-0 text-slate-400 hover:text-slate-600 text-lg leading-none"
      >
        &times;
      </button>
    </div>
  );
}
