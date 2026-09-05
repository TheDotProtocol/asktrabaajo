"use client";

import { Mic, FileCheck, ListChecks, UserCheck } from "lucide-react";
import SectionHeader from "@/marketing/components/common/SectionHeader";
import Reveal from "@/marketing/components/common/Reveal";
import { GhostButton } from "@/marketing/components/common/Buttons";
import { scrollToId } from "@/marketing/config/site";

const FEATURES = [
  { icon: ListChecks, title: "Structured screening", copy: "Every candidate answers the same role-relevant core — comparable by design." },
  { icon: Mic, title: "Adaptive questions", copy: "Follow-ups adjust to responses, probing real competency instead of rehearsed answers." },
  { icon: FileCheck, title: "Interview summaries", copy: "Clear, reviewable summaries for hiring teams — evidence, not impressions." },
  { icon: UserCheck, title: "Humans decide", copy: "AI assists the first interview. Final employment decisions stay with people." },
];

const TRANSCRIPT = [
  { speaker: "ATHENA", text: "Walk me through how you would design a rate limiter for a public API.", tone: "gold" },
  { speaker: "CANDIDATE", text: "I'd start with token buckets at the edge, then reconcile centrally for fairness…", tone: "silver" },
  { speaker: "ATHENA", text: "How would you adapt that for a multi-tenant system with strict isolation?", tone: "gold" },
];

export const Interviewer = () => (
  <section id="ai-interviews" data-testid="ai-interviews-section" className="relative py-24 sm:py-36 border-t border-white/[0.06]">
    <div className="mx-auto max-w-7xl px-5 sm:px-8">
      <SectionHeader
        index="06"
        eyebrow="AI Interviews"
        status="OUR VISION"
        title={"THE FIRST INTERVIEW\nCAN BE INTELLIGENT."}
        copy="A future AI interview layer for structured, role-specific first interviews — adaptive questions, competency assessment and clear summaries. No pseudoscience, no 'lie detection', no emotion scoring. Human HR remains in control of every final decision."
        testId="ai-interviews-header"
      />

      <div className="mt-16 grid lg:grid-cols-12 gap-10">
        <div className="lg:col-span-5 space-y-3">
          {FEATURES.map((f, i) => (
            <Reveal key={f.title} delay={i * 0.06}>
              <div className="card-surface p-5 sm:p-6 flex gap-4 hover:border-gold/40 transition-colors duration-300">
                <span className="w-10 h-10 shrink-0 rounded-sm border border-gold/30 bg-gold/[0.07] flex items-center justify-center">
                  <f.icon className="w-[18px] h-[18px] text-gold-soft" />
                </span>
                <div>
                  <h3 className="font-display text-lg text-slate-100">{f.title}</h3>
                  <p className="mt-1 text-sm text-mist leading-relaxed">{f.copy}</p>
                </div>
              </div>
            </Reveal>
          ))}
          <Reveal delay={0.28}>
            <div className="pt-4">
              <GhostButton
                href="#final-cta"
                testId="ai-interviews-cta"
                onClick={(e) => { e.preventDefault(); scrollToId("#final-cta"); }}
              >
                Explore AI Interviews
              </GhostButton>
            </div>
          </Reveal>
        </div>

        <Reveal delay={0.12} className="lg:col-span-7">
          <div className="card-surface overflow-hidden h-full" data-testid="ai-interview-panel">
            <div className="px-6 py-4 border-b border-white/[0.07] flex items-center justify-between">
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-faint">
                Structured interview · concept environment
              </p>
              <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em] text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 node-pulse" />
                Session active
              </span>
            </div>
            <div className="p-6 sm:p-8 space-y-6">
              {TRANSCRIPT.map((t, i) => (
                <div key={i} className="flex gap-4">
                  <span
                    className={`font-mono text-[9px] uppercase tracking-[0.18em] pt-1 w-20 shrink-0 ${
                      t.tone === "gold" ? "text-gold/80" : "text-mist"
                    }`}
                  >
                    {t.speaker}
                  </span>
                  <p className="text-sm sm:text-base text-slate-200 leading-relaxed border-l border-white/10 pl-4">
                    {t.text}
                  </p>
                </div>
              ))}
              <div className="pt-4 border-t border-white/[0.07] grid grid-cols-3 gap-4">
                {["Competency map", "Summary draft", "Bias audit"].map((label) => (
                  <div key={label} className="border border-white/[0.07] bg-white/[0.02] rounded-sm px-3 py-3 text-center">
                    <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-faint">{label}</p>
                    <p className="mt-1.5 font-mono text-[10px] text-gold-soft">REVIEWED BY HUMANS</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </div>
  </section>
);

export default Interviewer;
