"use client";

import { useEffect, useRef } from "react";
import SectionHeader from "@/marketing/components/common/SectionHeader";
import Reveal from "@/marketing/components/common/Reveal";

const HUBS = [
  { name: "London", x: 0.46, y: 0.26 },
  { name: "New York", x: 0.24, y: 0.34 },
  { name: "São Paulo", x: 0.32, y: 0.66 },
  { name: "Lagos", x: 0.47, y: 0.55 },
  { name: "Nairobi", x: 0.56, y: 0.60 },
  { name: "Dubai", x: 0.60, y: 0.42 },
  { name: "Mumbai", x: 0.65, y: 0.48 },
  { name: "Singapore", x: 0.74, y: 0.58 },
  { name: "Tokyo", x: 0.85, y: 0.36 },
  { name: "Sydney", x: 0.87, y: 0.74 },
];

const MapCanvas = () => {
  const ref = useRef(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let raf, w, h, dpr, t = 0;

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    const draw = () => {
      t += 0.008;
      ctx.clearRect(0, 0, w, h);

      // dotted lat/long grid
      ctx.fillStyle = "rgba(148,163,184,0.16)";
      const gx = 26, gy = 22;
      for (let i = 0; i < gx; i++) {
        for (let j = 0; j < gy; j++) {
          const x = (i + 0.5) * (w / gx);
          const y = (j + 0.5) * (h / gy);
          const shimmer = 0.5 + 0.5 * Math.sin(t * 2 + i * 0.4 + j * 0.7);
          ctx.globalAlpha = 0.35 + shimmer * 0.4;
          ctx.beginPath();
          ctx.arc(x, y, 1, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      ctx.globalAlpha = 1;

      // hub pulses
      HUBS.forEach((hub, i) => {
        const x = hub.x * w, y = hub.y * h;
        const phase = (t * 1.4 + i * 0.7) % 1;
        ctx.strokeStyle = `rgba(212,175,55,${0.5 * (1 - phase)})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(x, y, 4 + phase * 22, 0, Math.PI * 2);
        ctx.stroke();
        ctx.fillStyle = "#E7C968";
        ctx.beginPath();
        ctx.arc(x, y, 2.4, 0, Math.PI * 2);
        ctx.fill();
      });

      // flowing arcs between a few hub pairs
      const pairs = [[0, 1], [0, 5], [1, 2], [5, 7], [7, 8], [3, 4], [6, 8], [8, 9], [4, 6]];
      pairs.forEach(([a, b], i) => {
        const ax = HUBS[a].x * w, ay = HUBS[a].y * h;
        const bx = HUBS[b].x * w, by = HUBS[b].y * h;
        const mx = (ax + bx) / 2, my = Math.min(ay, by) - Math.hypot(bx - ax, by - ay) * 0.25 - 20;
        ctx.strokeStyle = "rgba(212,175,55,0.22)";
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 7]);
        ctx.lineDashOffset = -t * 40 - i * 5;
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.quadraticCurveTo(mx, my, bx, by);
        ctx.stroke();
        ctx.setLineDash([]);
      });

      raf = requestAnimationFrame(draw);
    };

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      t = 0.5;
      // draw one static frame
      const staticDraw = () => { draw(); cancelAnimationFrame(raf); };
      staticDraw();
    } else {
      draw();
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return <canvas ref={ref} className="w-full h-full" aria-hidden="true" />;
};

export const WorldMap = () => (
  <section id="world-map" data-testid="world-map-section" className="relative py-24 sm:py-36 border-t border-white/[0.06]">
    <div className="mx-auto max-w-7xl px-5 sm:px-8">
      <div className="grid lg:grid-cols-12 gap-12 items-center">
        <div className="lg:col-span-4">
          <SectionHeader
            index="09"
            eyebrow="The Global Workforce Map"
            title={"THE WORLD OF WORK,\nMAPPED."}
            copy="Government Workforce Intelligence reads geography, industries, skills and opportunity as aggregate signals — how countries, cities and sectors relate to talent and work, never as a view of a private person."
            testId="world-map-header"
          />
          <Reveal delay={0.18}>
            <p className="mt-8 font-mono text-[10px] uppercase tracking-[0.2em] text-faint leading-relaxed">
              Geographic lens of the platform.
              <br />
              This map is illustrative. It does not publish live statistics.
            </p>
          </Reveal>
        </div>

        <Reveal delay={0.1} className="lg:col-span-8">
          <div className="card-surface overflow-hidden" data-testid="world-map-panel">
            <div className="relative h-[340px] sm:h-[440px]">
              <MapCanvas />
              {HUBS.slice(0, 6).map((hub) => (
                <span
                  key={hub.name}
                  className="absolute font-mono text-[9px] uppercase tracking-[0.16em] text-slate-400 hidden sm:block"
                  style={{ left: `${hub.x * 100 + 1.5}%`, top: `${hub.y * 100 - 2}%` }}
                >
                  {hub.name}
                </span>
              ))}
            </div>
            <div className="px-6 py-4 border-t border-white/[0.07] flex flex-wrap gap-x-6 gap-y-2">
              {["COUNTRIES", "CITIES", "INDUSTRIES", "SKILLS", "TALENT", "OPPORTUNITIES"].map((t) => (
                <span key={t} className="font-mono text-[9px] uppercase tracking-[0.18em] text-faint">{t}</span>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </div>
  </section>
);

export default WorldMap;
