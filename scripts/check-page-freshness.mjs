#!/usr/bin/env node
/**
 * THE GATE OVER WHEN THE PAGE ASKS.
 *
 * Phase 20k watched a live cycle with the dashboard open and found that the
 * words refreshed and the figures never did. `readRunLayer()` fetched the five
 * things the map draws numbers from and was called ONCE, in the bootstrap
 * chain; the poll read `status/*.json` and the Actions API. Four symptoms, one
 * root: a green promotion left its phase reading `not run yet`, a priced prod
 * teardown left its node the same way while the published record said
 * `measured` at 467s, prod's price could not reach the cost box, and the
 * Refresh button changed only the sentence around the old numbers. Three
 * minutes untouched did not converge. ONE HARD RELOAD FIXED ALL FOUR.
 *
 * That last sentence is the whole gate. The property is not "a fetch happens" -
 * a page can re-fetch and decline to draw, which is what the signature half of
 * ADR-0053 is about, and counting requests would have called that green. The
 * property is:
 *
 *     A TAB LEFT OPEN CONVERGES ON WHAT A FRESH LOAD OF THE SAME SOURCES SHOWS.
 *
 * So each case runs the page twice over the same fixtures. Session A opens on
 * `before`, the sources are swapped to `after` underneath it, and the clock is
 * pushed past one bucket tick. Session B loads `after` from cold. Their
 * renderings must be identical. Every defect 20k saw fails this: no re-read
 * leaves A showing `before`; a re-read whose result nothing re-draws leaves A
 * showing `before`; a sentence built in the bootstrap chain leaves A dated
 * `before`; and a layer that accumulates instead of being rebuilt leaves A with
 * a doubled ledger, which is not `after` either.
 *
 * WHY THIS CANNOT BE A LIFTED BLOCK. check-page-tense.mjs and
 * check-live-state.mjs pull a pure function out of the built page and hand it
 * data - they can say what the page ANSWERS, never when it asks. Freshness is
 * not a property of a block. It needs the clock, the listeners and the fetches,
 * so it needs the browser, and it borrows measure-page.mjs's harness: the same
 * chromium, the same static server, the same refusal on a request nobody
 * declared. What it does not borrow is measure-page's silence - that is a
 * measurement with no verdict, and this has one.
 *
 * THE CONTROL THAT MUST DIFFER. A fingerprint that never moves would make
 * `A === B` true of a page that renders nothing at all, so the fixtures are
 * required to disagree with each other first: `before` and `after` are rendered
 * cold and refused if they come out the same. This project has already built a
 * control that reproduced the defect it was controlling for (2026-08-05); the
 * cheap version of not doing that again is naming the thing that must differ
 * and then checking that it does.
 *
 *     node scripts/check-page-freshness.mjs
 *     node scripts/check-page-freshness.mjs --case clock    # or refresh, repeat
 *     node scripts/check-page-freshness.mjs --diff          # print the disagreement
 *
 * CHROMIUM_PATH= on a machine whose chromium is not the pinned build, exactly
 * as for measure-page.mjs and check-contrast.mjs.
 *
 * Exit status: 0 when every case converged, 1 when one did not, 2 when it
 * refused to measure at all.
 */
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SITE = path.join(ROOT, "site");
const FIXTURES = path.join(ROOT, "tests/fixtures/page-freshness");

// One bucket tick is 30s on the page. 35 is past it with room, and the wait
// after it is wall-clock rather than fake: fastForward fires the timer, the
// fetches that timer starts still have to come back.
const PAST_ONE_TICK = 35_000;
const SETTLE_MS = 600;
const VIEWPORT = { width: 1440, height: 900 };

function refuse(message) {
  console.error(`page-freshness: ${message}`);
  process.exit(2);
}

function arg(flag, fallback = null) {
  const i = process.argv.indexOf(flag);
  return i === -1 ? fallback : process.argv[i + 1];
}

