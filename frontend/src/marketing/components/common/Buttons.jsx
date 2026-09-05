"use client";

import { ArrowUpRight } from "lucide-react";

export const GoldButton = ({ children, href, onClick, testId, className = "" }) => (
  <a
    href={href}
    onClick={onClick}
    data-testid={testId}
    className={`group relative inline-flex items-center gap-2.5 bg-gold text-ink font-display font-semibold text-sm tracking-wide px-7 py-3.5 rounded-sm overflow-hidden transition-transform duration-300 hover:-translate-y-0.5 ${className}`}
  >
    <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent -translate-x-[140%] group-hover:translate-x-[140%] transition-transform duration-700 ease-out" aria-hidden="true" />
    <span className="relative">{children}</span>
    <ArrowUpRight className="relative w-4 h-4 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
  </a>
);

export const GhostButton = ({ children, href, onClick, testId, className = "" }) => (
  <a
    href={href}
    onClick={onClick}
    data-testid={testId}
    className={`group inline-flex items-center gap-2.5 border border-white/20 text-slate-200 font-display font-medium text-sm tracking-wide px-7 py-3.5 rounded-sm transition-colors duration-300 hover:border-gold/60 hover:text-gold-soft ${className}`}
  >
    {children}
    <ArrowUpRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
  </a>
);
