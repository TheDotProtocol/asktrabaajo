"use client";

import Reveal from "./Reveal";
import StatusPill from "./StatusPill";

export const SectionHeader = ({ index, eyebrow, title, copy, status, align = "left", testId }) => (
  <div className={`max-w-3xl ${align === "center" ? "mx-auto text-center" : ""}`} data-testid={testId}>
    <Reveal>
      <div className={`flex items-center gap-4 ${align === "center" ? "justify-center" : ""}`}>
        {index && (
          <span className="font-mono text-[11px] tracking-[0.28em] text-faint">{index}</span>
        )}
        <span className="h-px w-10 bg-gold/40" aria-hidden="true" />
        <span className="eyebrow">{eyebrow}</span>
        {status && <StatusPill status={status} />}
      </div>
    </Reveal>
    <Reveal delay={0.08}>
      <h2 className="mt-6 font-display text-3xl sm:text-4xl lg:text-5xl font-semibold tracking-tight leading-[1.08] text-silver-grad whitespace-pre-line">
        {title}
      </h2>
    </Reveal>
    {copy && (
      <Reveal delay={0.16}>
        <p className={`mt-6 text-base sm:text-lg text-mist leading-relaxed max-w-2xl ${align === "center" ? "mx-auto" : ""}`}>
          {copy}
        </p>
      </Reveal>
    )}
  </div>
);

export default SectionHeader;
