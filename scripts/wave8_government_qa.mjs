/**
 * Wave 8 Government OS capture.
 * Reads password from gitignored backend/.wave7-dev-account.
 * Run: node scripts/wave8_government_qa.mjs
 */
import { createRequire } from "node:module";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(new URL("../wave6-qa/package.json", import.meta.url));
const { chromium } = require("playwright");

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "wave8-qa", "localhost");
const APP = "http://localhost:3000";
const EMAIL = "akumartrabaajo@gmail.com";

function readPassword() {
  const raw = readFileSync(join(ROOT, "backend", ".wave7-dev-account"), "utf8");
  const line = raw.split("\n").find((row) => row.startsWith("password="));
  if (!line) throw new Error("password missing from backend/.wave7-dev-account");
  return line.slice("password=".length).trim();
}

async function shot(page, name) {
  await page.waitForTimeout(800);
  await page.screenshot({ path: join(OUT, `${name}.png`), fullPage: true });
  console.log("captured", name);
}

async function main() {
  mkdirSync(OUT, { recursive: true });
  const password = readPassword();
  const browser = await chromium.launch({ headless: true });

  const desktop = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  desktop.on("pageerror", (err) => console.log("pageerror", err.message));

  await desktop.goto(`${APP}/login`, { waitUntil: "networkidle", timeout: 60000 });
  await desktop.locator("#email").fill(EMAIL);
  await desktop.locator("input[name=password]").fill(password);
  await desktop.getByRole("button", { name: /sign in/i }).click();
  await desktop.waitForURL((url) => !url.pathname.startsWith("/login"), { timeout: 20000 });
  await shot(desktop, "00-portals");

  for (const [name, path] of [
    ["01-command-center", "/government"],
    ["02-workforce", "/government/workforce"],
    ["03-skills", "/government/skills"],
    ["04-geography", "/government/geography"],
    ["05-industries", "/government/industries"],
    ["06-opportunities", "/government/opportunities"],
    ["07-companies", "/government/companies"],
    ["08-reports", "/government/reports"],
    ["09-athena", "/government/athena"],
    ["10-investment-future", "/government/investment"],
    ["11-settings", "/government/settings"],
    ["12-jobseeker-regression", "/jobseeker"],
    ["13-employer-regression", "/company"],
  ]) {
    const res = await desktop.goto(`${APP}${path}`, { waitUntil: "networkidle", timeout: 45000 });
    if (res && res.status() >= 400) throw new Error(`${path} ${res.status()}`);
    await shot(desktop, name);
  }

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto(`${APP}/login`, { waitUntil: "networkidle", timeout: 60000 });
  await mobile.locator("#email").fill(EMAIL);
  await mobile.locator("input[name=password]").fill(password);
  await mobile.getByRole("button", { name: /sign in/i }).click();
  await mobile.waitForURL((url) => !url.pathname.startsWith("/login"), { timeout: 20000 });
  for (const [name, path] of [
    ["m01-command-center", "/government"],
    ["m02-skills", "/government/skills"],
    ["m03-settings", "/government/settings"],
  ]) {
    const res = await mobile.goto(`${APP}${path}`, { waitUntil: "networkidle", timeout: 45000 });
    if (res && res.status() >= 400) throw new Error(`${path} ${res.status()}`);
    await shot(mobile, name);
  }

  await browser.close();
  console.log("WAVE8 GOVERNMENT QA: PASS");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
