"use client";

import { Link } from "@/marketing/compat/router";
import Reveal from "@/marketing/components/common/Reveal";
import StatusPill from "@/marketing/components/common/StatusPill";
import { GoldButton, GhostButton } from "@/marketing/components/common/Buttons";
import { PublicPage, PageHero } from "@/marketing/components/common/PublicPage";
import { usePageMeta } from "@/marketing/hooks/usePageMeta";
import { SITE } from "@/marketing/config/site";

const CHAPTERS = [
  { n: "I", text: "A job is one moment." },
  { n: "II", text: "A career is a journey." },
  { n: "III", text: "Employment is an ecosystem." },
];

const NOW = [
  { title: "Public website", copy: "This site is the public front door to AskTrabaajo." },
  { title: "Login and register", copy: "Accounts are created and authenticated on the canonical application — not on this website." },
  { title: "Jobseeker OS", copy: "Work ID, career tools, applications and Athena are available after you enter the platform." },
  { title: "Employer / Job Giver OS", copy: "Company profile, jobs, talent, pipeline and hiring workflows live in the application." },
  { title: "Government entry", copy: "A foundation page exists for government membership. Aggregate labour-market intelligence is not live." },
];

const LATER = [
  { title: "Independent recruiter network", copy: "Verified talent pools, consent-based outreach and portable recruiter reputation." },
  { title: "Institutional credential issuance", copy: "Universities, boards and employers attesting directly to a Work ID." },
  { title: "Government intelligence", copy: "Privacy-preserving, aggregate-only labour market signals. No individual citizen records." },
  { title: "Full Talent Graph matching", copy: "Graph-native matching continues to expand. We will not pretend it is finished." },
];

export const AboutPage = () => {
  usePageMeta({
    title: "About",
    description:
      "AskTrabaajo is the infrastructure and interface for a person's journey through the world of work — connecting people, employers, governments and credentials through one Work ID.",
  });

  return (
    <PublicPage testId="about-page">
      <PageHero
        eyebrow="About AskTrabaajo"
        title={"THE INTERFACE FOR THE\nWORLD OF WORK."}
        copy="AskTrabaajo is the infrastructure and interface for a person's journey through work. It connects people, employers, companies, recruiters, government, skills, opportunities, credentials, career development and AI assistance through a unified work identity — without pretending every future capability is already live."
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
              We are building the layer around the entire journey: every transition,
              every credential, every next chapter. That is the goal. It is not a
              claim that every stage is finished today.
            </p>
          </Reveal>
        </div>
      </section>

      <section className="py-20 sm:py-28 border-t border-white/[0.06]">
        <div className="mx-auto max-w-7xl px-5 sm:px-8 grid lg:grid-cols-2 gap-10">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="font-display text-2xl sm:text-3xl font-semibold text-silver-grad">Available now</h2>
              <StatusPill status="AVAILABLE NOW" />
            </div>
            <ul className="mt-8 space-y-5">
              {NOW.map((item) => (
                <li key={item.title} className="card-surface p-5">
                  <p className="font-display text-lg text-slate-100">{item.title}</p>
                  <p className="mt-2 text-sm text-mist leading-relaxed">{item.copy}</p>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="font-display text-2xl sm:text-3xl font-semibold text-silver-grad">Coming / vision</h2>
              <StatusPill status="OUR VISION" />
            </div>
            <ul className="mt-8 space-y-5">
              {LATER.map((item) => (
                <li key={item.title} className="card-surface p-5">
                  <p className="font-display text-lg text-slate-100">{item.title}</p>
                  <p className="mt-2 text-sm text-mist leading-relaxed">{item.copy}</p>
                </li>
              ))}
            </ul>
          </div>
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
