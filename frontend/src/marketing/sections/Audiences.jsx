"use client";

import { Link } from "@/marketing/compat/router";
import { UserRound, Building2, Handshake, Landmark, GraduationCap, ArrowUpRight } from "lucide-react";
import SectionHeader from "@/marketing/components/common/SectionHeader";
import Reveal from "@/marketing/components/common/Reveal";
import { SITE } from "@/marketing/config/site";

const AUDIENCES = [
  {
    icon: UserRound,
    title: "I'm looking for work",
    copy: "Build your Work ID and manage your entire professional journey from one place.",
    href: SITE.pages.jobseekers,
    id: "jobseeker",
  },
  {
    icon: Building2,
    title: "I'm hiring",
    copy: "Turn hiring into a system — from role creation to onboarding and beyond.",
    href: SITE.pages.companies,
    id: "hiring",
  },
  {
    icon: Handshake,
    title: "I'm a recruiter",
    copy: "Work with verified talent through structured, consent-based pipelines.",
    href: SITE.pages.recruiters,
    id: "recruiter",
  },
  {
    icon: Landmark,
    title: "I'm a government / institution",
    copy: "Understand your labour market through privacy-preserving aggregate intelligence.",
    href: SITE.pages.governments,
    id: "government",
  },
  {
    icon: GraduationCap,
    title: "I'm an institution / partner",
    copy: "Issue credentials that travel with people — verifiable, revocable, trusted.",
    href: SITE.pages.institutions,
    id: "institution",
  },
];

export const Audiences = () => (
  <section id="audiences" data-testid="audiences-section" className="relative py-24 sm:py-36 border-t border-white/[0.06]">
    <div className="mx-auto max-w-7xl px-5 sm:px-8">
      <SectionHeader
        index="14"
        eyebrow="Who It Is For"
        title={"FIVE DOORS.\nONE PLATFORM."}
        testId="audiences-header"
      />

      <div className="mt-14 grid sm:grid-cols-2 lg:grid-cols-5 gap-3" data-testid="audiences-grid">
        {AUDIENCES.map((a, i) => (
          <Reveal key={a.id} delay={i * 0.05}>
            <Link
              to={a.href}
              data-testid={`audience-card-${a.id}`}
              className="group flex flex-col h-full card-surface p-6 hover:border-gold/50 hover:bg-gold/[0.03] transition-all duration-300 hover:-translate-y-1"
            >
              <span className="w-11 h-11 rounded-sm border border-gold/30 bg-gold/[0.07] flex items-center justify-center">
                <a.icon className="w-5 h-5 text-gold-soft" />
              </span>
              <h3 className="mt-6 font-display text-lg text-slate-100 leading-snug">{a.title}</h3>
              <p className="mt-3 text-sm text-faint leading-relaxed flex-1">{a.copy}</p>
              <span className="mt-6 inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-gold/70 group-hover:text-gold-soft transition-colors">
                Enter <ArrowUpRight className="w-3.5 h-3.5 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </span>
            </Link>
          </Reveal>
        ))}
      </div>
    </div>
  </section>
);

export default Audiences;
