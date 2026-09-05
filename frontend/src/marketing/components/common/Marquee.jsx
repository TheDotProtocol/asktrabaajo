"use client";

const ITEMS = [
  "PERSISTENT IDENTITY",
  "CONSENT BY DESIGN",
  "THE TALENT GRAPH",
  "PRIVACY-PRESERVING INTELLIGENCE",
  "ONE INTERFACE FOR WORK",
  "TRUST IS INFRASTRUCTURE",
  "VERIFIED CREDENTIALS",
  "THE ATHENA LAYER",
];

const Row = () => (
  <div className="flex shrink-0 items-center">
    {ITEMS.map((item) => (
      <span key={item} className="flex items-center">
        <span className="font-display text-lg sm:text-2xl font-light tracking-[0.22em] text-slate-500 px-8 sm:px-12 whitespace-nowrap">
          {item}
        </span>
        <span className="w-1.5 h-1.5 rotate-45 bg-gold/50" aria-hidden="true" />
      </span>
    ))}
  </div>
);

export const Marquee = () => (
  <div
    data-testid="editorial-marquee"
    className="relative border-y border-white/[0.07] py-7 sm:py-9 overflow-hidden"
    aria-hidden="true"
  >
    <div className="marquee-track flex w-max">
      <Row />
      <Row />
    </div>
    <div className="absolute inset-y-0 left-0 w-24 bg-gradient-to-r from-ink to-transparent" />
    <div className="absolute inset-y-0 right-0 w-24 bg-gradient-to-l from-ink to-transparent" />
  </div>
);

export default Marquee;
