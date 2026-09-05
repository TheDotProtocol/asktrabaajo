"use client";

import { useEffect, useMemo, useState } from "react";
import { useLocation } from "@/marketing/compat/router";
import { Mail } from "lucide-react";
import Reveal from "@/marketing/components/common/Reveal";
import { GoldButton, GhostButton } from "@/marketing/components/common/Buttons";
import { PublicPage, PageHero } from "@/marketing/components/common/PublicPage";
import { usePageMeta } from "@/marketing/hooks/usePageMeta";
import { SITE, mailto, scrollToId } from "@/marketing/config/site";

const TOPICS = [
  { id: "general", label: "General enquiries", email: SITE.contact.general, subject: "Hello AskTrabaajo" },
  { id: "jobseekers", label: "Jobseekers", email: SITE.contact.access, subject: "Jobseeker enquiry" },
  { id: "employers", label: "Employers", email: SITE.contact.access, subject: "Employer enquiry" },
  { id: "government", label: "Government", email: SITE.contact.government, subject: "Government enquiry" },
  { id: "partnerships", label: "Partnerships", email: SITE.contact.partnerships, subject: "Partnership enquiry" },
  { id: "investors", label: "Investors", email: SITE.contact.general, subject: "Investor enquiry" },
];

const CHANNELS = [
  { label: "General", email: SITE.contact.general, note: "The public contact address." },
  { label: "Jobseekers & employers", email: SITE.contact.access, note: "Questions about entering the platform." },
  { label: "Partnerships", email: SITE.contact.partnerships, note: "Collaboration and institutional conversations." },
  { label: "Government", email: SITE.contact.government, note: "Public-institution conversations." },
  { label: "Press", email: SITE.contact.press, note: "Editorial and media requests." },
];

