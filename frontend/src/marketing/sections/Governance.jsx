"use client";

import { KeyRound, UserCheck, ScrollText, Scale, ShieldAlert, Gavel, Boxes, EyeOff } from "lucide-react";
import SectionHeader from "@/marketing/components/common/SectionHeader";
import Reveal from "@/marketing/components/common/Reveal";

const PILLARS = [
  { icon: KeyRound, title: "Permissions", copy: "Every access is explicit, scoped and revocable." },
  { icon: UserCheck, title: "Consent", copy: "Data moves only when the person says so." },
  { icon: ScrollText, title: "Audit trails", copy: "Every action is recorded and reviewable." },
  { icon: Scale, title: "Governance", copy: "Clear rules for how the platform is run and changed." },
  { icon: ShieldAlert, title: "Moderation", copy: "Abuse has consequences, not just reports." },
  { icon: Gavel, title: "Enforcement & appeals", copy: "Decisions can be challenged by real humans." },
  { icon: Boxes, title: "Tenant isolation", copy: "Each organization's data stays its own." },
  { icon: EyeOff, title: "Privacy", copy: "Aggregate intelligence never exposes individuals." },
];

export const Governance = () => (
  <section id="governance" data-testid="governance-section" className="relative py-24 sm:py-36 border-t border-white/[0.06]">
    <div className="mx-auto max-w-7xl px-5 sm:px-8">
      <div className="grid lg:grid-cols-12 gap-12">
        <div className="lg:col-span-4">
          <SectionHeader
            index="12"
            eyebrow="Governance & Trust"
            status="LIVE"
            title={"AN EMPLOYMENT PLATFORM\nNEEDS A CONSCIENCE."}
            testId="governance-header"
          />
          <Reveal delay={0.2}>
            <p className="mt-8 font-display text-2xl sm:text-3xl font-light text-gold-grad leading-snug">
              Trust is infrastructure.
            </p>
            <p className="mt-5 text-sm sm:text-base text-mist leading-relaxed">
              These principles govern how AskTrabaajo is designed and built — today,
              not as a future promise.
            </p>
          </Reveal>
        </div>

        <div className="lg:col-span-8 grid sm:grid-cols-2 gap-3" data-testid="governance-grid">
          {PILLARS.map((p, i) => (
            <Reveal key={p.title} delay={i * 0.04}>
              <div className="group card-surface p-5 sm:p-6 h-full hover:border-gold/40 transition-colors duration-300">
                <div className="flex items-center gap-3">
                  <p.icon className="w-4 h-4 text-gold-soft" />
                  <h3 className="font-display text-base sm:text-lg text-slate-100">{p.title}</h3>
                </div>
                <p className="mt-2.5 text-sm text-faint leading-relaxed group-hover:text-mist transition-colors duration-300">
                  {p.copy}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </div>
  </section>
);

export default Governance;
