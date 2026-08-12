#!/usr/bin/env node
/* ONE TAB, HELD OPEN, WHILE THE SOURCES UNDERNEATH IT CHANGE.
 *
 * An INSTRUMENT, not a gate: it prints observations and has no verdict, so it
 * is not in assets/gates.json and no break test is owed for it. What is owed is
 * trust, and the three properties below are what that trust rests on.
 *
 * WHY IT EXISTS. Phase 29 proved both ADR-0062 findings against a FIXTURE that
 * moves - the page loaded once and the layer swapped underneath it. A fixture
 * can do that because its clock and its documents are installed. Nothing in
 * this repository could do it against the LIVE page: watch-launch.sh polls AWS
 * and `gh` and never opens a browser, watch-convergence.sh measures S3 -> edge
 * over HTTP and never renders anything, and Phase 28 did it by hand - one tab,
 * a human, and frames copied out of it at 06:01, 06:04 and 06:08. Three glances
 * an hour cannot see a delay measured in seconds, and the human is the part
 * that does not survive a fifty-minute cycle.
 *
 * IT DOES NOT TOUCH THE NETWORK. It reads the rendered DOM and nothing else.
 * That is not tidiness: watch-convergence.sh's two high draws were its own
 * doing, because polling every two seconds keeps the edge warm and a write can
 * then never find it empty. An instrument that fetches is inside the thing it
 * measures. This one cannot warm the edge, cannot spend the page's 60 anonymous
 * requests, and cannot change the interval it is there to time.
 *
 * A RELOAD MUST BE IMPOSSIBLE TO MISTAKE FOR A RE-READ. The whole subject is
 * whether an OPEN page picks up a change; a page that quietly reloaded would
 * show the change and prove nothing. So a sentinel is installed on `window`
 * after the first load and asserted on every tick. If it is gone, the line says
 * SENTINEL-LOST rather than reporting the observation as if it counted.
 *
 * NOTHING PRINTS BLANK WHEN A READ FAILS. `state=` is what a node with no state
 * looks like; it is also what a crashed page, a detached frame and a renamed
 * selector look like, and this project has read nine empty lines as a clean
 * account once already. Every field is a value or ERR.
 *
 * RUN IT UNDER nohup. Phase 19g lost 2h46m out of the middle of the log it was
 * recording, to an SSH disconnect that took the foreground loop with it.
 *
 *   nohup node scripts/watch-page.mjs --minutes 90 \
 *     --out docs/sessions/$(date -u +%Y-%m-%d)-phase-N-cycle.log &
 *
 * Two files are written: <out> is the readable narrative, <out>.jsonl is every
 * tick in full, for anything that has to be re-derived afterwards.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function arg(name, fallback) {
  const i = process.argv.indexOf("--" + name);
  return i === -1 || i === process.argv.length - 1 ? fallback : process.argv[i + 1];
}

const URL_ = arg("url", "https://demo.uveapp.net");
const MINUTES = Number(arg("minutes", "90"));
const EVERY_MS = Number(arg("every", "5")) * 1000;
const HEARTBEAT_MS = Number(arg("heartbeat", "60")) * 1000;
const OUT = path.resolve(arg("out", path.join(ROOT, "watch-page.log")));

/* The gate's own extractor, verbatim from scripts/check-page-inflight.mjs. One
   definition would be better than two; a copy that DRIFTS would be worse than
   either, so the day this stops matching is the day it moves to a module. */
const OBSERVE = () => {
  const t = (el) => (el ? el.textContent.replace(/\s+/g, " ").trim() : null);
  return {
    sentinel: window.__watchPage || null,
    ratelimit: t(document.querySelector("#ratelimit")),
    autorefresh: t(document.querySelector("#autorefresh")),
    clockGitHub: t(document.querySelector("#clock-github")),
    clockBucket: t(document.querySelector("#clock-bucket")),
    mapSub: t(document.querySelector("#map-sub")),
    history: t(document.querySelector("#history-summary")),
    verdict: t(document.querySelector("#history-summary .verdict")),
    banner: (() => {
      const b = document.querySelector(".banner.bad");
      return b ? t(b).slice(0, 200) : null;
    })(),
    nodes: [...document.querySelectorAll(".node")]
      .filter((n) => n.dataset.id)
      .map((n) => ({
        id: n.dataset.id,
        word: n.dataset.word || "",
        state: t(n.querySelector(".nstate")),
        text: t(n)
      }))
  };
};

