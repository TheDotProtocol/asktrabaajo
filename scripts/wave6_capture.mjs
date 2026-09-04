/**
 * Wave 6 localhost visual capture. Isolated DEV accounts only.
 * Run: node scripts/wave6_capture.mjs
 */
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(new URL("../wave6-qa/package.json", import.meta.url));
const { chromium } = require("playwright");

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "wave6-qa", "localhost");
const BASE = "http://localhost:3000";
const PASS = "Wave6-dev-local!";

const VIEWPORTS = {
  desktop: { width: 1440, height: 900 },
  laptop: { width: 1280, height: 800 },
  tablet: { width: 768, height: 1024 },
  mobile: { width: 390, height: 844 },
};

async function shot(page, name) {
  await page.waitForTimeout(500);
  await page.screenshot({ path: join(OUT, `${name}.png`), fullPage: true });
  console.log("captured", name);
}

async function login(page, email) {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.fill("#email", email);
  await page.fill("#password", PASS);
  await page.click('button[type="submit"]');
  try {
    await page.waitForURL((url) => !url.pathname.startsWith("/login"), { timeout: 20000 });
  } catch (err) {
    await shot(page, `login_failed_${email.replace(/[^a-z0-9]+/g, "_")}`);
    throw err;
  }
}

async function tour(page, prefix, routes) {
  for (const route of routes) {
    const slug = route.replaceAll("/", "_").replace(/^_/, "") || "root";
    await page.goto(`${BASE}${route}`, { waitUntil: "networkidle" });
    await shot(page, `${prefix}_${slug}_1440`);
  }
}

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: VIEWPORTS.desktop });

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await shot(page, "auth_login_1440");
page.setViewportSize(VIEWPORTS.mobile);
await shot(page, "auth_login_390");
page.setViewportSize(VIEWPORTS.desktop);

await page.goto(`${BASE}/register`, { waitUntil: "networkidle" });
await shot(page, "auth_register_1440");
await page.goto(`${BASE}/forgot-password`, { waitUntil: "networkidle" });
await shot(page, "auth_forgot_1440");

await login(page, "dev+wave6.candidate@example.com");
await tour(page, "candidate", [
  "/jobseeker",
  "/id/work-id",
  "/jobseeker/documents",
  "/jobseeker/credentials",
  "/jobseeker/work-dna",
  "/jobseeker/career",
  "/jobseeker/opportunities",
  "/jobseeker/applications",
  "/jobseeker/interviews",
  "/jobseeker/ai-interview",
  "/jobseeker/interview-prep",
  "/jobseeker/offers",
  "/jobseeker/communications",
  "/jobseeker/notifications",
  "/jobseeker/privacy",
  "/jobseeker/athena",
]);
page.setViewportSize(VIEWPORTS.mobile);
await page.goto(`${BASE}/jobseeker`, { waitUntil: "networkidle" });
await shot(page, "candidate_jobseeker_390");
await page.goto(`${BASE}/jobseeker/athena`, { waitUntil: "networkidle" });
await shot(page, "candidate_athena_390");
page.setViewportSize(VIEWPORTS.desktop);

const ctx2 = await browser.newContext({ viewport: VIEWPORTS.desktop });
const emp = await ctx2.newPage();
await login(emp, "dev+wave6.employer@example.com");
await tour(emp, "employer", [
  "/company",
  "/company/profile",
  "/company/members",
  "/company/jobs",
  "/company/jobs/new",
  "/company/candidates",
  "/company/pipeline",
  "/company/interviews",
  "/employer/ai-interviews",
  "/company/offers",
  "/company/communications",
  "/company/analytics",
  "/company/notifications",
  "/employer/billing",
  "/company/settings",
  "/company/athena",
]);
await ctx2.close();

const ctx3 = await browser.newContext({ viewport: VIEWPORTS.desktop });
const adm = await ctx3.newPage();
await login(adm, "dev+wave6.admin@example.com");
await tour(adm, "admin", [
  "/admin",
  "/admin/governance",
  "/admin/governance/enforcement",
  "/admin/governance/appeals",
  "/admin/governance/audit",
  "/admin/governance/teams",
  "/admin/finance",
  "/admin/support",
  "/admin/operations",
  "/admin/athena",
  "/admin/notifications",
  "/admin/settings",
]);
await ctx3.close();

await browser.close();
console.log("WAVE6 CAPTURE DONE", OUT);
