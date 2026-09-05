"use client";

import { Suspense, lazy, useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { SITE } from "@/marketing/config/site";
import { scrollToId } from "@/marketing/config/site";
import { GoldButton, GhostButton } from "./common/Buttons";
import FallbackNetwork from "./FallbackNetwork";

const GlobeScene = lazy(() => import("./three/GlobeScene"));

const LINES = ["THE OPERATING SYSTEM", "FOR THE WORLD", "OF WORK."];

const FLOW = ["PEOPLE", "SKILLS", "OPPORTUNITIES", "COMPANIES", "GOVERNMENTS"];

const hasWebGL = () => {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
};

export const Hero = () => {
  const reduce = useReducedMotion();
  const [webgl, setWebgl] = useState(false);

  useEffect(() => {
    setWebgl(hasWebGL());
  }, []);

  return (
    <section
      id="top"
      data-testid="hero-section"
      className="relative min-h-screen flex flex-col overflow-hidden"
    >
      <div className="absolute inset-0 grid-bg mask-fade-y" aria-hidden="true" />
      <div
        className="absolute inset-0"
        aria-hidden="true"
        style={{
          background:
            "radial-gradient(ellipse 70% 55% at 68% 42%, rgba(212,175,55,0.09), transparent 65%)",
        }}
      />

      <div className="absolute inset-y-0 right-0 w-full lg:w-[58%] opacity-40 lg:opacity-90">
        {webgl && !reduce ? (
          <Suspense fallback={<FallbackNetwork />}>
            <GlobeScene />
          </Suspense>
        ) : (
          <FallbackNetwork />
        )}
      </div>

      <div className="relative z-10 mx-auto w-full max-w-7xl px-5 sm:px-8 flex-1 flex flex-col justify-center pt-32 pb-16">
        <motion.p
          initial={reduce ? false : { opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1 }}
          className="eyebrow"
          data-testid="hero-eyebrow"
        >
          AskTrabaajo — Global Employment Infrastructure
        </motion.p>

        <h1
          data-testid="hero-headline"
          className="mt-7 font-display font-bold tracking-tight leading-[1.04] text-[11vw] sm:text-6xl lg:text-[5.2rem] max-w-4xl"
        >
          {LINES.map((line, i) => (
            <span key={line} className="block overflow-hidden pb-1">
              <motion.span
                className={`block ${i === 2 ? "text-gold-grad" : "text-silver-grad"}`}
                initial={reduce ? false : { y: "115%" }}
                animate={{ y: 0 }}
                transition={{ duration: 1.05, delay: 0.25 + i * 0.14, ease: [0.22, 1, 0.36, 1] }}
              >
                {line}
              </motion.span>
            </span>
          ))}
        </h1>

        <motion.p
          initial={reduce ? false : { opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.85 }}
          className="mt-7 max-w-xl text-base sm:text-lg text-mist leading-relaxed"
          data-testid="hero-subcopy"
        >
          One intelligent interface for the journey from ambition to employment —
          and everything that comes after. AskTrabaajo connects people, employers,
          recruiters and governments through one intelligent employment ecosystem.
        </motion.p>

        <motion.div
          initial={reduce ? false : { opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 1 }}
          className="mt-10 flex flex-wrap items-center gap-4"
        >
          <GoldButton href={SITE.urls.app} testId="hero-enter-cta">
            Enter AskTrabaajo
          </GoldButton>
          <GhostButton
            href="#big-idea"
            testId="hero-explore-cta"
            onClick={(e) => {
              e.preventDefault();
              scrollToId("#big-idea");
            }}
          >
            Explore the Platform
          </GhostButton>
        </motion.div>

        <motion.div
          initial={reduce ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.2, delay: 1.25 }}
          className="mt-16 sm:mt-20"
          data-testid="hero-flow-strip"
        >
          <div className="flex flex-wrap items-center gap-x-3 gap-y-3">
            {FLOW.map((step, i) => (
              <span key={step} className="flex items-center gap-3">
                <span className="font-mono text-[10px] sm:text-[11px] uppercase tracking-[0.24em] text-slate-400 border border-white/10 bg-white/[0.03] px-3 py-1.5 rounded-sm">
                  {step}
                </span>
                {i < FLOW.length - 1 && (
                  <span className="hidden sm:block h-px w-6 bg-gradient-to-r from-gold/60 to-transparent" aria-hidden="true" />
                )}
              </span>
            ))}
          </div>
          <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
            Connected through one intelligent global network
          </p>
        </motion.div>
      </div>

      <div className="relative z-10 pb-8 flex justify-center" aria-hidden="true">
        <motion.div
          animate={reduce ? {} : { y: [0, 8, 0] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
          className="w-px h-12 bg-gradient-to-b from-transparent via-gold/60 to-transparent"
        />
      </div>
    </section>
  );
};

export default Hero;
