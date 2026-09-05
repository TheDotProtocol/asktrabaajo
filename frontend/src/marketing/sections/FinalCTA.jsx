"use client";

import Reveal from "@/marketing/components/common/Reveal";
import { GoldButton, GhostButton } from "@/marketing/components/common/Buttons";
import { SITE, mailto } from "@/marketing/config/site";

export const FinalCTA = () => (
  <section id="final-cta" data-testid="final-cta-section" className="relative py-28 sm:py-44 border-t border-white/[0.06] overflow-hidden">
    <div
      className="absolute inset-0"
      aria-hidden="true"
      style={{ background: "radial-gradient(ellipse 55% 60% at 50% 100%, rgba(212,175,55,0.13), transparent 70%)" }}
    />
    <div className="absolute inset-0 grid-bg opacity-50 mask-fade-y" aria-hidden="true" />

    <div className="relative mx-auto max-w-5xl px-5 sm:px-8 text-center">
      <Reveal>
        <span className="eyebrow">Begin</span>
      </Reveal>
      <Reveal delay={0.08}>
        <h2 className="mt-6 font-display text-4xl sm:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.05]">
          <span className="text-silver-grad">YOUR NEXT CHAPTER</span>
          <br />
          <span className="text-gold-grad">STARTS HERE.</span>
        </h2>
      </Reveal>
      <Reveal delay={0.16}>
        <p className="mt-8 max-w-xl mx-auto text-base sm:text-lg text-mist leading-relaxed">
          Whether you're building a career, a team or a nation's workforce —
          the journey runs through one interface.
        </p>
      </Reveal>
      <Reveal delay={0.24}>
        <div className="mt-12 flex flex-wrap items-center justify-center gap-4">
          <GoldButton href={SITE.urls.createWorkId} testId="final-create-work-id-cta">
            Create Your Work ID
          </GoldButton>
          <GoldButton href={SITE.urls.startHiring} testId="final-start-hiring-cta" className="!bg-transparent !text-gold-soft border border-gold/50 hover:!bg-gold/10">
            Start Hiring
          </GoldButton>
        </div>
      </Reveal>
      <Reveal delay={0.3}>
        <div className="mt-8">
          <GhostButton href={mailto(SITE.contact.access, "Exploring AskTrabaajo")} testId="final-explore-cta" className="!border-transparent !text-faint hover:!text-gold-soft">
            Explore AskTrabaajo — talk to us
          </GhostButton>
        </div>
      </Reveal>
    </div>
  </section>
);

export default FinalCTA;
