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
    body: "This is the public privacy statement for AskTrabaajo. It describes how this website and the AskTrabaajo application treat information. It is not a claim of a named regulatory certification.",
  },
  {
    id: "who",
    title: "Who we are",
    body: `AskTrabaajo is the public name of this employment operating system. Public contact: ${SITE.contact.general}.`,
  },
  {
    id: "website",
    title: "This public website",
    body: "Browsing this marketing site does not create an AskTrabaajo account. This site does not currently operate a hosted contact-form backend. If you email us, we receive the content you send (your address, message, and any details you include).",
  },
  {
    id: "accounts",
    title: "Accounts and the application",
    body: "Login, registration and platform data live on the AskTrabaajo application. Account, Work ID and organization data are governed by that application's rules.",
  },
  {
    id: "principles",
    title: "Design principles",
    body: "AskTrabaajo is designed around consent-controlled disclosure, tenant isolation, and data minimization. Government Workforce Intelligence is aggregate-only. This site does not claim certified compliance frameworks we have not published.",
  },
  {
    id: "security",
    title: "Security",
    body: "Authentication is handled by the AskTrabaajo application. We do not publish SOC 2, ISO or similar certifications on this page because they are not established here. To report a security concern, write to the general contact address and mark the subject as a security report.",
  },
  {
    id: "responsible-ai",
    title: "Responsible AI",
    body: "Athena and AI Interview are assistance tools. Humans decide. AI output is not a substitute for professional, legal or hiring judgment.",
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
    body: "These are the terms for use of the public AskTrabaajo website. The AskTrabaajo application may present additional terms when you register.",
  },
  {
    id: "use",
    title: "Use of this website",
    body: "You may browse this site to learn about AskTrabaajo. Do not attempt to disrupt the site, scrape it aggressively, or misrepresent an affiliation with AskTrabaajo.",
  },
  {
    id: "accounts-terms",
    title: "Platform accounts",
    body: "Creating an account, posting jobs, or using Work ID happens on the AskTrabaajo application. This website does not operate a second authentication system.",
  },
  {
    id: "accuracy",
    title: "Accuracy",
    body: "Public pages describe the AskTrabaajo platform as it exists. They are not an SLA, partnership announcement, or government endorsement.",
  },
  {
    id: "warranty",
    title: "No warranty",
    body: "The public website is provided as-is. We do not warrant uninterrupted availability.",
  },
  {
    id: "contact-terms",
    title: "Contact",
    body: `Questions: ${SITE.contact.general}.`,
  },
];

const PAYMENT = [
  {
    id: "scope",
    title: "What this policy covers",
    body: "This payment policy applies to billing surfaces inside the AskTrabaajo Employer OS and related finance operations. It does not invent a payment method, currency list, or processor that is not configured for your account.",
  },
  {
    id: "who-pays",
    title: "Who is billed",
    body: "Employer and organization accounts may be billed for platform subscriptions or related commercial services when those products are attached to the account. Jobseeker Work ID creation is not described here as a paid consumer checkout.",
  },
  {
    id: "how",
    title: "How payment is handled",
    body: "Charges, invoices and payment transactions are processed through the payment provider configured for the AskTrabaajo application. Secret keys never appear in this website. If live collection is not enabled for an environment, no production charge is taken.",
  },
  {
    id: "invoices",
    title: "Invoices and records",
    body: "Invoices and payment history, where issued, appear in the Employer billing area and in Super Admin finance operations for authorized operators.",
  },
  {
    id: "disputes",
    title: "Questions about a charge",
    body: `Write to ${SITE.contact.general} with the organization name and invoice or transaction reference. Do not send card numbers by email.`,
  },
];

const REFUND = [
  {
    id: "scope",
    title: "What this policy covers",
    body: "This refund policy applies when a charge has actually been collected through the configured AskTrabaajo payment provider. It does not promise a refund for a charge that was never taken.",
  },
  {
    id: "when",
    title: "When a refund may apply",
    body: "Refunds are considered for duplicate charges, billing errors, or other cases where the recorded transaction does not match the agreed service. Authorized finance operators process refunds through the application's finance tools when a refundable transaction exists.",
  },
  {
    id: "how",
    title: "How to request a refund",
    body: `Write to ${SITE.contact.general} with the organization name, invoice or transaction reference, and the reason. We do not publish a guaranteed turnaround time.`,
  },
  {
    id: "method",
    title: "How refunds are returned",
    body: "Approved refunds are returned through the same payment provider and original payment method where the provider supports it.",
  },
];

const COPY = {
  privacy: {
    title: "Privacy",
    eyebrow: "Privacy & trust",
    heading: "PRIVACY,\nSTATED HONESTLY.",
    intro: "How AskTrabaajo treats information — and what we will not claim.",
    description: "Privacy statement for the AskTrabaajo website and platform.",
    sections: PRIVACY,
  },
  terms: {
    title: "Terms",
    eyebrow: "Terms",
    heading: "TERMS OF\nTHIS WEBSITE.",
    intro: "The rules for using the public AskTrabaajo website.",
    description: "Terms for use of the public AskTrabaajo website.",
    sections: TERMS,
  },
  payment: {
    title: "Payment Policy",
    eyebrow: "Payment policy",
    heading: "HOW BILLING\nWORKS.",
    intro: "How AskTrabaajo handles invoices and payment transactions for organization accounts.",
    description: "Payment policy for AskTrabaajo organization billing.",
    sections: PAYMENT,
  },
  refund: {
    title: "Refund Policy",
    eyebrow: "Refund policy",
    heading: "REFUNDS,\nSTATED CLEARLY.",
    intro: "How refunds are requested and processed when a charge has actually been collected.",
    description: "Refund policy for AskTrabaajo billing.",
    sections: REFUND,
  },
};

export const LegalPage = ({ kind }) => {
  const { hash } = useLocation();
  const page = COPY[kind] || COPY.terms;

  usePageMeta({
    title: page.title,
    description: page.description,
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
      <PageHero eyebrow={page.eyebrow} title={page.heading} copy={page.intro} />

      <section className="pb-24 sm:pb-32">
        <div className="mx-auto max-w-3xl px-5 sm:px-8 space-y-10">
          {page.sections.map((s, i) => (
            <Reveal key={s.id} delay={i * 0.04}>
              <article id={s.id}>
                <h2 className="font-display text-2xl text-slate-100">{s.title}</h2>
                <p className="mt-3 text-mist leading-relaxed">{s.body}</p>
              </article>
            </Reveal>
          ))}
          <p className="text-sm text-faint">
            Write to{" "}
            <a className="text-gold-soft hover:underline" href={mailto(SITE.contact.general, page.title)}>
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
