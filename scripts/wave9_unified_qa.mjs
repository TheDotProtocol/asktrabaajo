/**
 * Wave 9 unified app capture on localhost:3001.
 * Password is read from gitignored backend/.wave7-dev-account.
 */
import { createRequire } from "node:module";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(new URL("../wave6-qa/package.json", import.meta.url));
const { chromium } = require("playwright");

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "wave9-qa", "localhost");
const APP = "http://localhost:3001";
const EMAIL = "akumartrabaajo@gmail.com";

function readPassword() {
  const raw = readFileSync(join(ROOT, "backend", ".wave7-dev-account"), "utf8");
  const line = raw.split("\n").find((row) => row.startsWith("password="));
  if (!line) throw new Error("password missing from backend/.wave7-dev-account");
  return line.slice("password=".length).trim();
}

async function shot(page, name) {
  await page.waitForTimeout(700);
  await page.screenshot({ path: join(OUT, `${name}.png`), fullPage: true });
  console.log("captured", name);
}

async function assertNoLegacy(page) {
  const url = page.url();
  if (url.includes("localhost:3000")) {
    throw new Error(`legacy 3000 redirect: ${url}`);
  }
}

async function main() {
  mkdirSync(OUT, { recursive: true });
  const password = readPassword();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on("pageerror", (err) => console.log("pageerror", err.message));

  await page.goto(`${APP}/`, { waitUntil: "networkidle", timeout: 60000 });
  await assertNoLegacy(page);
  const hero = await page.locator("body").innerText();
  if (!hero.includes("OPERATING SYSTEM") && !hero.includes("AskTrabaajo")) {
    throw new Error("public website did not render");
  }
  if (hero.includes("80% Lower Cost")) {
    throw new Error("old fabricated homepage still visible");
  }
  await shot(page, "00-home");

  for (const [name, path] of [
    ["01-about", "/about"],
    ["02-jobseekers", "/jobseekers"],
    ["03-contact", "/contact"],
    ["04-login", "/login"],
  ]) {
    const res = await page.goto(`${APP}${path}`, { waitUntil: "networkidle", timeout: 45000 });
    if (res && res.status() >= 400) throw new Error(`${path} ${res.status()}`);
    await assertNoLegacy(page);
    await shot(page, name);
  }

  await page.locator("#email").fill(EMAIL);
  await page.locator("input[name=password]").fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/login"), { timeout: 20000 });
  await assertNoLegacy(page);
  await shot(page, "05-portals");

  for (const [name, path] of [
    ["06-jobseeker", "/jobseeker"],
    ["07-work-id", "/id/work-id"],
    ["08-career", "/jobseeker/career"],
    ["09-opportunities", "/jobseeker/opportunities"],
    ["10-applications", "/jobseeker/applications"],
    ["11-jobseeker-athena", "/jobseeker/athena"],
    ["12-employer", "/company"],
    ["13-jobs", "/company/jobs"],
    ["14-talent", "/company/candidates"],
    ["15-pipeline", "/company/pipeline"],
    ["16-employer-athena", "/company/athena"],
    ["17-government", "/government"],
    ["18-workforce", "/government/workforce"],
    ["19-skills", "/government/skills"],
    ["20-geography", "/government/geography"],
    ["21-reports", "/government/reports"],
    ["22-gov-athena", "/government/athena"],
    ["23-admin", "/admin"],
    ["24-governance", "/admin/governance"],
    ["25-enforcement", "/admin/governance/enforcement"],
    ["26-appeals", "/admin/governance/appeals"],
    ["27-finance", "/admin/finance"],
  ]) {
    const res = await page.goto(`${APP}${path}`, { waitUntil: "networkidle", timeout: 45000 });
    if (res && res.status() >= 400) throw new Error(`${path} ${res.status()}`);
    await assertNoLegacy(page);
    await shot(page, name);
  }

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto(`${APP}/`, { waitUntil: "networkidle", timeout: 60000 });
  await shot(mobile, "m00-home");
  await mobile.goto(`${APP}/login`, { waitUntil: "networkidle", timeout: 45000 });
  await shot(mobile, "m01-login");

  await browser.close();
  console.log("WAVE9 UNIFIED QA: PASS");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
