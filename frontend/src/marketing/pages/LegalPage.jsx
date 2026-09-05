"use client";

import { useEffect } from "react";
import { useLocation } from "@/marketing/compat/router";
import Reveal from "@/marketing/components/common/Reveal";
import { PublicPage, PageHero } from "@/marketing/components/common/PublicPage";
import { usePageMeta } from "@/marketing/hooks/usePageMeta";
import { SITE, mailto, scrollToId } from "@/marketing/config/site";

const PRIVACY = [
  {
    id: "privacy",
    title: "What this statement is",
    body: "This is an informational privacy statement for a platform in active development. It is not a substitute for a counsel-reviewed privacy policy. When a formal policy is published, it will replace this page.",
  },
  {
    id: "who",
    title: "Who we are",
    body: `AskTrabaajo is the public name of this employment infrastructure product. Public contact: ${SITE.contact.general}.`,
  },
  {
    id: "website",
    title: "This public website",
    body: "Browsing this marketing site does not create an AskTrabaajo account. This site does not currently operate a hosted contact-form backend. If you email us, we receive the content you send (your address, message, and any details you include).",
  },
  {
    id: "accounts",
    title: "Accounts and the application",
    body: "Login, registration and platform data live on the canonical AskTrabaajo application — a separate system from this website. Account, Work ID and organization data are governed by that application's rules. We do not invent additional collection here.",
  },
  {
    id: "principles",
    title: "Design principles",
    body: "AskTrabaajo is designed around consent-controlled disclosure, tenant isolation, and data minimization. Government-facing capabilities, when they exist, are aggregate-only. This site does not claim certified compliance frameworks we have not published.",
  },
  {
    id: "security",
    title: "Security",
    body: "Authentication is handled by the canonical application, not by this website. We do not publish SOC 2, ISO or similar certifications on this page because they are not established here. To report a security concern, write to the general contact address and mark the subject as a security report.",
  },
  {
    id: "responsible-ai",
    title: "Responsible AI",
    body: "Athena and related AI surfaces are designed as assistance tools. Humans decide. AI output is not a substitute for professional, legal or hiring judgment. Capabilities continue to expand and are not claimed as universally live.",
  },
  {
    id: "accessibility",
    title: "Accessibility",
    body: "This website aims to support keyboard navigation, skip-to-content, visible focus, semantic headings and reduced-motion fallbacks for the WebGL hero. We are not claiming a completed WCAG audit. If something blocks you, write to us.",
  },
];

const TERMS = [
  {
    id: "terms",
    title: "What this statement is",
    body: "These are informational terms for use of the public AskTrabaajo website. They are not a substitute for counsel-reviewed terms of service. The canonical application may present additional terms when you register.",
  },
  {
    id: "use",
    title: "Use of this website",
    body: "You may browse this site to learn about AskTrabaajo. Do not attempt to disrupt the site, scrape it aggressively, or misrepresent an affiliation with AskTrabaajo.",
  },
  {
    id: "accounts-terms",
    title: "Platform accounts",
    body: "Creating an account, posting jobs, or using Work ID happens on the canonical application. This website does not operate a second authentication system.",
  },
  {
    id: "accuracy",
    title: "Accuracy and development status",
    body: "The product is in active development. Audience pages mark what is available, in development, coming, or vision. Do not treat vision language as a live service, SLA, or partnership claim.",
  },
  {
    id: "warranty",
    title: "No warranty",
    body: "The public website is provided as-is. We do not warrant uninterrupted availability or that descriptions of future capabilities will ship on any date.",
  },
  {
    id: "contact-terms",
    title: "Contact",
    body: `Questions: ${SITE.contact.general}.`,
  },
];

export const LegalPage = ({ kind }) => {
  const { hash } = useLocation();
  const isPrivacy = kind === "privacy";
  const sections = isPrivacy ? PRIVACY : TERMS;

  usePageMeta({
    title: isPrivacy ? "Privacy" : "Terms",
    description: isPrivacy
      ? "Informational privacy statement for the public AskTrabaajo website."
      : "Informational terms for use of the public AskTrabaajo website.",
  });

  useEffect(() => {
    if (hash) {
      const t = setTimeout(() => scrollToId(hash), 80);
      return () => clearTimeout(t);
    }
    window.scrollTo(0, 0);
    return undefined;
  }, [hash, kind]);

  return (
    <PublicPage testId={`legal-page-${kind}`}>
      <PageHero
        eyebrow={isPrivacy ? "Privacy & trust" : "Terms"}
        title={isPrivacy ? "PRIVACY,\nSTATED HONESTLY." : "TERMS OF\nTHIS WEBSITE."}
        copy={
          isPrivacy
            ? "How this public site treats information — and what we will not claim."
            : "The rules for using this public website while the platform is in active development."
        }
      />

      <section className="pb-24 sm:pb-32">
        <div className="mx-auto max-w-3xl px-5 sm:px-8 space-y-10">
          {sections.map((s, i) => (
            <Reveal key={s.id} delay={i * 0.04}>
              <article id={s.id}>
                <h2 className="font-display text-2xl text-slate-100">{s.title}</h2>
                <p className="mt-3 text-mist leading-relaxed">{s.body}</p>
              </article>
            </Reveal>
          ))}
          <p className="text-sm text-faint">
            Write to{" "}
            <a className="text-gold-soft hover:underline" href={mailto(SITE.contact.general, isPrivacy ? "Privacy" : "Terms")}>
              {SITE.contact.general}
            </a>
            .
          </p>
        </div>
      </section>
    </PublicPage>
  );
};

export default LegalPage;
