#!/usr/bin/env node
/**
 * Print what the page draws beside one phase, from the fixture the in-flight
 * gate uses. A reader, not a gate: scripts/break-phase-span-merge.sh is what
 * asserts against it.
 *
 *     node scripts/read-phase-span.mjs "Destroy"
 */
import fs from "node:fs";
import path from "node:path";
import http from "node:http";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const SITE = path.join(ROOT, "site");
const FIXTURE = path.join(ROOT, "tests/fixtures/page-inflight");
const LAYER = path.join(FIXTURE, "layer");
const STATE = path.join(FIXTURE, "at-rest");
const MIME = { ".html": "text/html", ".json": "application/json", ".svg": "image/svg+xml" };

async function loadChromium() {
  for (const c of [path.join(ROOT, "tests/playwright/node_modules/playwright/index.js"),
                   path.join(ROOT, "tests/playwright/node_modules/@playwright/test/index.js")]) {
    if (!fs.existsSync(c)) continue;
    const m = await import(pathToFileURL(c).href);
    if (m.chromium || m.default?.chromium) return m.chromium || m.default.chromium;
  }
  console.error("read-phase-span: playwright is not installed where this expects it");
  process.exit(2);
}

const want = process.argv[2] || "Destroy";
const srv = http.createServer((q, r) => {
  const rel = decodeURIComponent(new URL(q.url, "http://x").pathname).replace(/^\/+/, "") || "index.html";
  let f = path.join(LAYER, rel);
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) f = path.join(SITE, rel);
  if (!f.startsWith(SITE) && !f.startsWith(LAYER)) { r.writeHead(403); r.end(); return; }
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404); r.end(); return; }
  r.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" });
  r.end(fs.readFileSync(f));
});
await new Promise((r) => srv.listen(0, "127.0.0.1", r));
const origin = "http://127.0.0.1:" + srv.address().port;
const meta = JSON.parse(fs.readFileSync(path.join(STATE, "meta.json"), "utf8"));
const launch = { args: ["--no-sandbox"] };
if (process.env.CHROMIUM_PATH) launch.executablePath = process.env.CHROMIUM_PATH;
const chromium = await loadChromium();
const b = await chromium.launch(launch);
const p = await (await b.newContext({ viewport: { width: 1512, height: 982 } })).newPage();
await p.clock.setFixedTime(new Date(meta.now));
await p.route("**/*", async (route) => {
  const u = route.request().url();
  if (u.startsWith(origin)) {
    const m = u.match(/\/status\/(stage|prod)\.json/);
    if (m) return route.fulfill({ status: 200, contentType: "application/json",
      body: fs.readFileSync(path.join(STATE, `status-${m[1]}.json`)) });
    return route.continue();
  }
  if (/lambda-url/.test(u)) return route.fulfill({ status: 200, contentType: "application/json",
    body: fs.readFileSync(path.join(STATE, "quota.json")) });
  if (u.startsWith("https://api.github.com/")) return route.fulfill({ status: 200,
    contentType: "application/json", headers: { "x-ratelimit-remaining": "57" },
    body: fs.readFileSync(path.join(STATE, /\/jobs(\?|$)/.test(u) ? "jobs.json" : "runs.json")) });
  return route.abort();
});
await p.goto(origin + "/index.html", { waitUntil: "load" });
await p.waitForLoadState("networkidle");
await p.waitForTimeout(600);
const out = await p.evaluate((label) => {
  const ph = [...document.querySelectorAll("#rows > .phase")]
    .find((x) => (x.querySelector("header b")?.textContent || "").includes(label));
  const was = ph?.querySelector("header .was");
  return { found: !!ph, span: was?.textContent.trim() || null, title: was?.getAttribute("title") || null };
}, want);
console.log(`${want}: ${out.span || "(no span drawn)"}`);
if (out.title) console.log(`  title: ${out.title}`);
await b.close(); srv.close();
