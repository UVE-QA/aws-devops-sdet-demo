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

/* WHAT A NODE CAN SAY ABOUT WHOSE CYCLE ITS FIGURES ARE, taken from nodeTense()
   in site/index.html rather than from memory. The first at-rest frame this
   instrument ever took printed "-" for all thirty-six nodes: it had been written
   knowing only the two wordings Phase 29's FIXTURE uses, and the live page at
   rest says a third. A column that cannot name what it is looking at does not
   read as broken, it reads as "nothing to report".

   `under-way` and `PREVIOUS` are the two branches ADR-0062 D1 is about, and
   telling them apart on a live node is the whole point of watching. PREVIOUS is
   shouted because on a node whose figures the run in flight has just published,
   it is the defect. */
const QUALIFIERS = [
  ["these figures are from the cycle under way", "under-way"],
  ["these figures are from the cycle before this one", "PREVIOUS"],
  ["these figures are from the cycle that ended", "ended"],
  ["a cycle is under way and has not got here", "not-reached"]
];

function qualifier(text) {
  if (typeof text !== "string") return "";
  for (const [needle, name] of QUALIFIERS) if (text.includes(needle)) return name;
  return "";
}

/* `5.8s` is a figure; `8s` is the tail of one. The first version of this read
   the second out of the first and printed it in the figure column beside a state
   that plainly said 5.8s. Minutes come first in the alternation, or `8m 36s` is
   read as `36s` - the same mistake one unit up. */
const FIGURE = /\b\d+m \d+s\b|\b\d+(?:\.\d+)?s\b/;

/* MISSING IS NOT FAILED. The first frame printed ERR for six permanent levels
   and both outputs, and none of them had failed: nodeEl() returns no `.nstate`
   child at all for that branch, so there is nothing to read. The header of this
   file demands that a failed read never print blank; this is the other half of
   the same rule, and it was got wrong in the first version. ERR is reserved for
   the one thing that IS a failure - page.evaluate() throwing, which loses the
   whole frame and says so on its own line. */
const dash = (s) => (s === null || s === undefined || s === "" ? "—" : s);

const rows = (o) =>
  o.nodes.map((n) => ({
    id: n.id,
    word: n.word || "",
    qual: qualifier(n.text),
    fig: (typeof n.text === "string" && n.text.match(FIGURE)?.[0]) || ""
  }));

function digest(o) {
  if (!o || o.error) return "ERR";
  return JSON.stringify([o.mapSub, o.verdict, o.banner,
    rows(o).map((r) => [r.id, r.word, r.qual, r.fig])]);
}

const fmtRow = (r) =>
  `    ${r.id.padEnd(24)}${dash(r.word).padEnd(18)}${dash(r.qual).padEnd(14)}${dash(r.fig)}`;

function human(ts, o, note, prev) {
  if (!o || o.error) return `${ts}  ERR  ${(o && o.error) || "no observation"}`;
  const sentinel = o.sentinel ? "tab-held" : "SENTINEL-LOST";
  const lines = [
    `${ts}  ${sentinel}  ${note}`,
    `    clocks    github ${dash(o.clockGitHub)} · bucket ${dash(o.clockBucket)}`,
    `    budget    ${o.ratelimit || "(none read — the page is on its fallback branch)"}`,
    `    cadence   ${dash(o.autorefresh)}`,
    `    map       ${dash(o.mapSub).slice(0, 200)}`,
    `    verdict   ${dash(o.verdict)}`
  ];
  if (o.banner) lines.push(`    BANNER    ${o.banner}`);

  /* A changed frame prints WHAT MOVED, and says how much did not. Thirty-six
     unchanged rows under a one-node change is how a log stops being read - and
     the node that moved is the observation. */
  const now = rows(o);
  const show = prev
    ? now.filter((r) => {
        const p = prev.get(r.id);
        return !p || p.word !== r.word || p.qual !== r.qual || p.fig !== r.fig;
      })
    : now;
  for (const r of show) {
    const p = prev && prev.get(r.id);
    lines.push(p ? `${fmtRow(r)}   was: ${dash(p.word)} · ${dash(p.qual)} · ${dash(p.fig)}` : fmtRow(r));
  }
  if (prev) lines.push(`    (${now.length - show.length} of ${now.length} nodes unchanged)`);
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
let prevRows = null;

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
    const label = last === null ? "first frame" : changed ? "CHANGED" : "heartbeat";
    /* A heartbeat prints in full: a reader arriving at one should not have to
       reconstruct the state from every change above it. Only a CHANGED frame
       is a diff, and only it has something to diff against. */
    say(human(ts, o, label, changed ? prevRows : null));
    say("");
    lastPrint = Date.now();
    if (!o.error) prevRows = new Map(rows(o).map((r) => [r.id, r]));
  }
  last = d;
  await page.waitForTimeout(EVERY_MS);
}

say(`# watch-page done ${new Date().toISOString()}`);
await browser.close();
log.end();
jsonl.end();
