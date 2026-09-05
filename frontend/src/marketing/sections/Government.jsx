"use client";

import { ShieldCheck, Landmark, EyeOff } from "lucide-react";
import SectionHeader from "@/marketing/components/common/SectionHeader";
import Reveal from "@/marketing/components/common/Reveal";
import { GhostButton } from "@/marketing/components/common/Buttons";
import { SITE, mailto } from "@/marketing/config/site";

const DRILL = ["COUNTRY", "STATE", "CITY", "INDUSTRY", "SKILL", "WORKFORCE"];

const AGGREGATES = [
  { label: "Total talent", note: "Registered professional identities" },
  { label: "Employed", note: "Currently in employment" },
  { label: "Unemployed", note: "Actively seeking work" },
  { label: "Freelancers", note: "Independent professionals" },
  { label: "Entrepreneurs", note: "Building businesses" },
  { label: "Skill shortages", note: "Demand exceeding supply" },
  { label: "Training needs", note: "Gaps addressable by programs" },
];

const BARS = [
  { label: "Technology", v: 82 },
  { label: "Healthcare", v: 64 },
  { label: "Green Energy", v: 47 },
  { label: "Logistics", v: 58 },
  { label: "Finance", v: 39 },
];

export const Government = () => (
  <section id="government" data-testid="government-section" className="relative py-24 sm:py-36 border-t border-white/[0.06]">
    <div
      className="absolute inset-0"
      aria-hidden="true"
      style={{ background: "linear-gradient(180deg, transparent, rgba(16,18,24,0.6) 30%, rgba(16,18,24,0.6) 70%, transparent)" }}
    />
    <div className="relative mx-auto max-w-7xl px-5 sm:px-8">
      <SectionHeader
        index="08"
        eyebrow="Government & Public Institutions"
        status="OUR VISION"
        title={"SEE THE LABOUR MARKET.\nNOT THE PRIVATE PERSON."}
        copy="The Government Employment Intelligence layer is designed to give public institutions privacy-preserving, aggregate workforce intelligence — skill shortages, employment flows, training needs — without ever exposing individual professional identities."
        testId="government-header"
      />

      <div className="mt-16 grid lg:grid-cols-12 gap-10">
        <div className="lg:col-span-5">
          <Reveal>
            <div className="card-surface p-6 sm:p-8" data-testid="government-drill-panel">
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-faint">Intelligence drill-down</p>
              <div className="mt-5 flex flex-wrap items-center gap-2">
                {DRILL.map((d, i) => (
                  <span key={d} className="flex items-center gap-2">
                    <span className={`font-mono text-[10px] uppercase tracking-[0.18em] border px-3 py-1.5 rounded-sm ${
                      i === DRILL.length - 1 ? "border-gold/50 text-gold-soft bg-gold/[0.07]" : "border-white/10 text-mist"
                    }`}>
                      {d}
                    </span>
                    {i < DRILL.length - 1 && <span className="text-gold/50 font-mono text-xs" aria-hidden="true">→</span>}
                  </span>
                ))}
              </div>
              <ul className="mt-7 space-y-2.5">
                {AGGREGATES.map((a) => (
                  <li key={a.label} className="flex items-baseline justify-between gap-4 border-b border-white/[0.05] pb-2.5">
                    <span className="text-sm text-slate-200">{a.label}</span>
                    <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint text-right">{a.note}</span>
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>

        <div className="lg:col-span-7 space-y-6">
          <Reveal delay={0.08}>
            <div className="card-surface p-6 sm:p-8" data-testid="government-bars-panel">
              <div className="flex items-center justify-between">
                <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-faint">
                  Aggregate skill-shortage signal by industry
                </p>
                <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-amber-400 border border-amber-500/30 bg-amber-950/40 px-2 py-0.5 rounded-full">
                  Illustrative
                </span>
              </div>
              <div className="mt-6 space-y-4">
                {BARS.map((b) => (
                  <div key={b.label}>
                    <div className="flex justify-between mb-1.5">
                      <span className="text-sm text-slate-300">{b.label}</span>
                      <span className="font-mono text-[10px] text-faint">INDEX {b.v}</span>
                    </div>
                    <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-gold-dim via-gold to-gold-soft"
                        style={{ width: `${b.v}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.14}>
            <div className="border border-gold/25 bg-gold/[0.04] rounded-lg p-6 sm:p-8 flex gap-5" data-testid="government-privacy-statement">
              <EyeOff className="w-6 h-6 text-gold-soft shrink-0 mt-1" />
              <div>
                <p className="font-display text-lg sm:text-xl text-slate-100 leading-snug">
                  "AskTrabaajo is designed to provide workforce intelligence without
                  exposing individual professional identities."
                </p>
                <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2">
                  {[
                    { icon: ShieldCheck, t: "Aggregate only" },
                    { icon: Landmark, t: "Institutional governance" },
                  ].map(({ icon: Icon, t }) => (
                    <span key={t} className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em] text-mist">
                      <Icon className="w-3.5 h-3.5 text-gold/70" /> {t}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.2}>
            <GhostButton href={mailto(SITE.contact.government, "Government intelligence enquiry")} testId="government-cta">
              For Governments
            </GhostButton>
          </Reveal>
        </div>
      </div>
    </div>
  </section>
);

export default Government;
