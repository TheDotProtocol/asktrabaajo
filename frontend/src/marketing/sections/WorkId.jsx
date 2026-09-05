"use client";

import { useRef, useState } from "react";
import { motion, useMotionValue, useSpring, useTransform, useReducedMotion } from "framer-motion";
import { Fingerprint, ShieldCheck, Lock } from "lucide-react";
import SectionHeader from "@/marketing/components/common/SectionHeader";
import Reveal from "@/marketing/components/common/Reveal";
import { GhostButton } from "@/marketing/components/common/Buttons";
import { scrollToId } from "@/marketing/config/site";

const STATUSES = ["VERIFIED", "PENDING", "UNVERIFIED", "EXPIRED", "REVOKED"];
const STATUS_COLORS = {
  VERIFIED: "text-emerald-400 border-emerald-500/40 bg-emerald-950/50",
  PENDING: "text-amber-400 border-amber-500/40 bg-amber-950/50",
  UNVERIFIED: "text-slate-400 border-white/20 bg-white/[0.04]",
  EXPIRED: "text-orange-400 border-orange-500/40 bg-orange-950/50",
  REVOKED: "text-red-400 border-red-500/40 bg-red-950/50",
};

const CREDENTIAL_ROWS = [
  { label: "B.Sc. Computer Science", issuer: "University", status: "VERIFIED" },
  { label: "Senior Product Engineer", issuer: "Employment record", status: "VERIFIED" },
  { label: "Cloud Architecture Cert.", issuer: "Licensing body", status: "PENDING" },
];

const WorkIdCard = ({ status }) => {
  const ref = useRef(null);
  const reduce = useReducedMotion();
  const mx = useMotionValue(0.5);
  const my = useMotionValue(0.5);
  const rx = useSpring(useTransform(my, [0, 1], [10, -10]), { stiffness: 140, damping: 18 });
  const ry = useSpring(useTransform(mx, [0, 1], [-12, 12]), { stiffness: 140, damping: 18 });

  const onMove = (e) => {
    if (reduce || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    mx.set((e.clientX - r.left) / r.width);
    my.set((e.clientY - r.top) / r.height);
  };

  return (
    <div style={{ perspective: 1200 }} className="w-full max-w-md mx-auto">
      <motion.div
        ref={ref}
        onMouseMove={onMove}
        onMouseLeave={() => { mx.set(0.5); my.set(0.5); }}
        style={reduce ? {} : { rotateX: rx, rotateY: ry }}
        data-testid="work-id-card"
        className="relative rounded-xl border border-white/12 bg-gradient-to-br from-[#171a22] via-[#101218] to-[#0a0c10] p-7 sm:p-8 shadow-[0_40px_80px_-20px_rgba(0,0,0,0.8)] overflow-hidden"
      >
        <div className="absolute inset-0 overflow-hidden rounded-xl" aria-hidden="true">
          <div className="absolute inset-y-0 w-24 bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" style={{ animation: "sheen-move 5.5s ease-in-out infinite" }} />
        </div>
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-gold/60 to-transparent" aria-hidden="true" />

        <div className="relative flex items-start justify-between">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-gold/90">AskTrabaajo</p>
            <p className="mt-1 font-display text-lg font-semibold tracking-[0.14em] text-slate-100">WORK ID</p>
          </div>
          <span
            data-testid="work-id-status-badge"
            className={`font-mono text-[10px] tracking-[0.18em] border px-2.5 py-1 rounded-full ${STATUS_COLORS[status]}`}
          >
            {status}
          </span>
        </div>

        <div className="relative mt-8 flex items-center gap-4">
          <div className="w-12 h-12 rounded-full border border-gold/40 bg-gold/10 flex items-center justify-center">
            <Fingerprint className="w-5 h-5 text-gold-soft" />
          </div>
          <div>
            <p className="font-display text-lg text-slate-100">Alex M. — Product Engineer</p>
            <p className="font-mono text-[10px] text-faint tracking-wider mt-0.5">SAMPLE IDENTITY · did:trabaajo:8f3k…x92q</p>
          </div>
        </div>

        <div className="relative mt-7 space-y-2.5">
          {CREDENTIAL_ROWS.map((c) => (
            <div key={c.label} className="flex items-center justify-between border border-white/[0.07] bg-white/[0.02] rounded-sm px-3.5 py-2.5">
              <div>
                <p className="text-sm text-slate-200">{c.label}</p>
                <p className="font-mono text-[10px] text-faint mt-0.5">{c.issuer}</p>
              </div>
              <span className={`font-mono text-[9px] tracking-[0.16em] border px-2 py-0.5 rounded-full ${STATUS_COLORS[c.status]}`}>
                {c.status}
              </span>
            </div>
          ))}
        </div>

        <div className="relative mt-7 flex items-center justify-between">
          <p className="font-mono text-[9px] text-faint tracking-[0.14em]">PROOF 0x7A3F…E91C · CONSENT-CONTROLLED</p>
          <Lock className="w-3.5 h-3.5 text-gold/70" />
        </div>
      </motion.div>
    </div>
  );
};

export const WorkId = () => {
  const [status, setStatus] = useState("VERIFIED");

  return (
    <section id="work-id" data-testid="work-id-section" className="relative py-24 sm:py-36 border-t border-white/[0.06]">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <div>
            <SectionHeader
              index="02"
              eyebrow="Work ID"
              title={"YOUR PROFESSIONAL LIFE.\nONE PLACE."}
              copy="Work ID is your persistent professional identity — connecting history, education, skills, credentials, employment and goals into one living record that travels with you. You control what is disclosed, to whom, and when. Nothing moves without consent."
              testId="work-id-header"
            />
            <Reveal delay={0.2}>
              <div className="mt-8 flex flex-wrap gap-2" role="group" aria-label="Credential states">
                {STATUSES.map((s) => (
                  <button
                    key={s}
                    data-testid={`work-id-status-${s.toLowerCase()}`}
                    onClick={() => setStatus(s)}
                    aria-pressed={status === s}
                    className={`font-mono text-[10px] tracking-[0.16em] border px-3 py-1.5 rounded-full transition-all duration-300 ${
                      status === s ? STATUS_COLORS[s] + " scale-105" : "border-white/10 text-faint hover:text-mist"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </Reveal>
            <Reveal delay={0.26}>
              <div className="mt-10 flex items-center gap-6">
                <GhostButton
                  href="#final-cta"
                  testId="work-id-explore-cta"
                  onClick={(e) => { e.preventDefault(); scrollToId("#final-cta"); }}
                >
                  Explore Work ID
                </GhostButton>
                <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em] text-faint">
                  <ShieldCheck className="w-3.5 h-3.5 text-gold/70" />
                  Privacy & consent first
                </span>
              </div>
            </Reveal>
          </div>

          <Reveal delay={0.15} className="relative">
            <div
              className="absolute inset-0 -z-10"
              aria-hidden="true"
              style={{ background: "radial-gradient(ellipse 60% 50% at 50% 50%, rgba(212,175,55,0.10), transparent 70%)" }}
            />
            <WorkIdCard status={status} />
          </Reveal>
        </div>
      </div>
    </section>
  );
};

export default WorkId;
