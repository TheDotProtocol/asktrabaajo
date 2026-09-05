"use client";

import { Building2, Users, FileText, CalendarCheck, BadgeCheck, Rocket } from "lucide-react";
import SectionHeader from "@/marketing/components/common/SectionHeader";
import Reveal from "@/marketing/components/common/Reveal";
import { GhostButton } from "@/marketing/components/common/Buttons";
import { scrollToId } from "@/marketing/config/site";

const PIPELINE = [
  { icon: Building2, name: "Create Role", note: "Structured role definitions with real skill requirements." },
  { icon: Users, name: "Discover Talent", note: "Graph-based matching, not keyword roulette." },
  { icon: FileText, name: "Screen", note: "Credential-aware screening with consent built in." },
  { icon: CalendarCheck, name: "Interview", note: "Structured interviews, scheduled in one workflow." },
  { icon: BadgeCheck, name: "Offer", note: "Offers, documents and signatures in one channel." },
  { icon: Rocket, name: "Onboard", note: "From accepted offer to first day, seamlessly." },
];

const CAPABILITIES = [
  "Organizations & teams", "Jobs & pipelines", "Candidates & applications",
  "Outreach & messaging", "Interviews & scheduling", "Document requests",
  "Offers & contracts", "Employment workflows",
];

export const CompanyOS = () => (
  <section id="company-os" data-testid="company-os-section" className="relative py-24 sm:py-36 border-t border-white/[0.06]">
    <div className="mx-auto max-w-7xl px-5 sm:px-8">
      <div className="grid lg:grid-cols-2 gap-16">
        <div>
          <SectionHeader
            index="04"
            eyebrow="For Companies & HR"
            title={"HIRING BECOMES\nA SYSTEM."}
            copy="Employer OS is the operating system for hiring — organizations, jobs, Talent Graph discovery, pipelines, outreach, AI interviews, offers, onboarding, analytics and billing — as one coherent system instead of twelve disconnected tools."
            testId="company-os-header"
          />
          <Reveal delay={0.2}>
            <div className="mt-8 flex flex-wrap gap-2" data-testid="company-os-capabilities">
              {CAPABILITIES.map((c) => (
                <span key={c} className="font-mono text-[10px] uppercase tracking-[0.16em] text-mist border border-white/10 bg-white/[0.03] px-3 py-1.5 rounded-sm">
                  {c}
                </span>
              ))}
            </div>
          </Reveal>
          <Reveal delay={0.26}>
            <div className="mt-10">
              <GhostButton
                href="#audiences"
                testId="company-os-cta"
                onClick={(e) => { e.preventDefault(); scrollToId("#audiences"); }}
              >
                For Companies
              </GhostButton>
            </div>
          </Reveal>
        </div>

        <div className="relative">
          <div
            className="absolute inset-0 -z-10"
            aria-hidden="true"
            style={{ background: "radial-gradient(ellipse 55% 45% at 60% 40%, rgba(212,175,55,0.07), transparent 70%)" }}
          />
          <ol className="space-y-3" data-testid="company-os-pipeline">
            {PIPELINE.map((step, i) => (
              <Reveal key={step.name} delay={i * 0.06}>
                <li className="group card-surface flex items-center gap-5 px-5 sm:px-6 py-4 hover:border-gold/40 transition-colors duration-300">
                  <span className="font-mono text-xs text-faint w-6 shrink-0">{String(i + 1).padStart(2, "0")}</span>
                  <span className="w-10 h-10 shrink-0 rounded-sm border border-gold/30 bg-gold/[0.07] flex items-center justify-center">
                    <step.icon className="w-[18px] h-[18px] text-gold-soft" />
                  </span>
                  <div className="min-w-0">
                    <p className="font-display text-base sm:text-lg text-slate-100 tracking-wide">{step.name}</p>
                    <p className="text-sm text-faint truncate">{step.note}</p>
                  </div>
                  <span className="ml-auto h-px flex-1 max-w-16 bg-gradient-to-r from-gold/40 to-transparent hidden sm:block" aria-hidden="true" />
                </li>
              </Reveal>
            ))}
          </ol>
        </div>
      </div>
    </div>
  </section>
);

export default CompanyOS;
