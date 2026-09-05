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
    copy: "Your professional life belongs in one system. Create a Work ID and enter Jobseeker OS — identity, career, opportunities, applications, interviews, offers and Athena in one place.",
    chips: ["WORK ID", "TALENT GRAPH", "APPLICATIONS", "CAREER ADVISOR"],
    features: [
      { icon: Fingerprint, title: "A persistent professional identity", copy: "Work ID connects your history, skills, credentials and goals into one living record that travels with you — not with any employer or platform." },
      { icon: Network, title: "Matching that understands you", copy: "The Talent Graph aligns your skills and trajectory with opportunities that fit — beyond keywords and job titles." },
      { icon: Eye, title: "No more black boxes", copy: "Every application has a visible status. You always know where you stand." },
      { icon: Compass, title: "Guidance for what's next", copy: "Career Advisor shows where you are, what you can do, where you can go — and what to learn next." },
    ],
    steps: ["Create your Work ID", "Discover opportunities", "Interview and receive offers", "Grow — then find what's next"],
    quote: "Your career data belongs to you. AskTrabaajo is designed so you decide what is shared, with whom, and when — always.",
    cta: { primary: { label: "Create Your Work ID", href: SITE.urls.createWorkId }, secondary: { label: "Explore Work ID", href: "/#work-id" } },
  },

  companies: {
    id: "companies",
    eyebrow: "For Companies & HR Teams",
    title: "HIRING BECOMES\nA SYSTEM.",
    copy: "The Employer OS is the system of record for hiring: roles, talent, pipelines, interviews, offers, outreach and billing in one place.",
    chips: ["JOBS", "TALENT", "PIPELINE", "OFFERS"],
    features: [
      { icon: Workflow, title: "One system of record", copy: "Organizations, jobs, candidates, pipelines, outreach and employment workflows in a single, auditable platform." },
      { icon: Users, title: "Discovery through the Talent Graph", copy: "Find people by skills and real trajectory — not by who optimized a resume for your keywords." },
      { icon: ShieldCheck, title: "Consent-based screening", copy: "Candidates control what is disclosed. Trust is built into the workflow." },
      { icon: Rocket, title: "From offer to day one", copy: "Offers, documents and onboarding sit in one continuous process." },
    ],
    steps: ["Create the role", "Discover talent", "Interview with structure", "Offer and employ"],
    quote: "Disconnected hiring tools become one coherent system of record for employment.",
    cta: { primary: { label: "Start Hiring", href: SITE.urls.startHiring }, secondary: { label: "See the Employer OS", href: "/#company-os" } },
  },

  recruiters: {
    id: "recruiters",
    eyebrow: "For Hiring Professionals",
    title: "HIRE THROUGH\nTHE EMPLOYER OS.",
    copy: "Independent recruiters and hiring professionals use the same Employer OS as in-house teams — jobs, talent, pipelines, interviews, offers and communication on AskTrabaajo.",
    chips: ["JOBS", "TALENT", "PIPELINE", "COMMUNICATION"],
    features: [
      { icon: BadgeCheck, title: "Work inside the employment OS", copy: "Create roles, review candidates and move people through a structured pipeline — the same system employers use." },
      { icon: Send, title: "Outreach with control", copy: "Contact flows through the platform communication layer. Professional for you, respectful for candidates." },
      { icon: Briefcase, title: "Shared hiring workflows", copy: "Submissions, interviews, feedback and offers stay in one auditable place." },
      { icon: Star, title: "One identity for the work", copy: "You enter AskTrabaajo with the same account model as every other professional on the platform." },
    ],
    steps: ["Register", "Enter the Employer OS", "Create roles and pipelines", "Hire through one system"],
    quote: "Hiring professionals work inside the same operating system as the employers they serve.",
    cta: { primary: { label: "Start Hiring", href: SITE.urls.recruiter }, secondary: { label: "Talk to Us", href: mailto(SITE.contact.access, "Hiring professional enquiry") } },
  },

  governments: {
    id: "governments",
    eyebrow: "For Governments & Public Institutions",
    title: "SEE THE LABOUR MARKET.\nNOT THE PRIVATE PERSON.",
    copy: "Government Workforce Intelligence gives public institutions an aggregate understanding of skills, employment, geography, industries, opportunities and companies — without exposing an individual professional identity.",
    chips: ["AGGREGATE ONLY", "SKILLS", "GEOGRAPHY", "REPORTS"],
    features: [
      { icon: Landmark, title: "Workforce intelligence", copy: "Workforce, employment, industries and opportunity — understood as aggregate signals." },
      { icon: EyeOff, title: "Privacy-preserving by design", copy: "Governments see the market, never the person. No individual Work IDs, applications, documents or messages." },
      { icon: Globe2, title: "Regional drill-down", copy: "Country to geography to industry to skill — understand where workforce pressure concentrates." },
      { icon: ScrollText, title: "Evidence for programs", copy: "Skill and opportunity signals that inform education, employment and workforce programs." },
    ],
    steps: ["Enter Government OS", "Explore workforce and skills", "Read geography and industries", "Use reports and Athena"],
    quote: "Workforce intelligence without exposing individual professional identities — that constraint is architectural.",
    cta: { primary: { label: "Talk to Our Government Team", href: mailto(SITE.contact.government, "Government intelligence enquiry") }, secondary: { label: "Explore Workforce Intelligence", href: "/#government" } },
  },

  institutions: {
    id: "institutions",
    eyebrow: "For Institutions & Partners",
    title: "CREDENTIALS LIVE\nON WORK ID.",
    copy: "Education, certification, employment and achievement records sit on a person's Work ID with explicit trust states. Institutions that want to work with AskTrabaajo can write to us — we do not claim a live issuer network that is not in the product.",
    chips: ["WORK ID", "CREDENTIALS", "TRUST STATES", "PARTNERSHIP"],
    features: [
      { icon: GraduationCap, title: "Records that travel with the person", copy: "Credentials are part of Work ID, not trapped in a single employer portal." },
      { icon: Globe, title: "Clear states of trust", copy: "Verified, pending, unverified, expired, revoked — every state is explicit." },
      { icon: ShieldCheck, title: "Consent-controlled disclosure", copy: "People decide what is shared, with whom, and when." },
      { icon: Plug, title: "Talk to us about partnership", copy: "If your institution wants to work with AskTrabaajo, use the partnership contact. We do not invent coverage we do not operate." },
    ],
    steps: ["Write to AskTrabaajo", "Describe the collaboration", "Review how Work ID holds records", "Work through an agreed process"],
    quote: "A credential should be as portable as the person who earned it — and never labelled verified when it is not.",
    cta: { primary: { label: "Become a Partner", href: mailto(SITE.contact.partnerships, "Institutional partnership") }, secondary: { label: "Explore Credentials", href: "/#credentials" } },
  },
};

export const AUDIENCE_ORDER = ["jobseekers", "companies", "governments"];