// Same loader as measure-page.mjs and check-contrast.mjs: Playwright lives with
// the suites that use it, and guessing a location is not evidence.
async function loadChromium() {
  const candidates = [
    process.env.PLAYWRIGHT_MODULE,
    path.join(ROOT, "tests/playwright/node_modules/@playwright/test/index.js"),
    path.join(ROOT, "tests/playwright/node_modules/playwright/index.js")
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (!fs.existsSync(candidate)) continue;
    const mod = await import(pathToFileURL(candidate).href);
    const chromium = mod.chromium || (mod.default && mod.default.chromium);
    if (chromium) return chromium;
  }
  refuse(
    "Playwright is not installed where this expects it.\n" +
      "  Looked in: " + candidates.join(", ") + "\n" +
      "  Run `npm ci` in tests/playwright, or set PLAYWRIGHT_MODULE."
  );
}

function readJSON(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (e) {
    refuse(`${path.relative(ROOT, file)} is not readable JSON: ${e.message}`);
  }
}

/** The dashboard's own sources: status files and the Actions API. They are the
 *  SAME in both halves of every case on purpose. If they moved too, a
 *  convergence could be explained by the words rather than by the figures, and
 *  the figures are what this gate is about. */
function loadSources() {
  const dir = path.join(FIXTURES, "sources");
  if (!fs.existsSync(dir)) refuse(`${path.relative(ROOT, dir)} does not exist`);
  return {
    runs: readJSON(path.join(dir, "runs.json")),
    jobs: readJSON(path.join(dir, "jobs.json")),
    status: {
      stage: readJSON(path.join(dir, "status-stage.json")),
      prod: readJSON(path.join(dir, "status-prod.json"))
    }
  };
}

/** A run-layer set, as the bucket lays it out: the relative path a browser asks
 *  for maps to a file under the set's directory, and a file that is not there
 *  is a 404 - which is how the page sees an object no cycle has published. */
function loadLayer(name) {
  const dir = path.join(FIXTURES, name);
  if (!fs.existsSync(dir)) refuse(`no run-layer set called "${name}" in ${path.relative(ROOT, FIXTURES)}`);
  const files = new Map();
  const walk = (rel) => {
    for (const entry of fs.readdirSync(path.join(dir, rel), { withFileTypes: true })) {
      const next = rel ? `${rel}/${entry.name}` : entry.name;
      if (entry.isDirectory()) walk(next);
      else files.set(next, fs.readFileSync(path.join(dir, next), "utf8"));
    }
  };
  walk("");
  if (!files.size) refuse(`run-layer set "${name}" is empty. An empty set renders the page a cycle has never touched, which is not what any case here means.`);
  return files;
}

function serveSite() {
  const types = { ".html": "text/html", ".json": "application/json", ".svg": "image/svg+xml" };
  const server = http.createServer((req, res) => {
    const rel = decodeURIComponent(req.url.split("?")[0]).replace(/^\/+/, "");
    const file = path.join(SITE, rel);
    if (!file.startsWith(SITE) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      res.writeHead(404).end("not found");
      return;
    }
    res.writeHead(200, { "content-type": types[path.extname(file)] || "application/octet-stream" });
    res.end(fs.readFileSync(file));
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => resolve({ server, port: server.address().port }));
  });
}

/* WHAT IS COMPARED. Text, not pixels: this gate is about whether the page has
   the new numbers, and a layout question is measure-page.mjs's. The four
   regions are the four places 20k saw go stale - the map itself, the sentence
   under it that dates the cycle, the cost box that could not receive a price,
   and the disclosure cut whose ledger is a count.

   `.elapsed` is stripped because session A's clock has been pushed forward and
   session B's has not; an "8m 12s" that differs by the 35 seconds this gate
   itself advanced would be the instrument reading itself. */
