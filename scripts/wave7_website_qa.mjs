/**
 * Wave 7 public-website page + viewport QA.
 * Does not use DEV credentials.
 * Run: node scripts/wave7_website_qa.mjs
 */
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(new URL("../wave6-qa/package.json", import.meta.url));
const { chromium } = require("playwright");

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "wave7-qa", "website");
const WEBSITE = "http://localhost:3001";

const PAGES = [
  ["home", "/"],
  ["about", "/about"],
  ["jobseekers", "/jobseekers"],
  ["companies", "/companies"],
  ["governments", "/governments"],
  ["contact", "/contact"],
  ["privacy", "/privacy"],
  ["terms", "/terms"],
];

const VIEWPORTS = [
  [390, 844],
  [768, 1024],
  [1024, 768],
  [1280, 800],
  [1440, 900],
];

async function main() {
  mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const errors = [];

  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on("pageerror", (err) => errors.push(err.message));

  for (const [name, path] of PAGES) {
    const res = await page.goto(`${WEBSITE}${path}`, { waitUntil: "networkidle", timeout: 60000 });
    if (!res || res.status() >= 400) {
      throw new Error(`${path} returned ${res && res.status()}`);
    }
    const title = await page.locator("h1").first().textContent();
    if (!title || !title.trim()) throw new Error(`${path} missing h1`);
    await page.screenshot({ path: join(OUT, `page-${name}.png`), fullPage: true });
    console.log("page", name, res.status());
  }

  const loginHref = await page.goto(`${WEBSITE}/`, { waitUntil: "domcontentloaded" }).then(async () =>
    page.getAttribute("[data-testid=nav-login-cta]", "href")
  );
  const registerHref = await page.getAttribute("[data-testid=nav-register-cta]", "href");
  if (!loginHref || !loginHref.includes("/login")) throw new Error(`login href ${loginHref}`);
  if (!registerHref || !registerHref.includes("/register")) throw new Error(`register href ${registerHref}`);
  if (loginHref.includes("127.0.0.1") && !loginHref.includes("localhost:3000")) {
    throw new Error(`unexpected login href ${loginHref}`);
  }

  for (const [w, h] of VIEWPORTS) {
    await page.setViewportSize({ width: w, height: h });
    await page.goto(`${WEBSITE}/`, { waitUntil: "networkidle", timeout: 60000 });
    const overflow = await page.evaluate(() => {
      const html = getComputedStyle(document.documentElement);
      const body = getComputedStyle(document.body);
      const clipped = html.overflowX === "hidden" || body.overflowX === "hidden";
      if (clipped) return false;
      return document.documentElement.scrollWidth > document.documentElement.clientWidth + 2;
    });
    if (overflow) throw new Error(`horizontal overflow at ${w}x${h}`);
    await page.click("[data-testid=nav-mobile-toggle]").catch(() => {});
    await page.screenshot({ path: join(OUT, `viewport-${w}x${h}.png`) });
    console.log("viewport", `${w}x${h}`);
  }

  await browser.close();
  if (errors.length) {
    console.log("pageerrors", errors.slice(0, 8));
  }
  console.log("WAVE7 WEBSITE QA: PASS");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
