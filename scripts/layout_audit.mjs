// Samples the overlay composition every STEP seconds via window.__audit(t) (defined in templates/overlay/index.html)
// and writes the boxes of every visible element. Driven by layout_audit.py; you rarely call this directly.
// Usage: node layout_audit.mjs <edit_dir/mg> <out.json> [step=0.5]
import { createRequire } from "module";
import { existsSync, readdirSync, writeFileSync } from "fs";
import { join, resolve } from "path";
import { homedir } from "os";

const require = createRequire(join(homedir(), ".config/meeting-to-video/node/package.json"));
const puppeteer = require("puppeteer-core");
const [mg, out, stepArg] = process.argv.slice(2);
const step = parseFloat(stepArg || "0.5");

function findChrome() {
  if (process.env.CHROME_PATH && existsSync(process.env.CHROME_PATH)) return process.env.CHROME_PATH;
  const base = join(homedir(), ".cache/hyperframes/chrome/chrome-headless-shell");   // downloaded by the first HyperFrames render
  if (existsSync(base)) for (const v of readdirSync(base)) for (const d of readdirSync(join(base, v))) {
    for (const exe of ["chrome-headless-shell", "chrome-headless-shell.exe"]) { const p = join(base, v, d, exe); if (existsSync(p)) return p; }
  }
  for (const p of ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"]) if (existsSync(p)) return p;
  throw new Error("No Chrome found: run one HyperFrames snapshot/render first, or set CHROME_PATH");
}

const browser = await puppeteer.launch({ executablePath: findChrome(), headless: true, args: ["--allow-file-access-from-files", "--no-sandbox"] });
const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080 });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
await page.goto("file://" + resolve(mg, "index.html"), { waitUntil: "load" });
await page.evaluate(() => document.fonts.ready);
const total = await page.evaluate(() => window.DATA.total);
const samples = [];
for (let t = 0; t <= total; t += step) samples.push({ t: +t.toFixed(2), els: await page.evaluate((tt) => window.__audit(tt), t) });
writeFileSync(out, JSON.stringify({ total, step, errors, samples }));
await browser.close();
console.log(`sampled ${samples.length} moments (${step}s apart)` + (errors.length ? `, page errors: ${errors.length}` : ""));