export const ContactPage = () => {
  usePageMeta({
    title: "Contact",
    description: "Contact AskTrabaajo for general, jobseeker, employer, government, partnership and investor enquiries.",
  });

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [organization, setOrganization] = useState("");
  const [topicId, setTopicId] = useState("general");
  const [message, setMessage] = useState("");
  const [attempted, setAttempted] = useState(false);
  const { hash } = useLocation();

  useEffect(() => {
    if (hash) {
      const t = setTimeout(() => scrollToId(hash), 80);
      return () => clearTimeout(t);
    }
    window.scrollTo(0, 0);
    return undefined;
  }, [hash]);

  const topic = TOPICS.find((t) => t.id === topicId) || TOPICS[0];

  const composeHref = useMemo(() => {
    const lines = [
      message.trim() || "(Write your message here.)",
      "",
      name.trim() ? `Name: ${name.trim()}` : "",
      email.trim() ? `Email: ${email.trim()}` : "",
      organization.trim() ? `Organization: ${organization.trim()}` : "",
    ].filter(Boolean);
    return mailto(topic.email, topic.subject, lines.join("\n"));
  }, [email, message, name, organization, topic.email, topic.subject]);

  const onSubmit = (e) => {
    e.preventDefault();
    setAttempted(true);
  };

  return (
    <PublicPage testId="contact-page">
      <PageHero
        eyebrow="Contact"
        title={"WRITE TO\nASKTRABAAJO."}
        copy="Official email is the supported public channel. We do not publish a phone number, office address or response-time guarantee. We read messages sent to these addresses."
      />

      <section className="pb-20 sm:pb-28">
        <div className="mx-auto max-w-7xl px-5 sm:px-8 grid lg:grid-cols-12 gap-10">
          <div className="lg:col-span-5 space-y-4">
            {CHANNELS.map((c) => (
              <a
                key={c.email}
                href={mailto(c.email, `${c.label} — AskTrabaajo`)}
                data-testid={`contact-channel-${c.label.toLowerCase()}`}
                className="block card-surface p-5 hover:border-gold/40 transition-colors"
              >
                <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">{c.label}</p>
                <p className="mt-2 font-display text-lg text-slate-100 flex items-center gap-2">
                  <Mail className="w-4 h-4 text-gold-soft" aria-hidden="true" />
                  {c.email}
                </p>
                <p className="mt-2 text-sm text-mist">{c.note}</p>
              </a>
            ))}
            <p className="text-sm text-faint leading-relaxed">
              Phone numbers and office locations are not published because they are
              not officially confirmed for this site.
            </p>
          </div>

          <div className="lg:col-span-7">
            <Reveal>
              <form
                id="contact-form"
                data-testid="contact-form"
                onSubmit={onSubmit}
                className="card-surface p-6 sm:p-8 space-y-5"
                noValidate
              >
                <div>
                  <h2 className="font-display text-2xl text-silver-grad">Message</h2>
                  <p className="mt-2 text-sm text-mist leading-relaxed">
                    This website does not send messages through a hosted form.
                    Compose an email, or write directly to the addresses on the left.
                  </p>
                </div>

                <label className="block">
                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">Name</span>
                  <input
                    type="text"
                    name="name"
                    autoComplete="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="mt-2 w-full bg-ink/60 border border-white/10 rounded-sm px-3 py-2.5 text-sm text-slate-100"
                  />
                </label>

                <label className="block">
                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">Your email</span>
                  <input
                    type="email"
                    name="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="mt-2 w-full bg-ink/60 border border-white/10 rounded-sm px-3 py-2.5 text-sm text-slate-100"
                  />
                </label>

                <label className="block">
                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">Organization (optional)</span>
                  <input
                    type="text"
                    name="organization"
                    autoComplete="organization"
                    value={organization}
                    onChange={(e) => setOrganization(e.target.value)}
                    className="mt-2 w-full bg-ink/60 border border-white/10 rounded-sm px-3 py-2.5 text-sm text-slate-100"
                  />
                </label>

                <label className="block">
                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">Topic</span>
                  <select
                    name="topic"
                    value={topicId}
                    onChange={(e) => setTopicId(e.target.value)}
                    className="mt-2 w-full bg-ink/60 border border-white/10 rounded-sm px-3 py-2.5 text-sm text-slate-100"
                  >
                    {TOPICS.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-faint">Message</span>
                  <textarea
                    name="message"
                    rows={6}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    className="mt-2 w-full bg-ink/60 border border-white/10 rounded-sm px-3 py-2.5 text-sm text-slate-100 resize-y"
                  />
                </label>

                <div className="flex flex-wrap gap-3">
                  <GoldButton href={composeHref} testId="contact-compose-email">
                    Open in email app
                  </GoldButton>
                  <GhostButton
                    href="#contact-form"
                    onClick={(e) => {
                      e.preventDefault();
                      setAttempted(true);
                    }}
                    testId="contact-submit-note"
                  >
                    About sending from this page
                  </GhostButton>
                </div>

                {attempted && (
                  <p
                    role="status"
                    data-testid="contact-provider-notice"
                    className="text-sm text-gold-soft leading-relaxed border border-gold/30 bg-gold/[0.06] rounded-sm px-4 py-3"
                  >
                    REQUIRES PRODUCTION EMAIL/FORM PROVIDER. This page will not
                    pretend a message was delivered. Use the official email addresses
                    or “Open in email app” until a production provider is connected.
                  </p>
                )}
              </form>
            </Reveal>

            <div id="careers" className="mt-10 card-surface p-6 sm:p-8">
              <h2 className="font-display text-xl text-slate-100">Careers</h2>
              <p className="mt-3 text-sm text-mist leading-relaxed">
                We are not publishing open roles on this website. If you want to
                talk about working with AskTrabaajo, write to{" "}
                <a className="text-gold-soft hover:underline" href={mailto(SITE.contact.general, "Careers enquiry")}>
                  {SITE.contact.general}
                </a>
                .
              </p>
            </div>
          </div>
        </div>
      </section>
    </PublicPage>
  );
};

export default ContactPage;
