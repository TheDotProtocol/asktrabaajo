"use client";

import { useState } from "react";
import { GraduationCap, Award, Briefcase, Trophy } from "lucide-react";
import SectionHeader from "@/marketing/components/common/SectionHeader";
import Reveal from "@/marketing/components/common/Reveal";

const CREDENTIALS = [
  { icon: GraduationCap, type: "EDUCATION", title: "B.Sc. Computer Science", issuer: "University partner network", status: "VERIFIED", detail: "Cryptographically attested by the issuing institution. Designed for direct institutional integrations." },
  { icon: Award, type: "CERTIFICATION", title: "Cloud Solutions Architect", issuer: "Certification authority", status: "PENDING", detail: "Verification in progress with the issuing authority. Status updates automatically on resolution." },
  { icon: Briefcase, type: "EMPLOYMENT", title: "Senior Engineer, 4 yrs", issuer: "Employer attestation", status: "VERIFIED", detail: "Employment tenure confirmed through employer-side attestation inside the platform." },
  { icon: Trophy, type: "ACHIEVEMENT", title: "National Design Award", issuer: "Awards body", status: "UNVERIFIED", detail: "Self-declared achievement awaiting third-party confirmation. Clearly labelled as such." },
];

const STATUS_STYLES = {
  VERIFIED: "text-emerald-400 border-emerald-500/40 bg-emerald-950/50",
  PENDING: "text-amber-400 border-amber-500/40 bg-amber-950/50",
  UNVERIFIED: "text-slate-400 border-white/20 bg-white/[0.04]",
  EXPIRED: "text-orange-400 border-orange-500/40 bg-orange-950/50",
  REVOKED: "text-red-400 border-red-500/40 bg-red-950/50",
};

export const Credentials = () => {
  const [open, setOpen] = useState(0);

  return (
    <section id="credentials" data-testid="credentials-section" className="relative py-24 sm:py-36 border-t border-white/[0.06]">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <SectionHeader
          index="10"
          eyebrow="Verified Credentials"
          status="IN DEVELOPMENT"
          title={"TRUST SHOULD TRAVEL\nWITH THE PERSON."}
          copy="AskTrabaajo is designed to support verified professional credentials — education, certifications, employment and achievements — with clear states from VERIFIED to REVOKED. Institutional verification arrives through future integrations; we never claim a credential is verified when it isn't."
          testId="credentials-header"
        />

        <div className="mt-16 grid lg:grid-cols-12 gap-10">
          <div className="lg:col-span-7 space-y-3" data-testid="credentials-list">
            {CREDENTIALS.map((c, i) => (
              <Reveal key={c.title} delay={i * 0.05}>
                <button
                  data-testid={`credential-item-${i}`}
                  onClick={() => setOpen(i)}
                  aria-expanded={open === i}
                  className={`w-full text-left card-surface p-5 sm:p-6 transition-colors duration-300 ${
                    open === i ? "border-gold/40" : "hover:border-white/20"
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <span className="w-11 h-11 shrink-0 rounded-sm border border-white/10 bg-white/[0.03] flex items-center justify-center">
                      <c.icon className="w-5 h-5 text-silver" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-faint">{c.type}</p>
                      <p className="font-display text-base sm:text-lg text-slate-100 truncate">{c.title}</p>
                      <p className="text-xs text-faint">{c.issuer}</p>
                    </div>
                    <span className={`shrink-0 font-mono text-[9px] tracking-[0.16em] border px-2.5 py-1 rounded-full ${STATUS_STYLES[c.status]}`}>
                      {c.status}
                    </span>
                  </div>
                  {open === i && (
                    <p className="mt-4 pt-4 border-t border-white/[0.07] text-sm text-mist leading-relaxed">
                      {c.detail}
                    </p>
                  )}
                </button>
              </Reveal>
            ))}
          </div>

          <Reveal delay={0.15} className="lg:col-span-5">
            <div className="lg:sticky lg:top-28 card-surface p-7 sm:p-9" data-testid="credentials-states-panel">
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-faint">The five states of trust</p>
              <ul className="mt-6 space-y-4">
                {[
                  { s: "VERIFIED", d: "Confirmed by the issuing institution." },
                  { s: "PENDING", d: "Verification requested, in progress." },
                  { s: "UNVERIFIED", d: "Self-declared. Labelled honestly." },
                  { s: "EXPIRED", d: "Was verified; validity period ended." },
                  { s: "REVOKED", d: "Withdrawn by the issuer. Visible, not hidden." },
                ].map((row) => (
                  <li key={row.s} className="flex items-center gap-4">
                    <span className={`w-28 shrink-0 text-center font-mono text-[9px] tracking-[0.16em] border px-2 py-1 rounded-full ${STATUS_STYLES[row.s]}`}>
                      {row.s}
                    </span>
                    <span className="text-sm text-mist">{row.d}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-8 pt-6 border-t border-white/[0.07]">
                <p className="text-sm text-faint leading-relaxed">
                  Designed to support education, certification, employment and achievement
                  records. Universal verification depends on institutional integrations
                  now in development.
                </p>
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
};

export default Credentials;
