"use client";

import { Link } from "@/marketing/compat/router";
import Reveal from "@/marketing/components/common/Reveal";
import { GoldButton, GhostButton } from "@/marketing/components/common/Buttons";
import { PublicPage, PageHero } from "@/marketing/components/common/PublicPage";
import { usePageMeta } from "@/marketing/hooks/usePageMeta";
import { SITE } from "@/marketing/config/site";

const CHAPTERS = [
  { n: "I", text: "A job is one moment." },
  { n: "II", text: "A career is a journey." },
  { n: "III", text: "Employment is an ecosystem." },
];

const PLATFORM = [
  { title: "Jobseeker OS", copy: "The operating system for a professional life — Work ID, documents, credentials, Work DNA, assessments, career, learning, opportunities, applications, interviews, offers and communications." },
  { title: "Employer / Job Giver OS", copy: "The operating system for hiring — company profile, jobs, talent discovery, pipeline, AI interviews, outreach, offers, onboarding, analytics, billing and workforce operations." },
  { title: "Government Workforce Intelligence", copy: "Privacy-preserving, aggregate intelligence across workforce, skills, geography, industries, opportunities, companies and reports. Governments see the market, never the private person." },
  { title: "Work ID", copy: "The professional identity layer — a persistent record of history, skills, credentials and consent-controlled disclosure." },
  { title: "Athena", copy: "Intelligence for the world of work — a conversational interface across Jobseeker, Employer and Government, through controlled platform tools." },
  { title: "Talent Graph", copy: "Connects people, skills, opportunities, companies and career pathways so matching is comprehension, not keyword search." },
  { title: "Recruiter Network", copy: "Independent recruiters work with verified talent, consent-based outreach, shared pipelines and a portable professional reputation." },
  { title: "Institutional Credentials", copy: "Education, certifications, employment and achievements issued to Work ID — with explicit states from VERIFIED to REVOKED." },
  { title: "AI Interview & Career Advisor", copy: "Structured first interviews and career guidance across pathways, skill gaps and professional development — humans remain in control of decisions." },
  { title: "Communications, Commerce & Governance", copy: "Controlled messaging, offers, billing, permissions, audit, enforcement and appeals — trust as infrastructure for the employment journey." },
];

export const AboutPage = () => {
  usePageMeta({
    title: "About",
    description:
      "AskTrabaajo is the operating system for the world of work — connecting jobseekers, employers, recruiters, institutions and government through one Work ID, Talent Graph and Athena.",
  });

  return (
    <PublicPage testId="about-page">
      <PageHero
        eyebrow="About AskTrabaajo"
        title={"THE OPERATING SYSTEM\nFOR THE WORLD OF WORK."}
        copy="AskTrabaajo is the operating system for the world of work. One platform for professional identity, hiring, recruiter networks, institutional credentials, career intelligence and privacy-preserving government workforce insight."
      >
        <div className="mt-10 flex flex-wrap items-center gap-4">
          <GoldButton href={SITE.urls.app} testId="about-enter-cta">
            Enter AskTrabaajo
          </GoldButton>
          <GhostButton href={SITE.pages.contact} testId="about-contact-cta">
            Contact
          </GhostButton>
        </div>
      </PageHero>

      <section className="py-20 sm:py-28 border-t border-white/[0.06]">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <Reveal>
            <h2 className="font-display text-2xl sm:text-4xl font-semibold tracking-tight text-silver-grad">
              Work is more than a job.
            </h2>
          </Reveal>
          <div className="mt-12 space-y-8 max-w-3xl">
            {CHAPTERS.map((c, i) => (
              <Reveal key={c.n} delay={i * 0.06}>
                <div className="flex items-baseline gap-6 sm:gap-10 border-b border-white/[0.07] pb-8">
                  <span className="font-display text-2xl text-gold/70 font-light shrink-0 w-12">{c.n}.</span>
                  <p className="font-display text-2xl sm:text-3xl font-light text-slate-200 leading-snug">{c.text}</p>
                </div>
              </Reveal>
            ))}
          </div>
          <Reveal delay={0.15}>
            <p className="mt-12 max-w-2xl text-base sm:text-lg text-mist leading-relaxed">
              Traditional platforms fight over a single moment — the application.
              AskTrabaajo is the layer around the entire journey: every transition,
              every credential, every next chapter.
            </p>
          </Reveal>
        </div>
      </section>

      <section className="py-20 sm:py-28 border-t border-white/[0.06]">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <Reveal>
            <h2 className="font-display text-2xl sm:text-3xl font-semibold text-silver-grad">
              The AskTrabaajo platform
            </h2>
          </Reveal>
          <ul className="mt-10 grid sm:grid-cols-2 gap-5">
            {PLATFORM.map((item) => (
              <li key={item.title} className="card-surface p-5">
                <p className="font-display text-lg text-slate-100">{item.title}</p>
                <p className="mt-2 text-sm text-mist leading-relaxed">{item.copy}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="py-20 sm:py-28 border-t border-white/[0.06]">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <Reveal>
            <div className="border border-gold/25 bg-gold/[0.04] rounded-lg p-8 sm:p-12">
              <p className="font-display text-xl sm:text-3xl font-light text-slate-100 leading-snug max-w-4xl">
                Trust is infrastructure. AskTrabaajo is designed so people decide
                what is shared, with whom, and when — always.
              </p>
              <div className="mt-8 flex flex-wrap gap-4">
                <Link
                  to={SITE.pages.privacy}
                  className="font-mono text-[11px] uppercase tracking-[0.18em] text-gold-soft hover:underline"
                >
                  Privacy
                </Link>
                <Link
                  to={SITE.pages.jobseekers}
                  className="font-mono text-[11px] uppercase tracking-[0.18em] text-gold-soft hover:underline"
                >
                  For jobseekers
                </Link>
                <Link
                  to={SITE.pages.companies}
                  className="font-mono text-[11px] uppercase tracking-[0.18em] text-gold-soft hover:underline"
                >
                  For employers
                </Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>
    </PublicPage>
  );
};

export default AboutPage;
