"use client";

// Central configuration for outbound routes, public pages, and contact points.
// Do not hardcode localhost in production builds. Set origins via environment.

const CANONICAL = (process.env.NEXT_PUBLIC_APP_URL || "").replace(/\/$/, "");
const PUBLIC_SITE = (process.env.NEXT_PUBLIC_SITE_URL || "").replace(/\/$/, "");

function appPath(path) {
  if (!CANONICAL) return path;
  return `${CANONICAL}${path}`;
}

export const SITE = {
  name: "ASKTRABAAJO",
  legalName: "AskTrabaajo",
  tagline: "The Operating System for the World of Work",
  publicUrl: PUBLIC_SITE,
  urls: {
    app: appPath("/portals"),
    login: appPath("/login"),
    register: appPath("/register"),
    createWorkId: appPath("/register?intent=jobseeker"),
    startHiring: appPath("/register?intent=employer"),
    recruiter: appPath("/register?intent=employer"),
    government: appPath("/government"),
  },
  contact: {
    general: "hello@asktrabaajo.com",
    access: "access@asktrabaajo.com",
    partnerships: "partners@asktrabaajo.com",
    government: "gov@asktrabaajo.com",
    press: "press@asktrabaajo.com",
  },
  pages: {
    home: "/",
    about: "/about",
    contact: "/contact",
    privacy: "/privacy",
    terms: "/terms",
    paymentPolicy: "/payment-policy",
    refundPolicy: "/refund-policy",
    jobseekers: "/jobseekers",
    companies: "/companies",
    recruiters: "/recruiters",
    governments: "/governments",
    institutions: "/institutions",
  },
  social: {
    linkedin: "",
    x: "",
    youtube: "",
  },
};

export const mailto = (to, subject = "AskTrabaajo", body = "") => {
  const params = new URLSearchParams();
  if (subject) params.set("subject", subject);
  if (body) params.set("body", body);
  const query = params.toString();
  return query ? `mailto:${to}?${query}` : `mailto:${to}`;
};

export const scrollToId = (id) => {
  const el = document.querySelector(id);
  if (!el) return;
  if (window.__lenis) {
    window.__lenis.scrollTo(el, { offset: -72 });
  } else {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
};
