"use client";

import SectionHeader from "@/marketing/components/common/SectionHeader";
import Reveal from "@/marketing/components/common/Reveal";

const QUESTIONS = [
  { q: "Where am I?", a: "A precise read of your current skills, credentials and market position." },
  { q: "What can I do?", a: "The roles your profile genuinely qualifies for today — and nearly qualifies for." },
  { q: "Where can I go?", a: "Career paths observed across the Talent Graph, not generic advice." },
  { q: "What do I learn next?", a: "The specific skills that close the gap to your next chapter." },
];

const PATH = [
  { role: "Frontend Developer", stage: "NOW", active: true },
  { role: "Full Stack Engineer", stage: "+ SKILLS", active: false },
  { role: "AI Application Engineer", stage: "+ SPECIALISATION", active: false },
  { role: "Product Engineer", stage: "TRAJECTORY", active: false },
];

export const CareerAdvisor = () => (
  <section id="career-advisor" data-testid="career-advisor-section" className="relative py-24 sm:py-36 border-t border-white/[0.06]">
    <div className="mx-auto max-w-7xl px-5 sm:px-8">
      <SectionHeader
        index="07"
        eyebrow="Career Advisor"
        title={"YOUR NEXT CAREER MOVE\nSHOULD NOT BE A GUESS."}
        copy="Career Advisor uses Work ID, skills, opportunities and career pathways so people can see where they are, what they can do, where they can go — and what to learn next. Guidance, never promises."
        testId="career-advisor-header"
      />

      <div className="mt-16 grid lg:grid-cols-12 gap-10">
        <div className="lg:col-span-5 grid sm:grid-cols-2 lg:grid-cols-1 gap-3">
          {QUESTIONS.map((item, i) => (
            <Reveal key={item.q} delay={i * 0.06}>
              <div className="card-surface p-5 sm:p-6 hover:border-gold/40 transition-colors duration-300">
                <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-gold/80">{item.q}</p>
                <p className="mt-2 text-sm text-mist leading-relaxed">{item.a}</p>
              </div>
            </Reveal>
          ))}
        </div>

        <Reveal delay={0.12} className="lg:col-span-7">
          <div className="card-surface p-6 sm:p-10 h-full flex flex-col" data-testid="career-path-panel">
            <div className="flex items-center justify-between">
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-faint">
                Example trajectory · illustrative
              </p>
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-gold/70">Engineering</span>
            </div>

            <div className="mt-10 flex-1 flex flex-col justify-center">
              <div className="relative">
                <div className="absolute left-[19px] top-4 bottom-4 w-px bg-gradient-to-b from-gold/60 via-white/15 to-transparent sm:hidden" aria-hidden="true" />
                <div className="hidden sm:block absolute top-[19px] left-8 right-8 h-px bg-gradient-to-r from-gold/60 via-white/15 to-white/5" aria-hidden="true" />
                <ol className="relative flex flex-col sm:flex-row sm:items-start gap-8 sm:gap-0">
                  {PATH.map((p, i) => (
                    <li key={p.role} className="flex sm:flex-col items-start sm:items-center gap-4 sm:gap-0 sm:flex-1" data-testid={`career-path-step-${i}`}>
                      <span
                        className={`w-10 h-10 shrink-0 rounded-full border flex items-center justify-center font-mono text-xs ${
                          p.active
                            ? "border-gold bg-gold/15 text-gold-soft shadow-[0_0_24px_rgba(212,175,55,0.25)]"
                            : "border-white/15 bg-coal text-faint"
                        }`}
                      >
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <div className="sm:mt-5 sm:text-center">
                        <p className={`font-display text-base sm:text-lg ${p.active ? "text-slate-100" : "text-mist"}`}>{p.role}</p>
                        <p className="font-mono text-[9px] uppercase tracking-[0.18em] text-faint mt-1">{p.stage}</p>
                      </div>
                    </li>
                  ))}
                </ol>
              </div>
            </div>

            <p className="mt-10 pt-6 border-t border-white/[0.07] text-sm text-faint leading-relaxed">
              Career Advisor shows possibilities and pathways observed in the market.
              It does not — and cannot — guarantee employment outcomes.
            </p>
          </div>
        </Reveal>
      </div>
    </div>
  </section>
);

export default CareerAdvisor;
