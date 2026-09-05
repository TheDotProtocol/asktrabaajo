"use client";

import SectionHeader from "@/marketing/components/common/SectionHeader";
import Reveal from "@/marketing/components/common/Reveal";
import StatusPill from "@/marketing/components/common/StatusPill";

const RING_INNER = ["WORK ID", "TALENT GRAPH", "ATHENA", "COMPANY OS"];
const RING_OUTER = [
  "OPPORTUNITIES", "COMMUNICATION", "AI INTERVIEWS", "CREDENTIALS",
  "CAREER ADVISOR", "GOVERNANCE", "GOV. INTELLIGENCE", "PAYMENTS",
];

const LEGEND = [
  { name: "Work ID", status: "IN DEVELOPMENT" },
  { name: "Talent Graph", status: "IN DEVELOPMENT" },
  { name: "Athena AI", status: "OUR VISION" },
  { name: "Company OS", status: "IN DEVELOPMENT" },
  { name: "Opportunities", status: "COMING" },
  { name: "Communication", status: "IN DEVELOPMENT" },
  { name: "AI Interviews", status: "OUR VISION" },
  { name: "Credentials", status: "IN DEVELOPMENT" },
  { name: "Career Advisor", status: "OUR VISION" },
  { name: "Governance", status: "LIVE" },
  { name: "Gov. Intelligence", status: "OUR VISION" },
  { name: "Payments", status: "COMING" },
];

const ringNodes = (items, radiusPct, duration, reverse) =>
  items.map((label, i) => {
    const angle = (i / items.length) * 360;
    const rad = ((angle - 90) * Math.PI) / 180;
    const x = 50 + radiusPct * Math.cos(rad);
    const y = 50 + radiusPct * Math.sin(rad);
    return (
      <span
        key={label}
        className="absolute -translate-x-1/2 -translate-y-1/2"
        style={{ left: `${x}%`, top: `${y}%` }}
      >
        <span
          className="hidden sm:block font-mono text-[8px] sm:text-[9px] uppercase tracking-[0.16em] text-slate-300 border border-white/15 bg-ink/90 px-2 py-1 rounded-sm whitespace-nowrap"
          style={{ animation: `spin-slow ${duration}s linear infinite ${reverse ? "reverse" : ""}` }}
        >
          {label}
        </span>
        <span className="block sm:hidden w-1.5 h-1.5 rounded-full bg-gold/70" />
      </span>
    );
  });

export const Ecosystem = () => {
  return (
    <section id="ecosystem" data-testid="ecosystem-section" className="relative py-24 sm:py-36 border-t border-white/[0.06] overflow-hidden">
      <div
        className="absolute inset-0"
        aria-hidden="true"
        style={{ background: "radial-gradient(ellipse 50% 45% at 50% 50%, rgba(212,175,55,0.06), transparent 70%)" }}
      />
      <div className="relative mx-auto max-w-7xl px-5 sm:px-8">
        <SectionHeader
          index="13"
          eyebrow="The AskTrabaajo Ecosystem"
          status="OUR VISION"
          title={"ONE SYSTEM.\nEVERY PART OF WORK."}
          copy="Twelve capabilities orbiting one core — designed as a single coherent universe, not a bundle of features."
          align="center"
          testId="ecosystem-header"
        />

        <div className="mt-16 grid lg:grid-cols-12 gap-12 items-center">
          <Reveal className="lg:col-span-7">
            <div className="relative mx-auto aspect-square max-w-[560px]" data-testid="ecosystem-orbital" aria-hidden="true">
              <div className="absolute inset-0 rounded-full border border-white/[0.07]" />
              <div className="absolute inset-[16%] rounded-full border border-white/[0.09]" />
              <div className="absolute inset-[32%] rounded-full border border-gold/20" />
              <div className="absolute inset-0 orbit-spin-rev">
                {ringNodes(RING_OUTER, 48, 120, false)}
              </div>
              <div className="absolute inset-0 orbit-spin">
                {ringNodes(RING_INNER, 31, 90, true)}
              </div>
              <div className="absolute inset-[38%] rounded-full border border-gold/40 bg-ink flex flex-col items-center justify-center shadow-[0_0_60px_rgba(212,175,55,0.12)]">
                <img src="/brand/asktrabaajo-logo.webp" alt="" className="w-2/3 brightness-110" />
              </div>
            </div>
          </Reveal>

          <div className="lg:col-span-5 grid grid-cols-2 gap-2.5" data-testid="ecosystem-legend">
            {LEGEND.map((l, i) => (
              <Reveal key={l.name} delay={i * 0.03}>
                <div className="flex flex-col gap-1.5 border border-white/[0.07] bg-white/[0.02] rounded-sm px-3.5 py-3 hover:border-gold/30 transition-colors duration-300">
                  <span className="text-xs sm:text-sm text-slate-200">{l.name}</span>
                  <StatusPill status={l.status} className="!px-2 !py-0 !text-[8px] self-start" />
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default Ecosystem;
