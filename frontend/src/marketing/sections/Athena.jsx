"use client";

import { useEffect, useRef, useState } from "react";
import { Sparkles } from "lucide-react";
import SectionHeader from "@/marketing/components/common/SectionHeader";
import Reveal from "@/marketing/components/common/Reveal";

const EXCHANGES = [
  { who: "JOBSEEKER", q: "Find me the next big career opportunity.", a: "Analysing your Work ID, skills and the Talent Graph to surface paths with real momentum." },
  { who: "EMPLOYER", q: "Find five candidates for this role.", a: "Matching role requirements against verified skills, credentials and availability — with consent." },
  { who: "HR TEAM", q: "Show me today's interview pipeline.", a: "Compiling scheduled interviews, pending feedback and offer stages into one view." },
  { who: "CANDIDATE", q: "What's happening with my application?", a: "Retrieving your application status and every step still ahead — no more black boxes." },
  { who: "CAREER", q: "What should I learn next?", a: "Comparing your trajectory against emerging demand to suggest the highest-leverage skill." },
  { who: "GOVERNMENT", q: "Where are the biggest technology skill shortages?", a: "Aggregating anonymised, privacy-preserving labour market signals by region and industry." },
];

const AthenaPanel = () => {
  const [idx, setIdx] = useState(0);
  const [typed, setTyped] = useState(0);
  const [phase, setPhase] = useState("typing");
  const timer = useRef(null);

  useEffect(() => {
    const ex = EXCHANGES[idx];
    if (phase === "typing") {
      if (typed < ex.q.length) {
        timer.current = setTimeout(() => setTyped((t) => t + 1), 34);
      } else {
        timer.current = setTimeout(() => setPhase("answer"), 500);
      }
    } else if (phase === "answer") {
      timer.current = setTimeout(() => setPhase("hold"), 700);
    } else {
      timer.current = setTimeout(() => {
        setIdx((i) => (i + 1) % EXCHANGES.length);
        setTyped(0);
        setPhase("typing");
      }, 3400);
    }
    return () => clearTimeout(timer.current);
  }, [idx, typed, phase]);

  const ex = EXCHANGES[idx];

  return (
    <div
      data-testid="athena-panel"
      className="card-surface overflow-hidden shadow-[0_40px_100px_-30px_rgba(0,0,0,0.9)]"
    >
      <div className="flex items-center justify-between px-5 sm:px-6 py-4 border-b border-white/[0.07]">
        <div className="flex items-center gap-3">
          <span className="w-8 h-8 rounded-sm border border-gold/40 bg-gold/[0.08] flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-gold-soft" />
          </span>
          <div>
            <p className="font-display text-sm tracking-[0.18em] text-slate-100">ATHENA</p>
            <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-faint">AskTrabaajo AI layer · live interface</p>
          </div>
        </div>
        <div className="flex gap-1.5" aria-hidden="true">
          <span className="w-2 h-2 rounded-full bg-white/15" />
          <span className="w-2 h-2 rounded-full bg-white/15" />
          <span className="w-2 h-2 rounded-full bg-gold/60" />
        </div>
      </div>

      <div className="px-5 sm:px-6 py-6 min-h-[220px] sm:min-h-[240px]">
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-gold/80">{ex.who}</p>
        <p className="mt-3 font-display text-lg sm:text-xl text-slate-100 leading-snug" data-testid="athena-question">
          {ex.q.slice(0, typed)}
          <span className="caret-blink text-gold" aria-hidden="true">▍</span>
        </p>
        <div
          className={`mt-5 transition-opacity duration-700 ${phase === "typing" ? "opacity-0" : "opacity-100"}`}
          aria-live="polite"
        >
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-faint">Athena</p>
          <p className="mt-2 text-sm sm:text-base text-mist leading-relaxed">{ex.a}</p>
        </div>
      </div>

      <div className="px-5 sm:px-6 py-4 border-t border-white/[0.07] flex flex-wrap gap-2">
        {EXCHANGES.map((e, i) => (
          <button
            key={e.who}
            data-testid={`athena-persona-${e.who.toLowerCase().replace(/\s+/g, "-")}`}
            onClick={() => { setIdx(i); setTyped(0); setPhase("typing"); }}
            aria-pressed={idx === i}
            className={`font-mono text-[9px] uppercase tracking-[0.16em] px-2.5 py-1 rounded-full border transition-colors duration-300 ${
              idx === i ? "border-gold/50 text-gold-soft" : "border-white/10 text-faint hover:text-mist"
            }`}
          >
            {e.who}
          </button>
        ))}
      </div>
    </div>
  );
};

export const Athena = () => (
  <section id="athena" data-testid="athena-section" className="relative py-24 sm:py-36 border-t border-white/[0.06] overflow-hidden">
    <div
      className="absolute inset-0"
      aria-hidden="true"
      style={{ background: "radial-gradient(ellipse 60% 50% at 30% 50%, rgba(212,175,55,0.06), transparent 70%)" }}
    />
    <div className="relative mx-auto max-w-7xl px-5 sm:px-8">
      <div className="grid lg:grid-cols-2 gap-16 items-center">
        <div className="order-2 lg:order-1">
          <Reveal>
            <AthenaPanel />
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-5 font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
              Examples of how Athena is used. Live answers come from the platform after you sign in.
            </p>
          </Reveal>
        </div>
        <div className="order-1 lg:order-2">
          <SectionHeader
            index="05"
            eyebrow="Trabaajo / Athena"
            title={"INTELLIGENCE FOR\nTHE WORLD OF WORK."}
            copy="Athena is AskTrabaajo's intelligent interface — a conversational layer into the employment operating system. Jobseekers, employers and government users ask in natural language. Athena works through controlled platform tools, permissions and consent."
            testId="athena-header"
          />
          <Reveal delay={0.2}>
            <ul className="mt-8 space-y-3">
              {[
                "Natural language access to the whole platform",
                "Controlled tools — never unbounded automation",
                "Context from Work ID, the Talent Graph and pipelines",
              ].map((t) => (
                <li key={t} className="flex items-center gap-3 text-sm text-mist">
                  <span className="w-1.5 h-1.5 rotate-45 bg-gold/60 shrink-0" aria-hidden="true" />
                  {t}
                </li>
              ))}
            </ul>
          </Reveal>
        </div>
      </div>
    </div>
  </section>
);

export default Athena;
