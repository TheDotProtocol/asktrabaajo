/**
 * Wave 7 public-website → login → portals capture.
 * Reads password from gitignored backend/.wave7-dev-account.
 * Run: node scripts/wave7_capture.mjs
 */
import { createRequire } from "node:module";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(new URL("../wave6-qa/package.json", import.meta.url));
const { chromium } = require("playwright");

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "wave7-qa", "localhost");
const WEBSITE = "http://localhost:3001";
const APP = "http://localhost:3000";
const EMAIL = "akumartrabaajo@gamail.com";

function readPassword() {
  const raw = readFileSync(join(ROOT, "backend", ".wave7-dev-account"), "utf8");
  const line = raw.split("\n").find((row) => row.startsWith("password="));
  if (!line) throw new Error("password missing from backend/.wave7-dev-account");
  return line.slice("password=".length).trim();
}

async function shot(page, name) {
  await page.waitForTimeout(600);
  await page.screenshot({ path: join(OUT, `${name}.png`), fullPage: true });
  console.log("captured", name);
}

async function main() {
  mkdirSync(OUT, { recursive: true });
  const password = readPassword();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on("pageerror", (err) => console.log("pageerror", err.message));

  await page.goto(WEBSITE, { waitUntil: "networkidle", timeout: 60000 });
  await shot(page, "01-website-home");

  const loginHref = await page.getAttribute("[data-testid=nav-login-cta]", "href");
  if (!loginHref || !loginHref.includes("/login")) {
    throw new Error(`Login CTA did not point at canonical login: ${loginHref}`);
  }
  await page.click("[data-testid=nav-login-cta]");
  await page.waitForURL((url) => url.pathname.startsWith("/login"), { timeout: 20000 });
  await shot(page, "02-canonical-login");

  await page.locator("#email").fill(EMAIL);
  await page.locator("input[name=password]").fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/login"), { timeout: 20000 });
  await shot(page, "03-portals");

  await page.goto(`${APP}/jobseeker`, { waitUntil: "networkidle" });
  await shot(page, "04-jobseeker");
  await page.goto(`${APP}/id/work-id`, { waitUntil: "networkidle" });
  await shot(page, "05-work-id");
  await page.goto(`${APP}/company`, { waitUntil: "networkidle" });
  await shot(page, "06-employer");
  await page.goto(`${APP}/government`, { waitUntil: "networkidle" });
  await shot(page, "07-government");

  await browser.close();
  console.log("WAVE7 CAPTURE: PASS");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
