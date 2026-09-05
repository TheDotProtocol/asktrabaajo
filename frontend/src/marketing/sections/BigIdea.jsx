"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import SectionHeader from "@/marketing/components/common/SectionHeader";
import Reveal from "@/marketing/components/common/Reveal";

const STAGES = [
  { n: "01", name: "Discover", copy: "Opportunities mapped to who you actually are — not just keywords." },
  { n: "02", name: "Match", copy: "The Talent Graph aligns people, skills and roles with precision." },
  { n: "03", name: "Apply", copy: "One persistent identity. No re-typing your life into every portal." },
  { n: "04", name: "Interview", copy: "Structured, intelligent first interviews. Humans decide." },
  { n: "05", name: "Offer", copy: "Offers, documents and signatures in one controlled channel." },
  { n: "06", name: "Onboard", copy: "From accepted offer to productive first day, without chaos." },
  { n: "07", name: "Work", copy: "Employment records that stay accurate and stay yours." },
  { n: "08", name: "Learn", copy: "Skill gaps become learning paths, not dead ends." },
  { n: "09", name: "Grow", copy: "Career moves become deliberate, guided by evidence." },
  { n: "10", name: "Next Opportunity", copy: "The journey loops — smarter every time." },
];

export const BigIdea = () => {
  const [active, setActive] = useState(0);

  return (
    <section id="big-idea" data-testid="big-idea-section" className="relative py-24 sm:py-36">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <SectionHeader
          index="01"
          eyebrow="The Big Idea"
          title={"WE DIDN'T BUILD\nANOTHER JOB BOARD."}
          copy="Traditional platforms fight over a single moment — the application. We're building the infrastructure around the entire journey through work: every transition, every credential, every next chapter."
          testId="big-idea-header"
        />

        <div className="mt-16 grid lg:grid-cols-12 gap-10">
          <Reveal className="lg:col-span-5">
            <div className="lg:sticky lg:top-28">
              <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-faint">
                The journey, as one system
              </p>
              <div className="mt-6 card-surface p-7 sm:p-9" data-testid="journey-active-panel">
                <span className="font-mono text-xs text-gold tracking-[0.2em]">{STAGES[active].n}</span>
                <h3 className="mt-3 font-display text-2xl sm:text-3xl font-semibold text-slate-100">
                  {STAGES[active].name}
                </h3>
                <p className="mt-4 text-mist leading-relaxed">{STAGES[active].copy}</p>
                <div className="mt-8 h-px bg-gradient-to-r from-gold/50 via-gold/10 to-transparent" />
                <p className="mt-5 text-sm text-faint leading-relaxed">
                  One platform. One identity. Every stage connected — so nothing
                  about your professional life is lost between systems.
                </p>
              </div>
            </div>
          </Reveal>

          <div className="lg:col-span-7">
            <ol className="relative border-l border-white/[0.08] ml-3" data-testid="journey-steps-list">
              {STAGES.map((s, i) => (
                <Reveal key={s.n} delay={i * 0.04}>
                  <li>
                    <button
                      data-testid={`journey-step-${s.n}`}
                      onMouseEnter={() => setActive(i)}
                      onFocus={() => setActive(i)}
                      onClick={() => setActive(i)}
                      className={`group relative w-full text-left flex items-baseline gap-5 pl-8 py-4 transition-colors duration-300 ${
                        active === i ? "text-slate-100" : "text-faint hover:text-mist"
                      }`}
                      aria-current={active === i ? "step" : undefined}
                    >
                      <span
                        className={`absolute -left-[5px] top-1/2 -translate-y-1/2 w-2.5 h-2.5 rotate-45 transition-colors duration-300 ${
                          active === i ? "bg-gold" : "bg-white/15 group-hover:bg-white/30"
                        }`}
                        aria-hidden="true"
                      />
                      <span className="font-mono text-xs tracking-[0.2em] text-faint w-7 shrink-0">{s.n}</span>
                      <span
                        className={`font-display text-xl sm:text-2xl tracking-wide transition-colors duration-300 ${
                          active === i ? "text-gold-grad font-semibold" : "font-light"
                        }`}
                      >
                        {s.name}
                      </span>
                      {active === i && (
                        <motion.span
                          layoutId="journey-active-line"
                          className="absolute left-8 right-0 bottom-0 h-px bg-gold/30"
                          aria-hidden="true"
                        />
                      )}
                    </button>
                  </li>
                </Reveal>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </section>
  );
};

export default BigIdea;
