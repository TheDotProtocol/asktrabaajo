"use client";

const STYLES = {
  LIVE: "bg-emerald-950/70 text-emerald-400 border-emerald-500/40",
  "AVAILABLE NOW": "bg-emerald-950/70 text-emerald-400 border-emerald-500/40",
  "IN DEVELOPMENT": "bg-blue-950/70 text-blue-400 border-blue-500/40",
  COMING: "bg-amber-950/70 text-amber-400 border-amber-500/40",
  "OUR VISION": "bg-purple-950/70 text-purple-300 border-purple-400/40",
};

export const StatusPill = ({ status, className = "" }) => (
  <span
    data-testid={`status-pill-${status.toLowerCase().replace(/\s+/g, "-")}`}
    className={`inline-flex items-center gap-1.5 border px-2.5 py-0.5 text-[10px] font-mono rounded-full uppercase tracking-[0.18em] ${STYLES[status] || STYLES.COMING} ${className}`}
  >
    <span className="w-1 h-1 rounded-full bg-current" />
    {status}
  </span>
);

export default StatusPill;
