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
    status: "AVAILABLE NOW",
    title: "YOUR CAREER,\nFINALLY IN ONE PLACE.",
    copy: "Your professional life shouldn't be scattered across a dozen platforms. Create a Work ID and enter the Candidate OS. Matching, interviews and career guidance continue to expand — we will not pretend every capability is finished.",
    chips: ["WORK ID", "GRAPH MATCHING", "APPLICATION TRACKING", "CAREER ADVISOR"],
    features: [
      { icon: Fingerprint, title: "A persistent professional identity", copy: "Work ID connects your history, skills, credentials and goals into one living record that travels with you — not with any employer or platform." },
      { icon: Network, title: "Matching that understands you", copy: "The Talent Graph aligns your skills and trajectory with opportunities that actually fit — beyond keywords and job titles." },
      { icon: Eye, title: "No more black boxes", copy: "Every application has a visible status, every step ahead is known. You'll always know exactly where you stand." },
      { icon: Compass, title: "Guidance for what's next", copy: "Career Advisor is designed to show where you are, what you can do, where you can go — and what to learn next." },
    ],
    steps: ["Create your Work ID", "Get matched by the graph", "Interview & receive offers", "Grow — then find what's next"],
    quote: "Your career data belongs to you. AskTrabaajo is designed so you decide what is shared, with whom, and when — always.",
    cta: { primary: { label: "Create Your Work ID", href: SITE.urls.createWorkId }, secondary: { label: "Explore Work ID", href: "/#work-id" } },
  },

  companies: {
    id: "companies",
    eyebrow: "For Companies & HR Teams",
    status: "AVAILABLE NOW",
    title: "HIRING BECOMES\nA SYSTEM.",
    copy: "The Company Employment OS is available in the application: roles, talent, pipelines, interviews and offers in one place. Graph-native discovery and every downstream workflow continue to expand — enter the platform to see what is live today.",
    chips: ["ROLE DESIGN", "GRAPH DISCOVERY", "STRUCTURED SCREENING", "ONBOARDING"],
    features: [
      { icon: Workflow, title: "One system of record", copy: "Organizations, jobs, candidates, pipelines, outreach and employment workflows in a single, auditable platform." },
      { icon: Users, title: "Discovery through the Talent Graph", copy: "Find people by verified skills and real trajectory — not by who optimised a resume for your keywords." },
      { icon: ShieldCheck, title: "Consent-based screening", copy: "Credential-aware screening where candidates explicitly control what is disclosed. Trust built in, not bolted on." },
      { icon: Rocket, title: "From offer to day one", copy: "Offers, document requests, signatures and onboarding flow as one continuous process — no hand-off chaos." },
    ],
    steps: ["Create the role", "Discover matched talent", "Interview with structure", "Offer, onboard & employ"],
    quote: "Twelve disconnected tools become one coherent system of record for employment.",
    cta: { primary: { label: "Start Hiring", href: SITE.urls.startHiring }, secondary: { label: "See the Company OS", href: "/#company-os" } },
  },

  recruiters: {
    id: "recruiters",
    eyebrow: "For Independent Recruiters",
    status: "COMING",
    title: "RECRUITING,\nWITH PROOF.",
    copy: "AskTrabaajo is designed to make independent recruiters first-class participants in the employment network — working with verified talent, consent-based outreach and shared pipelines, with a reputation that is provable and portable.",
    chips: ["VERIFIED TALENT POOLS", "CONSENT-BASED OUTREACH", "SHARED PIPELINES", "PORTABLE REPUTATION"],
    features: [
      { icon: BadgeCheck, title: "Work with verified talent", copy: "Talent pools built on Work IDs with real credential states — you know what is verified before you ever reach out." },
      { icon: Send, title: "Outreach with consent", copy: "Contact flows through the platform's controlled communication layer. Professional for you, respectful for candidates." },
      { icon: Briefcase, title: "Shared client pipelines", copy: "Collaborate inside the same pipeline your client companies use — submissions, feedback and offers in one place." },
      { icon: Star, title: "Reputation that travels", copy: "Placements and outcomes become a verifiable track record attached to your professional identity on the network." },
    ],
    steps: ["Join & verify your identity", "Build verified talent pools", "Collaborate inside client pipelines", "Grow a provable reputation"],
    quote: "Recruiters become first-class participants in the network — with proof, not just promises.",
    cta: { primary: { label: "Join as a Recruiter", href: SITE.urls.recruiter }, secondary: { label: "Talk to Us", href: mailto(SITE.contact.access, "Recruiter access") } },
  },

  governments: {
    id: "governments",
    eyebrow: "For Governments & Public Institutions",
    status: "OUR VISION",
    title: "SEE THE LABOUR MARKET.\nNOT THE PRIVATE PERSON.",
    copy: "The Government Employment Intelligence layer is designed to give public institutions a live, aggregate understanding of their labour market — employment flows, skill shortages and training needs — without ever exposing an individual professional identity.",
    chips: ["AGGREGATE ONLY", "SKILL SHORTAGES", "TRAINING NEEDS", "POLICY SIGNALS"],
    features: [
      { icon: Landmark, title: "Labour market intelligence", copy: "Total talent, employment, unemployment, freelance and entrepreneurial activity — understood as aggregate signals." },
      { icon: EyeOff, title: "Privacy-preserving by design", copy: "The architecture is designed so governments see the market, never the person. No individual-level exposure." },
      { icon: Globe2, title: "Regional drill-down", copy: "Country to state to city to industry to skill — understand exactly where workforce pressure is building." },
      { icon: ScrollText, title: "Evidence for policy", copy: "Skill shortage and training-need signals designed to inform education, migration and workforce programs." },
    ],
    steps: ["Define the region", "Explore industries & skills", "Identify shortages & surpluses", "Design targeted programs"],
    quote: "Workforce intelligence without exposing individual professional identities — that constraint is architectural, not a policy promise.",
    cta: { primary: { label: "Talk to Our Government Team", href: mailto(SITE.contact.government, "Government intelligence enquiry") }, secondary: { label: "Explore the Intelligence Layer", href: "/#government" } },
  },

  institutions: {
    id: "institutions",
    eyebrow: "For Institutions & Partners",
    status: "COMING",
    title: "ISSUE CREDENTIALS\nTHAT TRAVEL.",
    copy: "Universities, certification bodies, licensing boards and employers are designed to become issuers in the AskTrabaajo trust network — attesting education, certifications, employment and achievements directly to a person's Work ID.",
    chips: ["EDUCATION", "CERTIFICATIONS", "EMPLOYMENT", "ACHIEVEMENTS"],
    features: [
      { icon: GraduationCap, title: "Issue verifiable credentials", copy: "Attest qualifications directly to a person's Work ID, where they become portable proof instead of paper in a drawer." },
      { icon: Globe, title: "Credentials that travel", copy: "Your attestation follows the person across borders, employers and entire careers — with your institution's name attached." },
      { icon: ShieldCheck, title: "Clear states of trust", copy: "Verified, pending, unverified, expired, revoked — every state is explicit, so trust is never ambiguous." },
      { icon: Plug, title: "Built for future integrations", copy: "The credential layer is designed to support institutional integrations — onboarding partners progressively, never claiming coverage we don't have." },
    ],
    steps: ["Partner with AskTrabaajo", "Issue attestations to Work IDs", "Credentials travel with people", "Stay in control — expire or revoke"],
    quote: "A credential should be as portable as the person who earned it.",
    cta: { primary: { label: "Become a Partner", href: mailto(SITE.contact.partnerships, "Institutional partnership") }, secondary: { label: "Explore Verified Credentials", href: "/#credentials" } },
  },
};

export const AUDIENCE_ORDER = ["jobseekers", "companies", "recruiters", "governments", "institutions"];
