"use client";

import { ReactNode, useEffect } from "react";
import Lenis from "lenis";

import Footer from "@/marketing/components/Footer";
import Nav from "@/marketing/components/Nav";

export function MarketingShell({ children }: { children: ReactNode }) {
  useEffect(() => {
    document.documentElement.classList.add("marketing");
    document.body.classList.add("marketing");
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return () => {
        document.documentElement.classList.remove("marketing");
        document.body.classList.remove("marketing");
      };
    }
    const lenis = new Lenis({ duration: 1.15, smoothWheel: true });
    (window as Window & { __lenis?: Lenis }).__lenis = lenis;
    let raf = 0;
    const loop = (t: number) => {
      lenis.raf(t);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(raf);
      lenis.destroy();
      (window as Window & { __lenis?: Lenis }).__lenis = undefined;
      document.documentElement.classList.remove("marketing");
      document.body.classList.remove("marketing");
    };
  }, []);

  return (
    <div className="marketing-root bg-ink min-h-screen text-slate-100">
      <div className="noise-layer" aria-hidden="true" />
      <Nav />
      {children}
      <Footer />
    </div>
  );
}
