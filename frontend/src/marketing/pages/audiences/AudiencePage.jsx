"use client";

import { useEffect } from "react";
import { Link } from "@/marketing/compat/router";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import Reveal from "@/marketing/components/common/Reveal";
import StatusPill from "@/marketing/components/common/StatusPill";
import { GoldButton, GhostButton } from "@/marketing/components/common/Buttons";
import { AUDIENCE_PAGES, AUDIENCE_ORDER } from "./content";
import { usePageMeta } from "@/marketing/hooks/usePageMeta";

const HeroLines = ({ title }) => {
  const reduce = useReducedMotion();
  return (
    <h1
      data-testid="audience-headline"
      className="mt-7 font-display font-bold tracking-tight leading-[1.06] text-4xl sm:text-6xl lg:text-7xl max-w-4xl"
    >
      {title.split("\n").map((line, i) => (
        <span key={line} className="block overflow-hidden pb-1">
          <motion.span
            className={`block ${i === 1 ? "text-gold-grad" : "text-silver-grad"}`}
            initial={reduce ? false : { y: "112%" }}
            animate={{ y: 0 }}
            transition={{ duration: 0.95, delay: 0.15 + i * 0.12, ease: [0.22, 1, 0.36, 1] }}
          >
            {line}
          </motion.span>
        </span>
      ))}
    </h1>
  );
};

const AudiencePage = ({ data }) => {
  usePageMeta({
    title: data.eyebrow,
    description: data.copy,
  });

  useEffect(() => {
    if (window.__lenis) window.__lenis.scrollTo(0, { immediate: true });
    else window.scrollTo(0, 0);
  }, [data.id]);

  const others = AUDIENCE_ORDER.filter((k) => k !== data.id);

  return (
    <main id="main-content" data-testid={`audience-page-${data.id}`}>
      <section className="relative pt-40 pb-20 sm:pb-28 overflow-hidden">
        <div className="absolute inset-0 grid-bg mask-fade-y" aria-hidden="true" />
        <div
          className="absolute inset-0"
          aria-hidden="true"
          style={{ background: "radial-gradient(ellipse 60% 50% at 70% 20%, rgba(212,175,55,0.08), transparent 65%)" }}
        />
        <div className="relative mx-auto max-w-7xl px-5 sm:px-8">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
            className="flex items-center gap-4 flex-wrap"
          >
            <span className="eyebrow">{data.eyebrow}</span>
            <StatusPill status={data.status} />
          </motion.div>

          <HeroLines title={data.title} />

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.55 }}
            className="mt-7 max-w-2xl text-base sm:text-lg text-mist leading-relaxed"
          >
            {data.copy}
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.7 }}
            className="mt-10 flex flex-wrap items-center gap-4"
          >
            <GoldButton href={data.cta.primary.href} testId={`audience-cta-primary-${data.id}`}>
              {data.cta.primary.label}
            </GoldButton>
            <GhostButton href={data.cta.secondary.href} testId={`audience-cta-secondary-${data.id}`}>
              {data.cta.secondary.label}
            </GhostButton>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1, delay: 0.85 }}
            className="mt-12 flex flex-wrap gap-2"
          >
            {data.chips.map((c) => (
              <span key={c} className="font-mono text-[10px] uppercase tracking-[0.2em] text-slate-400 border border-white/10 bg-white/[0.03] px-3 py-1.5 rounded-sm">
                {c}
              </span>
            ))}
          </motion.div>
        </div>
      </section>

      <section className="py-20 sm:py-28 border-t border-white/[0.06]">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <Reveal>
            <h2 className="font-display text-2xl sm:text-4xl font-semibold tracking-tight text-silver-grad">
              What this means for you
            </h2>
          </Reveal>
          <div className="mt-12 grid sm:grid-cols-2 gap-3" data-testid={`audience-features-${data.id}`}>
            {data.features.map((f, i) => (
              <Reveal key={f.title} delay={i * 0.06}>
                <div className="group card-surface p-6 sm:p-8 h-full hover:border-gold/40 transition-colors duration-300">
                  <span className="w-11 h-11 rounded-sm border border-gold/30 bg-gold/[0.07] flex items-center justify-center">
                    <f.icon className="w-5 h-5 text-gold-soft" />
                  </span>
                  <h3 className="mt-6 font-display text-xl text-slate-100">{f.title}</h3>
                  <p className="mt-3 text-sm sm:text-base text-mist leading-relaxed">{f.copy}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 sm:py-28 border-t border-white/[0.06]">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <Reveal>
            <h2 className="font-display text-2xl sm:text-4xl font-semibold tracking-tight text-silver-grad">
              How the journey works
            </h2>
          </Reveal>
          <ol className="mt-12 grid sm:grid-cols-2 lg:grid-cols-4 gap-3" data-testid={`audience-steps-${data.id}`}>
            {data.steps.map((s, i) => (
              <Reveal key={s} delay={i * 0.07}>
                <li className="relative card-surface p-6 h-full">
                  <span className="font-mono text-xs text-gold/80 tracking-[0.2em]">{String(i + 1).padStart(2, "0")}</span>
                  <p className="mt-4 font-display text-lg text-slate-100 leading-snug">{s}</p>
                  <span className="mt-5 block h-px bg-gradient-to-r from-gold/40 to-transparent" aria-hidden="true" />
                </li>
              </Reveal>
            ))}
          </ol>
        </div>
      </section>

      <section className="py-20 sm:py-28 border-t border-white/[0.06]">
        <div className="mx-auto max-w-7xl px-5 sm:px-8">
          <Reveal>
            <div className="border border-gold/25 bg-gold/[0.04] rounded-lg p-8 sm:p-12" data-testid={`audience-quote-${data.id}`}>
              <p className="font-display text-xl sm:text-3xl font-light text-slate-100 leading-snug max-w-4xl">
                "{data.quote}"
              </p>
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <div className="mt-16 flex flex-col sm:flex-row sm:items-center justify-between gap-8 border border-white/[0.07] rounded-lg p-8 sm:p-10 bg-coal/60">
              <div>
                <h2 className="font-display text-2xl sm:text-3xl font-semibold text-silver-grad tracking-tight">
                  Ready when you are.
                </h2>
                <p className="mt-3 text-mist max-w-md">{data.cta.primary.label} — or keep exploring the platform.</p>
              </div>
              <GoldButton href={data.cta.primary.href} testId={`audience-cta-bottom-${data.id}`}>
                {data.cta.primary.label}
              </GoldButton>
            </div>
          </Reveal>

          <Reveal delay={0.15}>
            <div className="mt-16">
              <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-faint">Explore other audiences</p>
              <div className="mt-5 grid grid-cols-2 lg:grid-cols-4 gap-3">
                {others.map((key) => {
                  const o = AUDIENCE_PAGES[key];
                  return (
                    <Link
                      key={key}
                      to={`/${key}`}
                      data-testid={`audience-crosslink-${key}`}
                      className="group flex items-center justify-between border border-white/[0.08] rounded-sm px-4 py-4 hover:border-gold/50 hover:bg-gold/[0.03] transition-all duration-300"
                    >
                      <span className="text-sm text-mist group-hover:text-slate-100 transition-colors">{o.eyebrow.replace("For ", "")}</span>
                      <ArrowUpRight className="w-4 h-4 text-faint group-hover:text-gold-soft transition-colors" />
                    </Link>
                  );
                })}
              </div>
            </div>
          </Reveal>
        </div>
      </section>
    </main>
  );
};

export default AudiencePage;
