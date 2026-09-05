"use client";

import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "@/marketing/compat/router";
import { AnimatePresence, motion } from "framer-motion";
import { Menu, X, ArrowUpRight } from "lucide-react";
import { SITE, scrollToId } from "@/marketing/config/site";

const LINKS = [
  { label: "About", href: SITE.pages.about },
  { label: "Jobseekers", href: SITE.pages.jobseekers },
  { label: "Employers", href: SITE.pages.companies },
  { label: "Government", href: SITE.pages.governments },
  { label: "Work ID", href: "/#work-id" },
  { label: "Athena", href: "/#athena" },
  { label: "Contact", href: SITE.pages.contact },
];

function parseHashHref(href) {
  if (href.startsWith("#")) return href;
  if (href.startsWith("/#")) return href.slice(1);
  return null;
}

export const Nav = () => {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const go = (e, href) => {
    if (!href || href.startsWith("http") || href.startsWith("mailto")) return;
    e.preventDefault();
    setOpen(false);
    const hash = parseHashHref(href);
    if (hash) {
      if (location.pathname === "/") {
        scrollToId(hash);
        window.history.replaceState(null, "", `/${hash}`);
      } else {
        navigate({ pathname: "/", hash: hash.slice(1) });
      }
      return;
    }
    navigate(href);
  };

  return (
    <header
      data-testid="site-nav"
      className={`fixed top-0 left-0 right-0 z-50 transition-colors duration-500 ${
        scrolled ? "bg-ink/85 backdrop-blur-xl border-b border-white/[0.07]" : "border-b border-transparent"
      }`}
    >
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-[60] focus:bg-gold focus:text-ink focus:px-4 focus:py-2 focus:font-mono focus:text-xs"
      >
        Skip to content
      </a>
      <nav className="mx-auto max-w-7xl px-5 sm:px-8 h-[72px] flex items-center justify-between" aria-label="Primary">
        <Link
          to="/"
          data-testid="nav-logo-link"
          className="flex items-center gap-3 shrink-0"
          aria-label="AskTrabaajo home"
          onClick={() => setOpen(false)}
        >
          <img
            src="/brand/asktrabaajo-logo.webp"
            alt="AskTrabaajo"
            className="h-7 sm:h-8 w-auto mix-blend-screen invert-0 brightness-110"
          />
        </Link>

        <div className="hidden xl:flex items-center gap-5">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={(e) => go(e, l.href)}
              data-testid={`nav-link-${l.label.toLowerCase().replace(/\s+/g, "-")}`}
              className="font-mono text-[10px] uppercase tracking-[0.16em] text-mist hover:text-gold-soft transition-colors duration-300"
            >
              {l.label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <a
            href={SITE.urls.login}
            data-testid="nav-login-cta"
            className="hidden sm:inline-flex font-mono text-[11px] uppercase tracking-[0.18em] text-mist hover:text-gold-soft transition-colors duration-300"
          >
            Login
          </a>
          <a
            href={SITE.urls.register}
            data-testid="nav-register-cta"
            className="hidden sm:inline-flex font-mono text-[11px] uppercase tracking-[0.18em] text-mist hover:text-gold-soft transition-colors duration-300"
          >
            Register
          </a>
          <a
            href={SITE.urls.app}
            data-testid="nav-enter-cta"
            className="hidden sm:inline-flex items-center gap-2 border border-gold/40 text-gold-soft font-mono text-[11px] uppercase tracking-[0.18em] px-5 py-2.5 rounded-sm hover:bg-gold hover:text-ink transition-colors duration-300"
          >
            Enter AskTrabaajo
            <ArrowUpRight className="w-3.5 h-3.5" />
          </a>
          <button
            data-testid="nav-mobile-toggle"
            onClick={() => setOpen((v) => !v)}
            className="xl:hidden p-2 text-slate-200"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
          >
            {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </nav>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="xl:hidden overflow-hidden bg-ink/95 backdrop-blur-xl border-b border-white/[0.07]"
          >
            <div className="px-6 py-6 flex flex-col gap-5">
              {LINKS.map((l) => (
                <a
                  key={l.href}
                  href={l.href}
                  onClick={(e) => go(e, l.href)}
                  data-testid={`nav-mobile-link-${l.label.toLowerCase().replace(/\s+/g, "-")}`}
                  className="font-display text-lg text-slate-200 hover:text-gold-soft transition-colors"
                >
                  {l.label}
                </a>
              ))}
              <a
                href={SITE.urls.login}
                data-testid="nav-mobile-login-cta"
                className="font-display text-lg text-slate-200 hover:text-gold-soft transition-colors"
              >
                Login
              </a>
              <a
                href={SITE.urls.register}
                data-testid="nav-mobile-register-cta"
                className="font-display text-lg text-slate-200 hover:text-gold-soft transition-colors"
              >
                Register
              </a>
              <a
                href={SITE.urls.app}
                data-testid="nav-mobile-enter-cta"
                className="mt-2 inline-flex items-center justify-center gap-2 bg-gold text-ink font-display font-semibold px-5 py-3 rounded-sm"
              >
                Enter AskTrabaajo
                <ArrowUpRight className="w-4 h-4" />
              </a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
};

export default Nav;
