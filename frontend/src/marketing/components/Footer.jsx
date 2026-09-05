"use client";

import { useNavigate } from "@/marketing/compat/router";
import { Linkedin, Twitter, Youtube } from "lucide-react";
import { SITE, mailto, scrollToId } from "@/marketing/config/site";

const COLS = [
  {
    title: "Platform",
    links: [
      { label: "Jobseekers", href: SITE.pages.jobseekers },
      { label: "Employers", href: SITE.pages.companies },
      { label: "Recruiters", href: SITE.pages.recruiters },
      { label: "Government", href: SITE.pages.governments },
      { label: "Work ID", href: "/#work-id" },
      { label: "Athena", href: "/#athena" },
      { label: "Career Advisor", href: "/#career-advisor" },
      { label: "AI Interviews", href: "/#ai-interviews" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: SITE.pages.about },
      { label: "Contact", href: SITE.pages.contact },
      { label: "Careers", href: `${SITE.pages.contact}#careers` },
      { label: "Partners", href: SITE.pages.institutions },
    ],
  },
  {
    title: "Trust",
    links: [
      { label: "Privacy", href: SITE.pages.privacy },
      { label: "Security", href: `${SITE.pages.privacy}#security` },
      { label: "Terms", href: SITE.pages.terms },
      { label: "Responsible AI", href: `${SITE.pages.privacy}#responsible-ai` },
      { label: "Accessibility", href: `${SITE.pages.privacy}#accessibility` },
    ],
  },
];

const SOCIAL = [
  { icon: Linkedin, href: SITE.social.linkedin, label: "LinkedIn", id: "linkedin" },
  { icon: Twitter, href: SITE.social.x, label: "X", id: "x" },
  { icon: Youtube, href: SITE.social.youtube, label: "YouTube", id: "youtube" },
];

export const Footer = () => {
  const navigate = useNavigate();

  const go = (e, href) => {
    if (!href || href.startsWith("mailto") || href.startsWith("http")) return;
    if (href.startsWith("#")) {
      e.preventDefault();
      if (window.location.pathname === "/") {
        scrollToId(href);
      } else {
        navigate({ pathname: "/", hash: href.slice(1) });
      }
      return;
    }
    if (href.startsWith("/#")) {
      e.preventDefault();
      const hash = href.slice(1);
      if (window.location.pathname === "/") {
        scrollToId(hash);
      } else {
        navigate({ pathname: "/", hash: hash.slice(1) });
      }
      return;
    }
    if (href.startsWith("/")) {
      e.preventDefault();
      const [path, hash] = href.split("#");
      navigate({ pathname: path, hash: hash || "" });
      if (!hash) {
        if (window.__lenis) window.__lenis.scrollTo(0, { immediate: true });
        else window.scrollTo(0, 0);
      }
    }
  };

  return (
    <footer data-testid="site-footer" className="border-t border-white/[0.07] bg-[#060709]">
      <div className="mx-auto max-w-7xl px-5 sm:px-8 py-16 sm:py-20">
        <div className="grid grid-cols-2 md:grid-cols-12 gap-10">
          <div className="col-span-2 md:col-span-5">
            <img
              src="/brand/asktrabaajo-logo.webp"
              alt="AskTrabaajo"
              className="h-8 w-auto brightness-110"
            />
            <p className="mt-6 max-w-sm text-sm text-mist leading-relaxed">
              An intelligent employment ecosystem connecting people, companies,
              recruiters and governments — one interface for the world of work.
            </p>
            <p className="mt-6 font-mono text-[11px] uppercase tracking-[0.22em] text-faint">
              Trust is infrastructure.
            </p>
            <a
              href={mailto(SITE.contact.general, "Hello AskTrabaajo")}
              className="mt-6 inline-block font-mono text-[11px] text-gold-soft hover:underline"
            >
              {SITE.contact.general}
            </a>
            <div className="mt-8 flex items-center gap-3">
              {SOCIAL.map(({ icon: Icon, href, label, id }) =>
                href ? (
                  <a
                    key={id}
                    href={href}
                    data-testid={`footer-social-${id}`}
                    aria-label={`AskTrabaajo on ${label}`}
                    className="w-9 h-9 border border-white/10 rounded-sm flex items-center justify-center text-faint hover:text-gold-soft hover:border-gold/40 transition-colors duration-300"
                  >
                    <Icon className="w-4 h-4" />
                  </a>
                ) : (
                  <span
                    key={id}
                    data-testid={`footer-social-${id}`}
                    aria-label={`${label} profile coming soon`}
                    title={`${label} — coming soon`}
                    className="w-9 h-9 border border-white/10 rounded-sm flex items-center justify-center text-faint/50 cursor-not-allowed"
                  >
                    <Icon className="w-4 h-4" />
                  </span>
                )
              )}
            </div>
          </div>

          {COLS.map((col) => (
            <div key={col.title} className="md:col-span-2">
              <h3 className="font-mono text-[11px] uppercase tracking-[0.24em] text-faint">{col.title}</h3>
              <ul className="mt-5 space-y-3">
                {col.links.map((l) => (
                  <li key={l.label}>
                    <a
                      href={l.href}
                      onClick={(e) => go(e, l.href)}
                      data-testid={`footer-link-${l.label.toLowerCase().replace(/\s+/g, "-")}`}
                      className="text-sm text-mist hover:text-gold-soft transition-colors duration-300"
                    >
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-16 pt-8 border-t border-white/[0.06] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <p className="font-mono text-[11px] tracking-[0.18em] text-faint uppercase">
            © {new Date().getFullYear()} AskTrabaajo. All rights reserved.
          </p>
          <p className="font-mono text-[11px] tracking-[0.18em] text-faint uppercase">
            One interface for the world of work
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
