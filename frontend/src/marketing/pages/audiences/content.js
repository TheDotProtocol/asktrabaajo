"use client";

import {
  Fingerprint, Network, Eye, Compass,
  Workflow, Users, ShieldCheck, Rocket,
  BadgeCheck, Send, Briefcase, Star,
  Landmark, EyeOff, Globe2, ScrollText,
  GraduationCap, Globe, Plug,
} from "lucide-react";
import { SITE, mailto } from "@/marketing/config/site";

export const AUDIENCE_PAGES = {
  jobseekers: {
    id: "jobseekers",
    eyebrow: "For Jobseekers",
    title: "YOUR CAREER,\nFINALLY IN ONE PLACE.",
    copy: "Jobseeker OS is the operating system for a professional life. Work ID, documents, credentials, Work DNA, assessments, Career Advisor, opportunities, applications, interviews, offers, learning and communications sit in one place.",
    chips: ["WORK ID", "TALENT GRAPH", "CAREER ADVISOR", "APPLICATIONS", "LEARNING"],
    features: [
      { icon: Fingerprint, title: "A persistent professional identity", copy: "Work ID connects your history, skills, credentials, documents and goals into one living record that travels with you — not with any employer or platform." },
      { icon: Network, title: "Matching that understands you", copy: "The Talent Graph aligns your skills, strengths and trajectory with opportunities — beyond keywords and job titles." },
      { icon: Eye, title: "No more black boxes", copy: "Applications, interviews and offers have a visible status. You always know where you stand." },
      { icon: Compass, title: "Guidance for what's next", copy: "Career Advisor, assessments and learning paths show where you are, what you can do, where you can go — and what to learn next." },
    ],
    steps: ["Create your Work ID", "Discover matched opportunities", "Interview and receive offers", "Grow — then find what's next"],
    quote: "Your career data belongs to you. AskTrabaajo is designed so you decide what is shared, with whom, and when — always.",
    cta: { primary: { label: "Create Your Work ID", href: SITE.urls.createWorkId }, secondary: { label: "Explore Work ID", href: "/#work-id" } },
  },

  companies: {
    id: "companies",
    eyebrow: "For Companies & HR Teams",
    title: "HIRING BECOMES\nA SYSTEM.",
    copy: "Employer OS is the operating system for hiring and workforce operations — company profile, jobs, Talent Graph discovery, pipeline, AI interviews, outreach, offers, onboarding, analytics and billing.",
    chips: ["JOBS", "TALENT GRAPH", "PIPELINE", "AI INTERVIEWS", "BILLING"],
    features: [
      { icon: Workflow, title: "One system of record", copy: "Organizations, jobs, candidates, pipelines, outreach and employment workflows in a single, auditable platform." },
      { icon: Users, title: "Discovery through the Talent Graph", copy: "Find people by skills, strengths and real trajectory — not by who optimized a resume for your keywords." },
      { icon: ShieldCheck, title: "Consent-based screening", copy: "Credential-aware screening where candidates control what is disclosed. Trust built into the workflow." },
      { icon: Rocket, title: "From offer to day one", copy: "Offers, documents, signatures and onboarding flow as one continuous process." },
    ],
    steps: ["Create the role", "Discover matched talent", "Interview with structure", "Offer, onboard and employ"],
    quote: "Disconnected hiring tools become one coherent system of record for employment.",
    cta: { primary: { label: "Start Hiring", href: SITE.urls.startHiring }, secondary: { label: "See the Employer OS", href: "/#company-os" } },
  },

  recruiters: {
    id: "recruiters",
    eyebrow: "For Independent Recruiters",
    title: "RECRUITING,\nWITH PROOF.",
    copy: "The AskTrabaajo recruiter network makes independent recruiters first-class participants in the employment operating system — verified talent, consent-based outreach, shared pipelines and a reputation that is portable.",
    chips: ["VERIFIED TALENT", "CONSENT-BASED OUTREACH", "SHARED PIPELINES", "PORTABLE REPUTATION"],
    features: [
      { icon: BadgeCheck, title: "Work with verified talent", copy: "Talent pools built on Work IDs with explicit credential states — you know what is verified before you reach out." },
      { icon: Send, title: "Outreach with consent", copy: "Contact flows through the platform communication layer. Professional for you, respectful for candidates." },
      { icon: Briefcase, title: "Shared client pipelines", copy: "Collaborate inside the same pipeline your client companies use — submissions, interviews, feedback and offers in one place." },
      { icon: Star, title: "Reputation that travels", copy: "Placements and outcomes become a verifiable track record attached to your professional identity on the network." },
    ],
    steps: ["Join and verify your identity", "Build verified talent pools", "Collaborate inside client pipelines", "Grow a portable reputation"],
    quote: "Recruiters are first-class participants in the network — with proof, not just promises.",
    cta: { primary: { label: "Join as a Recruiter", href: SITE.urls.recruiter }, secondary: { label: "Talk to Us", href: mailto(SITE.contact.access, "Recruiter access") } },
  },

  governments: {
    id: "governments",
    eyebrow: "For Governments & Public Institutions",
    title: "SEE THE LABOUR MARKET.\nNOT THE PRIVATE PERSON.",
    copy: "Government Workforce Intelligence is the public-institution operating system for aggregate labour-market insight — workforce, skills, geography, industries, opportunities, companies, reports and Government Athena — without exposing an individual professional identity.",
    chips: ["AGGREGATE ONLY", "SKILLS", "GEOGRAPHY", "INDUSTRIES", "REPORTS"],
    features: [
      { icon: Landmark, title: "Workforce and employment intelligence", copy: "Workforce, employment, freelance and entrepreneurial activity — understood as aggregate signals." },
      { icon: EyeOff, title: "Privacy-preserving by design", copy: "Governments see the market, never the person. No individual Work IDs, applications, documents, KYC or messages." },
      { icon: Globe2, title: "Geography, industry and opportunity", copy: "Country to city to industry to skill — plus company and opportunity intelligence for program design." },
      { icon: ScrollText, title: "Reports, exports and Athena", copy: "Skill-shortage, training-need and investment signals that inform education, employment and workforce programs." },
    ],
    steps: ["Enter Government OS", "Explore workforce and skills", "Read geography and industries", "Use reports and Government Athena"],
    quote: "Workforce intelligence without exposing individual professional identities — that constraint is architectural.",
    cta: { primary: { label: "Talk to Our Government Team", href: mailto(SITE.contact.government, "Government intelligence enquiry") }, secondary: { label: "Explore Workforce Intelligence", href: "/#government" } },
  },

  institutions: {
    id: "institutions",
    eyebrow: "For Institutions & Partners",
    title: "ISSUE CREDENTIALS\nTHAT TRAVEL.",
    copy: "Universities, certification bodies, licensing boards and employers issue education, certifications, employment and achievements directly to a person's Work ID — a professional credential layer that travels with the person.",
    chips: ["EDUCATION", "CERTIFICATIONS", "EMPLOYMENT", "ACHIEVEMENTS"],
    features: [
      { icon: GraduationCap, title: "Issue verifiable credentials", copy: "Attest qualifications directly to a person's Work ID, where they become portable proof instead of paper in a drawer." },
      { icon: Globe, title: "Credentials that travel", copy: "Your attestation follows the person across borders, employers and entire careers — with your institution's name attached." },
      { icon: ShieldCheck, title: "Clear states of trust", copy: "Verified, pending, unverified, expired, revoked — every state is explicit, so trust is never ambiguous." },
      { icon: Plug, title: "Built for institutional integrations", copy: "The credential layer connects issuing institutions to Work ID through a controlled issuance process." },
    ],
    steps: ["Partner with AskTrabaajo", "Issue attestations to Work IDs", "Credentials travel with people", "Stay in control — expire or revoke"],
    quote: "A credential should be as portable as the person who earned it.",
    cta: { primary: { label: "Become a Partner", href: mailto(SITE.contact.partnerships, "Institutional partnership") }, secondary: { label: "Explore Verified Credentials", href: "/#credentials" } },
  },
};

export const AUDIENCE_ORDER = ["jobseekers", "companies", "recruiters", "governments", "institutions"];
