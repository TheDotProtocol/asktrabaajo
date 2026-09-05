"use client";

import Reveal from "@/marketing/components/common/Reveal";

const CHAPTERS = [
  { n: "I", text: "A job is one moment." },
  { n: "II", text: "A career is a journey." },
  { n: "III", text: "Employment is an ecosystem." },
];

export const Philosophy = () => (
  <section id="philosophy" data-testid="philosophy-section" className="relative py-28 sm:py-44 border-t border-white/[0.06]">
    <div className="mx-auto max-w-7xl px-5 sm:px-8">
      <div className="grid lg:grid-cols-12 gap-12">
        <div className="lg:col-span-3">
          <Reveal>
            <div className="lg:sticky lg:top-32">
              <span className="eyebrow">The Philosophy</span>
              <div className="mt-6 h-24 w-px bg-gradient-to-b from-gold/70 to-transparent" aria-hidden="true" />
            </div>
          </Reveal>
        </div>

        <div className="lg:col-span-9">
          <Reveal>
            <h2 className="font-display text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight leading-[1.05] text-silver-grad">
              WORK IS MORE
              <br />
              THAN A JOB.
            </h2>
          </Reveal>

          <div className="mt-16 space-y-10 max-w-3xl">
            {CHAPTERS.map((c, i) => (
              <Reveal key={c.n} delay={i * 0.08}>
                <div className="flex items-baseline gap-6 sm:gap-10 border-b border-white/[0.07] pb-10">
                  <span className="font-display text-2xl sm:text-3xl text-gold/70 font-light shrink-0 w-14">{c.n}.</span>
                  <p className="font-display text-2xl sm:text-4xl font-light text-slate-200 leading-snug">{c.text}</p>
                </div>
              </Reveal>
            ))}
          </div>

          <Reveal delay={0.2}>
            <p className="mt-14 max-w-2xl text-base sm:text-lg text-mist leading-relaxed">
              AskTrabaajo is designed to connect the entire journey — because the
              moments between jobs are where careers are actually made.
            </p>
          </Reveal>
        </div>
      </div>
    </div>
  </section>
);

export default Philosophy;