const FINGERPRINT = () => {
  const clean = (el) => {
    if (!el) return "ABSENT";
    const copy = el.cloneNode(true);
    copy.querySelectorAll(".elapsed").forEach((e) => e.remove());
    return copy.textContent.replace(/\s+/g, " ").trim();
  };
  const box = document.querySelector("#cost-box");
  return {
    map: clean(document.querySelector("#rows")),
    sub: clean(document.querySelector("#map-sub")),
    cost: (box && box.hidden ? "HIDDEN " : "") + clean(document.querySelector("#cost-line")),
    detail: clean(document.querySelector("#detail-body")),
    banner: (() => {
      const b = document.querySelector(".banner.bad");
      return b ? b.textContent.replace(/\s+/g, " ").trim().slice(0, 200) : null;
    })()
  };
};

async function openPage(browser, origin, sources, layerRef, now) {
  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();
  // install(), not setFixedTime(): this gate has to be able to PUSH the clock
  // past a bucket tick, and a fixed time freezes the display without giving the
  // timers back.
  await page.clock.install({ time: new Date(now) });

  const unmocked = [];
  await page.route("**/*", async (route) => {
    const url = route.request().url();
    if (url.startsWith(origin)) {
      const rel = url.slice(origin.length).split("?")[0].replace(/^\/+/, "");
      if (/^status\/(stage|prod)\.json$/.test(rel)) {
        const env = rel.includes("stage") ? "stage" : "prod";
        return route.fulfill({ status: 200, contentType: "application/json",
                               body: JSON.stringify(sources.status[env]) });
      }
      // THE RUN LAYER, read through a REFERENCE rather than a captured value:
      // the swap below replaces what layerRef.files points at, and the page must
      // see the new set on its next ask without anything being re-registered.
      if (/^(timeline|results|cost)\//.test(rel)) {
        const body = layerRef.files.get(rel);
        if (body === undefined) return route.fulfill({ status: 404, body: "not found" });
        return route.fulfill({ status: 200, contentType: "application/json", body });
      }
      return route.continue();
    }
    if (url.startsWith("https://api.github.com/")) {
      const body = /\/jobs(\?|$)/.test(url) ? sources.jobs : sources.runs;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: {
          "x-ratelimit-remaining": "57",
          "x-ratelimit-reset": String(Math.floor(Date.parse(now) / 1000) + 1800)
        },
        body: JSON.stringify(body)
      });
    }
    unmocked.push(url);
    return route.abort();
  });

  await page.goto(origin + "/index.html", { waitUntil: "load" });
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(SETTLE_MS);
  return { page, context, unmocked };
}

const REGIONS = ["map", "sub", "cost", "detail"];

function disagreements(a, b) {
  return REGIONS.filter((k) => a[k] !== b[k]);
}

