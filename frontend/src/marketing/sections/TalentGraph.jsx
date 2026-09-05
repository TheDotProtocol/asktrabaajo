"use client";

import { useState } from "react";
import SectionHeader from "@/marketing/components/common/SectionHeader";
import Reveal from "@/marketing/components/common/Reveal";

const MODES = {
  person: {
    label: "Person View",
    nodes: [
      { id: "person", x: 90, y: 170, r: 26, label: "PERSON", gold: true },
      { id: "s1", x: 300, y: 60, r: 15, label: "React" },
      { id: "s2", x: 330, y: 150, r: 15, label: "System Design" },
      { id: "s3", x: 300, y: 250, r: 15, label: "Leadership" },
      { id: "cred", x: 500, y: 90, r: 14, label: "Credentials" },
      { id: "opp", x: 540, y: 210, r: 18, label: "OPPORTUNITIES", gold: true },
      { id: "path", x: 700, y: 140, r: 18, label: "CAREER PATH", gold: true },
    ],
    edges: [
      ["person", "s1"], ["person", "s2"], ["person", "s3"],
      ["s1", "cred"], ["s2", "cred"], ["s2", "opp"], ["s3", "opp"],
      ["cred", "path"], ["opp", "path"],
    ],
  },
  company: {
    label: "Company View",
    nodes: [
      { id: "company", x: 90, y: 170, r: 26, label: "COMPANY", gold: true },
      { id: "r1", x: 300, y: 70, r: 15, label: "Role Spec" },
      { id: "r2", x: 330, y: 170, r: 15, label: "Requirements" },
      { id: "r3", x: 290, y: 265, r: 15, label: "Compensation" },
      { id: "talent", x: 520, y: 110, r: 18, label: "TALENT", gold: true },
      { id: "pipe", x: 540, y: 230, r: 14, label: "Pipeline" },
      { id: "hiring", x: 710, y: 160, r: 18, label: "HIRING", gold: true },
    ],
    edges: [
      ["company", "r1"], ["company", "r2"], ["company", "r3"],
      ["r1", "talent"], ["r2", "talent"], ["r2", "pipe"], ["r3", "pipe"],
      ["talent", "hiring"], ["pipe", "hiring"],
    ],
  },
};

export const TalentGraph = () => {
  const [mode, setMode] = useState("person");
  const graph = MODES[mode];
  const nodeById = Object.fromEntries(graph.nodes.map((n) => [n.id, n]));

  return (
    <section id="talent-graph" data-testid="talent-graph-section" className="relative py-24 sm:py-36 border-t border-white/[0.06]">
      <div className="absolute inset-0 grid-bg opacity-40 mask-fade-y" aria-hidden="true" />
      <div className="relative mx-auto max-w-7xl px-5 sm:px-8">
        <SectionHeader
          index="03"
          eyebrow="The Talent Graph"
          title={"STOP SEARCHING RESUMES.\nSTART UNDERSTANDING TALENT."}
          copy="The Talent Graph connects people, skills, experience, credentials, jobs, companies and career paths — so matching is comprehension, not keyword filtering. Jobseekers see opportunities and pathways. Employers discover talent and run pipelines."
          testId="talent-graph-header"
        />

        <Reveal delay={0.15}>
          <div className="mt-14 card-surface overflow-hidden" data-testid="talent-graph-panel">
            <div className="flex flex-wrap items-center justify-between gap-4 px-6 sm:px-8 py-5 border-b border-white/[0.07]">
              <div className="flex gap-2" role="tablist" aria-label="Talent graph perspective">
                {Object.entries(MODES).map(([key, m]) => (
                  <button
                    key={key}
                    role="tab"
                    aria-selected={mode === key}
                    data-testid={`talent-graph-mode-${key}`}
                    onClick={() => setMode(key)}
                    className={`font-mono text-[11px] uppercase tracking-[0.18em] px-4 py-2 rounded-sm border transition-colors duration-300 ${
                      mode === key
                        ? "border-gold/50 text-gold-soft bg-gold/[0.08]"
                        : "border-white/10 text-faint hover:text-mist"
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
              <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">
                How the graph is read
              </span>
            </div>

            <div className="relative">
              <svg
                viewBox="0 0 800 340"
                className="w-full h-auto"
                role="img"
                aria-label={`Talent graph showing ${graph.label.toLowerCase()} relationships`}
              >
                {graph.edges.map(([a, b]) => {
                  const na = nodeById[a], nb = nodeById[b];
                  return (
                    <line
                      key={`${a}-${b}`}
                      x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
                      stroke="rgba(212,175,55,0.35)"
                      strokeWidth="1"
                      className="dash-flow"
                    />
                  );
                })}
                {graph.nodes.map((n) => (
                  <g key={n.id} className="node-pulse" style={{ animationDelay: `${(n.x + n.y) % 7 * 0.4}s` }}>
                    <circle
                      cx={n.x} cy={n.y} r={n.r}
                      fill={n.gold ? "rgba(212,175,55,0.12)" : "rgba(148,163,184,0.08)"}
                      stroke={n.gold ? "rgba(212,175,55,0.7)" : "rgba(148,163,184,0.4)"}
                      strokeWidth="1"
                    />
                    <circle cx={n.x} cy={n.y} r={n.gold ? 3.5 : 2.5} fill={n.gold ? "#E7C968" : "#94A3B8"} />
                    <text
                      x={n.x}
                      y={n.y + n.r + 16}
                      textAnchor="middle"
                      className="fill-slate-400"
                      style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "10px", letterSpacing: "0.14em", textTransform: "uppercase" }}
                    >
                      {n.label}
                    </text>
                  </g>
                ))}
              </svg>
            </div>

            <div className="px-6 sm:px-8 py-5 border-t border-white/[0.07] flex flex-wrap gap-x-8 gap-y-2">
              {(mode === "person"
                ? ["PERSON → SKILLS", "SKILLS → CREDENTIALS", "SKILLS → OPPORTUNITIES", "OPPORTUNITIES → CAREER PATH"]
                : ["COMPANY → REQUIREMENTS", "REQUIREMENTS → TALENT", "REQUIREMENTS → PIPELINE", "PIPELINE → HIRING"]
              ).map((t) => (
                <span key={t} className="font-mono text-[10px] tracking-[0.16em] text-faint uppercase">{t}</span>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
};

export default TalentGraph;
