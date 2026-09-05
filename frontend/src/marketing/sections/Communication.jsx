"use client";

import { Send, MessageSquare, CalendarClock, FileSignature, BellRing } from "lucide-react";
import SectionHeader from "@/marketing/components/common/SectionHeader";
import Reveal from "@/marketing/components/common/Reveal";

const FLOW = [
  { icon: Send, label: "Outreach", note: "Employer initiates — identity protected until consent." },
  { icon: MessageSquare, label: "Messages", note: "Structured conversation, inside the platform." },
  { icon: CalendarClock, label: "Interviews", note: "Scheduled and run as part of the same thread." },
  { icon: FileSignature, label: "Offers", note: "Documents and signatures in one place." },
  { icon: BellRing, label: "Notifications", note: "Every state change visible to both sides." },
];

export const Communication = () => (
  <section id="communication" data-testid="communication-section" className="relative py-24 sm:py-36 border-t border-white/[0.06]">
    <div className="mx-auto max-w-7xl px-5 sm:px-8">
      <SectionHeader
        index="11"
        eyebrow="Communication Layer"
        title={"THE CONVERSATION BETWEEN\nTALENT AND EMPLOYERS."}
        copy="AskTrabaajo provides a controlled communication layer: Company → AskTrabaajo → Candidate. Outreach, messages, interviews, offers and notifications run as one continuous workflow without unnecessary exposure of private contact details."
        testId="communication-header"
      />

      <Reveal delay={0.15}>
        <div className="mt-16 card-surface p-6 sm:p-10" data-testid="communication-flow">
          <div className="flex items-center justify-between gap-4 font-mono text-[10px] uppercase tracking-[0.2em]">
            <span className="text-slate-200">Company</span>
            <span className="flex-1 h-px bg-gradient-to-r from-white/20 via-gold/50 to-white/20" aria-hidden="true" />
            <span className="text-gold-soft">AskTrabaajo</span>
            <span className="flex-1 h-px bg-gradient-to-r from-white/20 via-gold/50 to-white/20" aria-hidden="true" />
            <span className="text-slate-200">Candidate</span>
          </div>

          <ol className="mt-10 grid sm:grid-cols-5 gap-4">
            {FLOW.map((f, i) => (
              <li
                key={f.label}
                data-testid={`communication-step-${f.label.toLowerCase()}`}
                className="group border border-white/[0.07] bg-white/[0.02] rounded-md p-5 hover:border-gold/40 hover:bg-gold/[0.04] transition-colors duration-300"
              >
                <span className="w-9 h-9 rounded-sm border border-gold/30 bg-gold/[0.07] flex items-center justify-center">
                  <f.icon className="w-4 h-4 text-gold-soft" />
                </span>
                <p className="mt-4 font-display text-base text-slate-100">{f.label}</p>
                <p className="mt-1.5 text-xs text-faint leading-relaxed">{f.note}</p>
                <span className="mt-3 block font-mono text-[9px] tracking-[0.2em] text-faint">{String(i + 1).padStart(2, "0")}</span>
              </li>
            ))}
          </ol>

          <p className="mt-8 font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
            One thread. Zero leaked contact details. Full audit trail.
          </p>
        </div>
      </Reveal>
    </div>
  </section>
);

export default Communication;
