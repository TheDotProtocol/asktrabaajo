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
  { title: "Jobseeker OS", copy: "Manage your professional life — Work ID, documents, credentials, career, opportunities, applications, interviews, offers, messages and Athena." },
  { title: "Employer OS", copy: "Manage hiring — company profile, members, jobs, talent, pipeline, interviews, offers, outreach, analytics and billing." },
  { title: "Government Workforce Intelligence", copy: "Privacy-preserving, aggregate insight into workforce, skills, geography, employment, industries, opportunities and companies. No individual citizen records." },
  { title: "Work ID", copy: "A persistent professional identity connecting a person's verified professional journey, with consent-controlled disclosure." },
  { title: "Athena", copy: "AskTrabaajo's intelligent interface for jobseekers, employers and government — natural language into controlled platform tools." },
  { title: "Talent Graph", copy: "Connects skills, people, opportunities, companies and career pathways so discovery is more than keyword search." },
];

export const AboutPage = () => {
  usePageMeta({
    title: "About",
    description:
      "AskTrabaajo is the operating system for the world of work — connecting people, employers and government workforce intelligence through one Work ID.",
  });

  return (
    <PublicPage testId="about-page">
      <PageHero
        eyebrow="About AskTrabaajo"
        title={"THE OPERATING SYSTEM\nFOR THE WORLD OF WORK."}
        copy="AskTrabaajo is a live employment operating system. It connects people, employers, government, skills, opportunities, credentials, career development and AI assistance through a unified work identity."
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
