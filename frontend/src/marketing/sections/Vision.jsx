"use client";

import SectionHeader from "@/marketing/components/common/SectionHeader";
import Reveal from "@/marketing/components/common/Reveal";

const LEGACY = [
  "One moment: the application",
  "Resumes re-entered everywhere",
  "Keyword matching",
  "Black-box application status",
  "Your data, their platform",
  "Hiring ends at the offer",
];

const ASKTRABAAJO = [
  "The entire journey through work",
  "One persistent Work ID",
  "A living Talent Graph",
  "Every step visible, by design",
  "Consent-controlled disclosure",
  "Onboarding, growth and what's next",
];

export const Vision = () => (
  <section id="vision" data-testid="vision-section" className="relative py-24 sm:py-36 border-t border-white/[0.06]">
    <div className="mx-auto max-w-7xl px-5 sm:px-8">
      <SectionHeader
        index="15"
        eyebrow="The Vision"
        status="OUR VISION"
        title={"THE NEXT EMPLOYMENT\nINFRASTRUCTURE."}
        copy="Our ambition is an interoperable employment layer across industries and geographies. We are building toward it deliberately — capability by capability, integration by integration. This is the goal, not a claim about today."
        testId="vision-header"
      />

      <Reveal delay={0.15}>
        <div className="mt-16 grid md:grid-cols-2 gap-3" data-testid="vision-comparison">
          <div className="card-surface p-7 sm:p-9">
            <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-faint">Legacy job platforms</p>
            <ul className="mt-7 space-y-4">
              {LEGACY.map((t) => (
                <li key={t} className="flex items-center gap-4 text-sm sm:text-base text-faint">
                  <span className="w-1.5 h-1.5 rotate-45 bg-white/20 shrink-0" aria-hidden="true" />
                  {t}
                </li>
              ))}
            </ul>
          </div>
          <div className="relative card-surface p-7 sm:p-9 border-gold/30 overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-gold/70 to-transparent" aria-hidden="true" />
            <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-gold/90">The AskTrabaajo OS</p>
            <ul className="mt-7 space-y-4">
              {ASKTRABAAJO.map((t) => (
                <li key={t} className="flex items-center gap-4 text-sm sm:text-base text-slate-200">
                  <span className="w-1.5 h-1.5 rotate-45 bg-gold shrink-0" aria-hidden="true" />
                  {t}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Reveal>
    </div>
  </section>
);

export default Vision;