async function loadChromium() {
  const candidates = [
    path.join(ROOT, "tests/playwright/node_modules/playwright/index.js"),
    path.join(ROOT, "tests/playwright/node_modules/@playwright/test/index.js")
  ];
  for (const c of candidates) {
    if (!fs.existsSync(c)) continue;
    const mod = await import(pathToFileURL(c).href);
    const chromium = mod.chromium || (mod.default && mod.default.chromium);
    if (chromium) return chromium;
  }
  console.error("watch-page: no playwright under tests/playwright/node_modules.");
  console.error("  Run `npm ci` in tests/playwright.");
  process.exit(2);
}

/* The one sentence per node that this whole instrument exists to catch, and the
   figure it is attached to. Substrings rather than a parse: the page's wording
   is the subject, so reading it loosely would hide the thing being watched. */
function tense(text) {
  if (text === null) return "ERR";
  if (text.includes("the cycle under way")) return "under-way";
  if (text.includes("the cycle before this one")) return "previous";
  if (text.includes("not reached yet")) return "not-reached";
  if (text.includes("not run yet")) return "not-run";
  return "-";
}

const FIGURE = /(\d+m \d+s|\d+s)\b/;

function digest(o) {
  if (!o || o.error) return "ERR";
  return JSON.stringify([
    o.mapSub, o.verdict, o.banner,
    o.nodes.map((n) => [n.id, n.state, tense(n.text), (n.text || "").match(FIGURE)?.[0] || ""])
  ]);
}

function human(ts, o, note) {
  if (!o || o.error) return `${ts}  ERR  ${(o && o.error) || "no observation"}`;
  const sentinel = o.sentinel ? "tab-held" : "SENTINEL-LOST";
  const lines = [
    `${ts}  ${sentinel}  ${note}`,
    `    clocks    github ${o.clockGitHub ?? "ERR"} · bucket ${o.clockBucket ?? "ERR"}`,
    `    budget    ${o.ratelimit || "(none read — the page is on its fallback branch)"}`,
    `    cadence   ${o.autorefresh ?? "ERR"}`,
    `    map       ${o.mapSub ?? "ERR"}`,
    `    verdict   ${o.verdict ?? "ERR"}`
  ];
  if (o.banner) lines.push(`    BANNER    ${o.banner}`);
  for (const n of o.nodes) {
    const fig = (n.text || "").match(FIGURE)?.[0] || "";
    lines.push(`    ${n.id.padEnd(26)}${(n.state ?? "ERR").padEnd(14)}${tense(n.text).padEnd(12)}${fig}`);
  }
  return lines.join("\n");
}

const chromium = await loadChromium();
const browser = await chromium.launch();
const page = await browser.newPage();

const started = new Date();
const stamp = started.toISOString();

fs.mkdirSync(path.dirname(OUT), { recursive: true });
const log = fs.createWriteStream(OUT, { flags: "a" });
const jsonl = fs.createWriteStream(OUT + ".jsonl", { flags: "a" });
const say = (s) => { log.write(s + "\n"); console.log(s); };

say(`# watch-page ${stamp}`);
say(`# url ${URL_} · every ${EVERY_MS / 1000}s · heartbeat ${HEARTBEAT_MS / 1000}s · ${MINUTES}m`);
say(`# the page is loaded ONCE. Every line below is a re-read of that same tab,`);
say(`# and "tab-held" is the sentinel saying so. This instrument makes no network`);
say(`# request of its own, so it cannot warm the edge or spend the page's budget.`);
say("");

/* Installed BEFORE the first load, so it survives that load and every re-read
   after it. Installed after, it would prove only that nothing reloaded since
   the moment it was set, which is the question being asked. */
await page.addInitScript(`window.__watchPage = ${JSON.stringify(stamp)};`);
await page.goto(URL_, { waitUntil: "load", timeout: 60000 });

const deadline = Date.now() + MINUTES * 60000;
let last = null;
let lastPrint = 0;

while (Date.now() < deadline) {
  const ts = new Date().toISOString().replace("T", " ").slice(0, 19) + "Z";
  let o;
  try {
    o = await page.evaluate(OBSERVE);
  } catch (e) {
    o = { error: String(e).split("\n")[0].slice(0, 160) };
  }
  jsonl.write(JSON.stringify({ ts, o }) + "\n");

  const d = digest(o);
  const changed = last !== null && d !== last;
  const due = Date.now() - lastPrint >= HEARTBEAT_MS;

  if (last === null || changed || due) {
    say(human(ts, o, last === null ? "first frame" : changed ? "CHANGED" : "heartbeat"));
    say("");
    lastPrint = Date.now();
  }
  last = d;
  await page.waitForTimeout(EVERY_MS);
}

say(`# watch-page done ${new Date().toISOString()}`);
await browser.close();
log.end();
jsonl.end();