async function main() {
  if (!fs.existsSync(path.join(SITE, "index.html"))) {
    refuse("site/index.html does not exist. Run `make site-page` first.");
  }
  const chromium = await loadChromium();
  const sources = loadSources();
  const before = loadLayer("before");
  const after = loadLayer("after");
  const now = "2026-08-09T06:00:00Z";
  const showDiff = process.argv.includes("--diff");

  const wantedCase = arg("--case");
  const CASES = ["clock", "refresh", "repeat"];
  const cases = wantedCase ? CASES.filter((c) => c === wantedCase) : CASES;
  if (!cases.length) refuse(`no case called "${wantedCase}". Cases: ${CASES.join(", ")}`);

  const { server, port } = await serveSite();
  const origin = `http://127.0.0.1:${port}`;
  const launch = { args: ["--no-sandbox"] };
  if (process.env.CHROMIUM_PATH) launch.executablePath = process.env.CHROMIUM_PATH;
  const browser = await chromium.launch(launch);

  const cold = async (files) => {
    const ref = { files };
    const { page, context, unmocked } = await openPage(browser, origin, sources, ref, now);
    const fp = await page.evaluate(FINGERPRINT);
    await context.close();
    return { fp, unmocked };
  };

  let failed = 0;
  try {
    // THE CONTROL, first, and it is a refusal rather than a case: if the two
    // sets render the same page there is nothing for convergence to mean, and
    // every case below would pass without the page doing anything at all.
    const coldBefore = await cold(before);
    const coldAfter = await cold(after);
    for (const { unmocked } of [coldBefore, coldAfter]) {
      if (unmocked.length) {
        refuse("a request left the origin and nobody declared it:\n  " +
               [...new Set(unmocked)].join("\n  "));
      }
    }
    for (const [name, r] of [["before", coldBefore], ["after", coldAfter]]) {
      if (r.fp.banner) refuse(`the page drew a source-failure banner on "${name}": ${r.fp.banner}`);
    }
    // EVERY region, not "at least one", and the difference cost a break test.
    // The first version of this control asked whether the two sets rendered
    // differently ANYWHERE, and stayed green with renderMapSub() unhooked from
    // the re-read: a region nothing draws holds the same static markup in both
    // sessions, so it converges trivially and its silence looks like agreement.
    // A region that cannot move cannot testify - the same shape as the 20a
    // measurement that asked the document about a box overflowing its parent.
    const moved = disagreements(coldBefore.fp, coldAfter.fp);
    const mute = REGIONS.filter((k) => !moved.includes(k));
    if (mute.length) {
      refuse(
        `these regions render identically from the two run-layer sets: ${mute.join(", ")}.\n` +
          "  Convergence on something that never moved is not evidence, and a region\n" +
          "  the page has stopped drawing at all reads exactly like this. Either the\n" +
          "  fixtures no longer disagree about it, or nothing renders it any more."
      );
    }
    console.log(`control: before and after differ in ${moved.join(", ")} — every compared region can testify`);

    for (const name of cases) {
      const ref = { files: before };
      const { page, context, unmocked } = await openPage(browser, origin, sources, ref, now);
      const opened = await page.evaluate(FINGERPRINT);
      if (disagreements(opened, coldBefore.fp).length) {
        refuse(`case ${name}: the page did not open on "before". The harness is wrong, not the page.`);
      }

      // The cycle finishes and is torn down while the tab sits there.
      ref.files = after;

      let ticks = 1;
      if (name === "repeat") ticks = 3;
      for (let i = 0; i < ticks; i++) {
        if (name === "refresh") await page.click("#refresh");
        else await page.clock.fastForward(PAST_ONE_TICK);
        await page.waitForTimeout(SETTLE_MS);
      }

      const got = await page.evaluate(FINGERPRINT);
      if (unmocked.length) {
        refuse("a request left the origin and nobody declared it:\n  " +
               [...new Set(unmocked)].join("\n  "));
      }
      if (got.banner) refuse(`case ${name}: the page drew a source-failure banner: ${got.banner}`);

      const off = disagreements(got, coldAfter.fp);
      if (off.length) {
        failed++;
        console.log(`FAIL  ${name} — the open tab disagrees with a fresh load in: ${off.join(", ")}`);
        const stillBefore = off.filter((k) => got[k] === coldBefore.fp[k]);
        if (stillBefore.length) {
          console.log(`      ${stillBefore.join(", ")} still shows what was published BEFORE the cycle: ` +
                      `the page never asked again, or asked and did not draw.`);
        }
        if (showDiff) {
          for (const k of off) {
            console.log(`      --- ${k} open tab\n      ${got[k].slice(0, 600)}`);
            console.log(`      --- ${k} fresh load\n      ${coldAfter.fp[k].slice(0, 600)}`);
          }
        } else {
          console.log(`      re-run with --diff to see the disagreement`);
        }
      } else {
        const how = name === "refresh" ? "the Refresh button"
          : name === "repeat" ? "three ticks, and not a word doubled"
          : "one bucket tick";
        console.log(`ok    ${name} — ${how}: the open tab is what a reload would show`);
      }
      await context.close();
    }
  } finally {
    await browser.close();
    server.close();
  }

  if (failed) {
    console.log(`\npage-freshness-check: ${failed} of ${cases.length} cases left the reader holding old figures`);
    process.exit(1);
  }
  console.log(`\n${cases.length} cases: a tab left open shows what a reload would show`);
}

main();
