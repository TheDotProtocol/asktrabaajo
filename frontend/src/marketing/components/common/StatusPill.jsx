"use client";

/** Unused on public pages. Kept so existing imports do not break. Do not add development-status labels. */
export const StatusPill = ({ status, className = "" }) => (
  <span
    data-testid={`status-pill-${String(status || "").toLowerCase().replace(/\s+/g, "-")}`}
    className={`inline-flex items-center gap-1.5 border border-white/15 px-2.5 py-0.5 text-[10px] font-mono rounded-full uppercase tracking-[0.18em] text-mist ${className}`}
  >
    <span className="w-1 h-1 rounded-full bg-current" />
    {status}
  </span>
);

export default StatusPill;
