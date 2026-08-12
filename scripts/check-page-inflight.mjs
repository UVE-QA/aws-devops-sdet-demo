#!/usr/bin/env node
/**
 * THE GATE OVER WHAT THE PAGE SAYS WHILE A CYCLE IS RUNNING.
 *
 * Phase 20m watched a full cycle from one tab and found the page's account of it
 * wrong three ways, every one of them invisible at rest. Phase 22 fixed the
 * first. This gate is the instrument the other two never had, and the reason
 * they never had one is worth stating: every page gate here examines the page AT
 * REST, or lifts one pure function out of it and hands that function data.
 *
 *     check-page-tense.mjs   lifts nodeTense() and historyTally() and asks them
 *                            questions. Both were CORRECT while the page was
 *                            wrong: during a run the renderer never called one
 *                            of them.
 *     check-live-state.mjs   the run layer's own model, no page involved.
 *     check-page-freshness   an open tab against a fresh load - and both render
 *                            the same wrong caption, so they converge and it is
 *                            green.
 *     site-page-check        the built page against a fresh build.
 *
 * A function that answers correctly and is not called is exactly the shape of
 * defect this repository keeps finding, so the subject here is the RENDERED
 * PAGE, in the state a visitor is most likely to be looking at it: while
 * something is running.
 *
 * THE FIXTURE IS THE HARD HALF, AND IT DID NOT EXIST. 20m's own note said so.
 * tests/fixtures/page-inflight/ carries two things no page-measure set does:
 *
 *   an otherwise-green history   a red row gives the badge a bad verdict for a
 *                                reason that has nothing to do with the run in
 *                                flight, so the green-while-unknown shape - the
 *                                one the first finding was about - never appears
 *   the RUN LAYER               the ten documents readRunLayer() fetches. The
 *                                page-measure sets mock the three REMOTE sources
 *                                and let these ten 404 against the static
 *                                server, so every node on that page reads `not
 *                                run yet` and nothing prints a figure at all.
 *                                A finding about a figure needs a figure.
 *
 * TWO STATES OVER ONE LAYER, AND THE SECOND IS THE CONTROL. `in-flight` has
 * deploy-stage #64 running with its front on `Terraform apply`; `at-rest` is the
 * same fixture thirteen minutes later, #64 finished, nothing else changed. Every
 * claim below is made in both states. On 2026-08-05 this project built a control
 * that reproduced the defect it was controlling for, so the two renderings are
 * required to DIFFER before either verdict is believed.
 *
 * WHY IT REFUSES ON A 404 FROM ITS OWN SERVER, and measure-page.mjs does not.
 * That script guards the requests that LEAVE the origin and lets origin requests
 * through to a static directory that does not contain the run layer. Nothing is
 * wrong with the guard; the requests it cannot see are the ones that matter
 * here, and a page missing its whole run layer renders happily, shorter and
 * quieter, with no banner. The empty result that looks clean. So here every
 * origin 404 is a refusal.
 *
 *     node scripts/check-page-inflight.mjs
 *     node scripts/check-page-inflight.mjs --state in-flight
 *     node scripts/check-page-inflight.mjs --dump      # every node, as rendered
 *
 * CHROMIUM_PATH= on a machine whose chromium is not the pinned build, exactly as
 * for measure-page.mjs, check-contrast.mjs and check-page-freshness.mjs.
 *
 * Exit status: 0 when every claim held, 1 when one did not, 2 when it refused to
 * measure at all.
 */
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SITE = path.join(ROOT, "site");
const FIXTURE = path.join(ROOT, "tests/fixtures/page-inflight");
const LAYER = path.join(FIXTURE, "layer");
const PUBLISHED = path.join(FIXTURE, "layer-published");
const TOPOLOGY = path.join(SITE, "data/topology.json");
const VIEWPORT = { width: 1440, height: 900 };
const SETTLE_MS = 700;

/* THE SENTENCES THAT QUALIFY A FIGURE, listed rather than pattern-matched. Each
   one is written by a named branch of the page, and this gate reads the sentence
   a VISITOR reads rather than a data attribute, because the subject of the third
   finding is a sentence: `prod.rds` stood at full colour with the previous
   cycle's figures for twelve measured minutes and every one of those minutes was
   a person reading a number. Rewording one of these reddens the gate, and that
   is correct - the wording IS the claim. */
const QUALIFIERS = [
  "the cycle that ended",        // nodeTense(), the destroyed branch
  "the cycle before this one",   // nodeTense(), the under-way branch
  "from the previous run"        // suiteFigures(), n.result_previous
];

/* WHAT A NODE NOTHING CAN MEASURE IS NOT ALLOWED TO SAY. `figures publish when
   the cycle ends` is true of a phase whose numbers arrive at the end and false
   forever of the image push, the migrate/seed task and the human approval -
   Terraform reports resources and none of the three is one. */
const PROMISE = "figures publish when the cycle ends";
const NOT_MEASURED = ["not measured here", "its step is in Actions, not in a timeline"];

function refuse(message) {
  console.error(`page-inflight: ${message}`);
  process.exit(2);
}

function arg(flag, fallback = null) {
  const i = process.argv.indexOf(flag);
  return i === -1 ? fallback : process.argv[i + 1];
}

function readJSON(file, what) {
  if (!fs.existsSync(file)) refuse(`${path.relative(ROOT, file)} is missing (${what}).`);
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (e) {
    refuse(`${path.relative(ROOT, file)} is not valid JSON: ${e.message}`);
  }
}

// Same loader as measure-page.mjs and check-page-freshness.mjs: Playwright lives
// with the suites that use it, and guessing a location is not evidence.
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

/* EVERY NODE THE MAP CAN DRAW, indexed by the id it now writes into the DOM.
   Walked rather than reached into by path: the estate hangs its nodes off an
   environment group and the cycle hangs them off a phase, and a walk cannot go
   stale when schema 3 grows a third place to put one. */
function topologyIndex(topology) {
  const byId = {};
  (function walk(node) {
    if (Array.isArray(node)) return node.forEach(walk);
    if (!node || typeof node !== "object") return;
    if (typeof node.id === "string" && (node.observer || node.kind)) {
      byId[node.id] = { id: node.id, label: node.label, env: node.env || null,
                        kind: node.kind || null, observer: node.observer || null };
    }
    Object.values(node).forEach(walk);
  })(topology);
  return byId;
}

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon"
};

/* THE SITE, WITH THE RUN LAYER OVER THE TOP. The layer is what a cycle
   publishes into the bucket beside the page; site/ in the repository does not
   contain it and never will. Serving the fixture's copy at the same paths is
   what makes the map draw figures at all.

   THE OVERLAY IS WHY THIS TAKES A BOX RATHER THAN A CONSTANT. Phase 29's
   subject is a document arriving while the page is open, so the directory this
   serves from has to be changeable between two reads of the SAME page. `box`
   holds it, the lookup is overlay-then-layer-then-site, and nothing else about
   the server moves. */
function serve(notFound, box) {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://127.0.0.1");
    const rel = decodeURIComponent(url.pathname).replace(/^\/+/, "");
    let file = null;
    for (const dir of [box.overlay, LAYER].filter(Boolean)) {
      const candidate = path.join(dir, rel);
      if (candidate.startsWith(dir) && fs.existsSync(candidate) && !fs.statSync(candidate).isDirectory()) {
        file = candidate;
        break;
      }
    }
    if (!file) file = path.join(SITE, rel);
    if (rel === "" || rel.endsWith("/")) file = path.join(SITE, rel, "index.html");
    if (!file.startsWith(SITE) && !file.startsWith(LAYER) && !file.startsWith(PUBLISHED)) {
      notFound.push("/" + rel);
      res.writeHead(403, { "content-type": "text/plain" });
      res.end("refused");
      return;
    }
    if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      notFound.push("/" + rel);
      res.writeHead(404, { "content-type": "text/plain" });
      res.end("not found");
      return;
    }
    res.writeHead(200, { "content-type": MIME[path.extname(file)] || "application/octet-stream" });
    res.end(fs.readFileSync(file));
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => resolve({ server, port: server.address().port }));
  });
}

/* WHAT IS READ OFF THE RENDERED PAGE. Text and two data attributes, no pixels -
   a layout question is measure-page.mjs's. `data-id` is the binding this phase
   added to nodeEl(); without it the only handle on a box is the label it draws,
   and stage and prod draw the same labels. */
const OBSERVE = () => {
  const t = (el) => (el ? el.textContent.replace(/\s+/g, " ").trim() : null);
  return {
    history: t(document.querySelector("#history-summary")),
    verdict: t(document.querySelector("#history-summary .verdict")),
    mapSub: t(document.querySelector("#map-sub")),
    autorefresh: t(document.querySelector("#autorefresh")),
    banner: (() => {
      const b = document.querySelector(".banner.bad");
      return b ? t(b).slice(0, 200) : null;
    })(),
    rows: [...document.querySelectorAll("#history table tbody tr")].map((tr) =>
      [...tr.children].map((td) => t(td))),
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

function readState(state) {
  const dir = path.join(FIXTURE, state);
  if (!fs.existsSync(dir)) refuse(`no state called "${state}" in ${path.relative(ROOT, FIXTURE)}.`);
  const meta = readJSON(path.join(dir, "meta.json"), "the fixture's clock and its declared cycle");
  if (!meta.now) refuse(`${state}/meta.json declares no \`now\`; every age string would drift.`);
  if (!meta.cycle) refuse(`${state}/meta.json declares no \`cycle\`; this gate would have to re-derive which environments the run is about, which is the page's WRITERS table in a second place.`);
  return {
    meta,
    runs: readJSON(path.join(dir, "runs.json"), "the run history"),
    jobs: readJSON(path.join(dir, "jobs.json"), "the current run's steps"),
    status: {
      stage: readJSON(path.join(dir, "status-stage.json"), "what the bucket last observed of stage"),
      prod: readJSON(path.join(dir, "status-prod.json"), "what the bucket last observed of prod")
    }
  };
}

/* THE THREE REMOTE SOURCES, MOCKED FROM A BOX RATHER THAN FROM A CLOSURE. The
   sequence pass changes what the GitHub API answers while the page is open -
   that is ADR-0062 D2's whole subject - so the handler reads `src.current`
   every time rather than capturing one answer when it is installed. */
async function installRoutes(page, origin, src, unmocked) {
  src.githubReads = 0;
  await page.route("**/*", async (route) => {
    const url = route.request().url();
    const { runs, jobs, status, meta } = src.current;
    if (url.startsWith("https://api.github.com/")) src.githubReads += 1;
    if (url.startsWith(origin)) {
      if (/\/status\/(stage|prod)\.json/.test(url)) {
        const env = url.includes("stage") ? "stage" : "prod";
        return route.fulfill({ status: 200, contentType: "application/json",
                               body: JSON.stringify(status[env]) });
      }
      return route.continue();
    }
    if (url.startsWith("https://api.github.com/")) {
      const body = /\/jobs(\?|$)/.test(url) ? jobs : runs;
      return route.fulfill({
        status: 200, contentType: "application/json",
        headers: {
          "x-ratelimit-remaining": "57",
          "x-ratelimit-reset": String(Math.floor(Date.parse(meta.now) / 1000) + 1800),
          // THE MOCK HAD TO LEARN CORS BEFORE IT COULD MODEL GITHUB. These two
          // headers were here from the start and the page could not read either
          // of them: api.github.com is a different origin, and a cross-origin
          // response's non-simple headers are invisible to `r.headers.get()`
          // unless the response says otherwise. So readBudget() saw null twice,
          // `state.rateRemaining` stayed undefined, and every reading this gate
          // has ever taken was of the page's fallback branch rather than of the
          // budget arithmetic it actually runs in production. It did not matter
          // while the idle interval was a constant; ADR-0062 D2 makes it the
          // whole subject. GitHub sends this header, and the real page's
          // measured ~123 s live interval - which is neither of the fallback
          // constants - is the evidence that it does.
          "access-control-expose-headers": "x-ratelimit-remaining, x-ratelimit-reset"
        },
        body: JSON.stringify(body)
      });
    }
    unmocked.push(url);
    return route.abort();
  });
}

async function render(browser, origin, state, notFound) {
  const src = { current: readState(state) };
  const { meta, runs } = src.current;

  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();
  await page.clock.setFixedTime(new Date(meta.now));

  const unmocked = [];
  await installRoutes(page, origin, src, unmocked);

  await page.goto(origin + "/index.html", { waitUntil: "load" });
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(SETTLE_MS);
  const seen = await page.evaluate(OBSERVE);
  await context.close();

  if (unmocked.length) {
    refuse("the page asked for a source nobody mocked, so this reading would be of a page " +
      "missing part of itself:\n  " + [...new Set(unmocked)].join("\n  "));
  }
  if (notFound.length) {
    refuse("the page asked this gate's own server for documents it does not have, and a page " +
      "missing its run layer renders quietly and prints no figures at all - which is the " +
      "state every one of these claims would then be measured in:\n  " +
      [...new Set(notFound)].join("\n  "));
  }
  if (seen.banner) {
    refuse(`the page drew a source-failure banner - "${seen.banner}".`);
  }
  return { state, meta, runs, seen };
}

/* THE FIXTURE THAT PUBLISHES UNDERNEATH A RUNNING PAGE (Phase 29).
 *
 * Everything above holds one moment still and reads it. ADR-0062's two findings
 * cannot be seen that way, and this gate was green through the whole of Phase 28
 * while a live page was demonstrating one of them: both live in the layer or the
 * clock CHANGING while the tab stays open.
 *
 * WORSE THAN BLIND - CLAIM 3 ENCODES THE PREMISE THAT WAS FALSE. Its own comment
 * said `nothing publishes until a cycle ends, so every figure drawn during one
 * belongs to the cycle before it`, and required the disclaimer on every numeric
 * figure in an environment being touched. A job that publishes from a step
 * inside itself - promote-prod does, deploy-stage does - breaks that premise for
 * as long as it takes the rest of the job to finish, five measured minutes in
 * the real case.
 *
 * So the sequence is: load once, swap the layer underneath, let the page's own
 * 30-second tick pick it up, read again. No reload, no navigation, no Refresh -
 * asserted rather than assumed, by leaving a sentinel on `window` and requiring
 * it to survive. The clock is INSTALLED rather than fixed, because a tick that
 * has to happen in real time is a gate nobody will run.
 */
async function sequence(browser, origin, box, notFound) {
  const src = { current: readState("in-flight") };
  const { meta, runs } = src.current;

  const flying = (runs.workflow_runs || []).filter((r) => r.status !== "completed");
  if (flying.length !== 1) {
    refuse(`the sequence needs exactly one run in flight and the fixture has ${flying.length}.`);
  }
  const flight = flying[0];

  const doc = readJSON(path.join(PUBLISHED, "timeline/stage/nodes-apply.json"),
    "the document the run in flight publishes from inside its own job");
  const publishedBy = doc.cycle && doc.cycle.run && String(doc.cycle.run.id);
  if (publishedBy !== String(flight.id)) {
    refuse(`layer-published says it was written by run ${publishedBy} and the run in flight is ` +
      `${flight.id}. The whole point of this pass is a document belonging to the run being ` +
      `watched; with those two different it would test nothing.`);
  }
  const mine = Object.keys(doc.nodes || {});
  if (!mine.length) refuse("the published document carries no nodes at all.");

  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();
  await page.clock.install({ time: new Date(meta.now) });
  const unmocked = [];
  await installRoutes(page, origin, src, unmocked);

  box.overlay = null;
  await page.goto(origin + "/index.html", { waitUntil: "load" });
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(SETTLE_MS);
  const before = await page.evaluate(OBSERVE);
  await page.evaluate(() => { window.__phase29 = "the tab that was never reloaded"; });

  // THE PUBLISH. Nothing else changes: the run history still has #64 in flight,
  // the job still has steps to go, the bucket's status files are untouched.
  box.overlay = PUBLISHED;
  await page.clock.fastForward(35_000);
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(SETTLE_MS);
  const after = await page.evaluate(OBSERVE);
  const survived = await page.evaluate(() => window.__phase29 || null);
  await context.close();

  if (unmocked.length) {
    refuse("the page asked for a source nobody mocked during the sequence:\n  " +
      [...new Set(unmocked)].join("\n  "));
  }
  if (notFound.length) {
    refuse("the page asked this gate's own server for documents it does not have during the " +
      "sequence:\n  " + [...new Set(notFound)].join("\n  "));
  }
  if (survived !== "the tab that was never reloaded") {
    refuse("the sentinel left on `window` did not survive to the second reading, so the page " +
      "reloaded and this measured two page loads rather than one page learning something.");
  }
  return { flight, mine, before, after, publishedBy };
}

/* HOW LONG THE PAGE TAKES TO NOTICE A RUN THAT HAS STARTED (ADR-0062 D2).
 *
 * The other half of "the fixture changes underneath a running page": here it is
 * the API rather than the bucket. An at-rest page is opened, `new-run` starts
 * being answered twenty seconds later, and the clock is walked forward in steps
 * until the page says so out loud.
 *
 * THE ANSWER IS A WINDOW, NOT A POINT, and it is printed as one - the same
 * discipline scripts/watch-convergence.sh had to be corrected into (ADR-0062
 * D3): a poller can only ever say "not yet at T-step, and yes by T".
 *
 * WHY 120 SECONDS. It is twice the sustainable anonymous floor: 60 requests an
 * hour is one a minute, and an idle poll now costs one request rather than two.
 * So the bound holds even with half the budget gone, and it is a number chosen
 * for a page somebody is watching - which 300 s never was.
 */
const FIRST_NEWS_CEILING_MS = 120_000;
const FIRST_NEWS_STEP_MS = 15_000;
// THE WALK GOES PAST THE CEILING ON PURPOSE, far enough to catch the old
// five-minute clock. A walk that stops at the ceiling can only ever report `not
// within 120s`, which is the empty result that looks like a measurement; the
// break test asked for the number and got a silence, and the number is what
// says WHICH clock the page is on. Virtual time makes the extra steps free.
const FIRST_NEWS_WALK_MS = 330_000;

async function sequenceFirstNews(browser, origin, box, notFound) {
  const rest = readState("at-rest");
  const news = readState("new-run");
  const src = { current: rest };

  const flying = (news.runs.workflow_runs || []).filter((r) => r.status !== "completed");
  if (flying.length !== 1) {
    refuse(`new-run must hold exactly one unfinished run and it holds ${flying.length}.`);
  }
  if ((rest.runs.workflow_runs || []).some((r) => r.status !== "completed")) {
    refuse("at-rest holds an unfinished run, so the page would already have the news this " +
      "measures the arrival of.");
  }

  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();
  await page.clock.install({ time: new Date(rest.meta.now) });
  const unmocked = [];
  await installRoutes(page, origin, src, unmocked);
  box.overlay = null;

  await page.goto(origin + "/index.html", { waitUntil: "load" });
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(SETTLE_MS);
  const before = await page.evaluate(OBSERVE);

  // THE PAGE HAS TO BE IN THE BRANCH PRODUCTION IS IN. Both intervals are
  // derived from the rate budget and both have a constant fallback for when it
  // could not be read; measuring the fallback and calling it the interval is the
  // wrong-scope reading this repository keeps finding. It was the reading here
  // for one commit, silently, and only a probe of the page's own advertised
  // cadence - 120 s, which is a fallback constant and nothing else - said so.
  const budget = await page.evaluate(() =>
    (typeof state === "undefined" ? null : { rem: state.rateRemaining, reset: state.rateReset }));
  if (!budget || !budget.rem || !budget.reset) {
    refuse("the page could not read the rate budget out of the mocked GitHub response, so its " +
      "interval comes from a fallback constant and this would not be measuring the arithmetic " +
      "production runs. The mock must expose the two ratelimit headers across the origin, the " +
      `way api.github.com does. Read: ${JSON.stringify(budget)}`);
  }
  const advertised = (before.autorefresh || "").match(/GitHub every (\d+) s/);

  const knows = (seen) => /still going/.test(seen.verdict || "");
  if (knows(before)) {
    refuse("the page already says a run is going before one has started, so nothing below " +
      `would be measuring an arrival: "${before.verdict}"`);
  }

  // THE RUN STARTS. Only the API's answer changes; the page is not touched.
  const readsBefore = src.githubReads;
  src.current = news;
  const walked = [];
  let seenAt = null;
  let elapsed = 0;
  while (elapsed < FIRST_NEWS_WALK_MS) {
    await page.clock.fastForward(FIRST_NEWS_STEP_MS);
    elapsed += FIRST_NEWS_STEP_MS;
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(200);
    const seen = await page.evaluate(OBSERVE);
    walked.push({ at: elapsed, verdict: seen.verdict, reads: src.githubReads - readsBefore });
    if (knows(seen)) { seenAt = elapsed; break; }
  }
  const reads = src.githubReads - readsBefore;
  await context.close();

  if (unmocked.length) {
    refuse("the page asked for a source nobody mocked while the news was arriving:\n  " +
      [...new Set(unmocked)].join("\n  "));
  }
  return { before, walked, seenAt, reads, step: FIRST_NEWS_STEP_MS,
           advertised: advertised ? Number(advertised[1]) : null };
}

/* CLAIM 5 - THE PAGE'S FIRST WORD ABOUT A RUN DOES NOT ARRIVE ON ITS SLOWEST
   CLOCK. ADR-0062 D2, measured at 293 s against a 300 s ceiling on a real
   cycle. */
function claimFirstNews({ seenAt, walked, step }) {
  const out = [];
  if (seenAt === null) {
    const last = walked[walked.length - 1];
    out.push(`the page still says nothing about the run ${last.at / 1000}s after it started, ` +
      `which is past every interval it can return: "${last.verdict}"`);
    return out;
  }
  if (seenAt > FIRST_NEWS_CEILING_MS) {
    out.push(`the page's first word about the run arrives in (${(seenAt - step) / 1000}s, ` +
      `${seenAt / 1000}s], and the ceiling is ${FIRST_NEWS_CEILING_MS / 1000}s. The interval is ` +
      "derived from whether a run is ALREADY known to be live, which is the news it does not have");
  }
  return out;
}

/* CLAIM 4 - A FIGURE THE RUN IN FLIGHT PUBLISHED IS NOT CALLED THE PREVIOUS
   CYCLE'S. ADR-0062 D1. The right predicate is `does this record belong to the
   run in flight?`, and the record has answered it since ADR-0039 - the page has
   never asked. */
function claimPublishedFigureOwnsItself({ flight, mine, before, after }) {
  const out = [];
  const byId = (seen) => Object.fromEntries(seen.nodes.map((n) => [n.id, n.state || ""]));
  const was = byId(before);
  const now = byId(after);

  // THE PUBLISH HAS TO HAVE BEEN SEEN, or every sentence below is a sentence
  // about a page that learned nothing, and the claim passes for free. This is
  // the sequence's version of "a control that reproduces the defect is not a
  // control": here the risk is the opposite, a subject that never became one.
  const moved = mine.filter((id) => was[id] !== undefined && now[id] !== was[id]);
  if (!moved.length) {
    out.push("not one of the published nodes says anything different after the swap, so the " +
      "page never read the document and nothing below was measured:\n        " +
      mine.map((id) => `${id}: ${JSON.stringify(was[id])}`).join("\n        "));
    return out;
  }

  for (const id of mine) {
    const state = now[id];
    if (state === undefined) continue;
    const stale = QUALIFIERS.filter((q) => state.includes(q));
    if (stale.length) {
      out.push(`${id} was measured by ${flight.name} #${flight.run_number}, the run the page is ` +
        `watching, and the page calls it "${stale[0]}": "${state}"`);
    }
  }
  return out;
}

/* THE FIXTURE HAS TO BE THE THING IT CLAIMS TO BE, checked before any verdict is
   read off it. A fixture whose history carries a failure cannot show the shape
   the first finding was about; a fixture with nothing in flight cannot show the
   other two. Both are silent failures - the gate would simply pass. */
function auditFixture({ state, meta, runs }) {
  const WRITERS = {
    ".github/workflows/deploy-stage.yml": ["stage"],
    ".github/workflows/promote-prod.yml": ["prod"],
    ".github/workflows/self-service.yml": ["stage"],
    ".github/workflows/destroy.yml": null
  };
  const lifecycle = (runs.workflow_runs || []).filter((r) => r.path in WRITERS);
  if (!lifecycle.length) refuse(`${state}: the fixture's history contains no lifecycle run at all.`);
  const bad = lifecycle.filter((r) => r.status === "completed" && r.conclusion !== "success");
  if (bad.length) {
    refuse(`${state}: the fixture's history is not otherwise-green - ` +
      bad.map((r) => `${r.name} #${r.run_number} ${r.conclusion}`).join(", ") +
      ". A red row gives the badge a bad verdict for a reason that has nothing to do with " +
      "the run in flight, and the green-while-unknown shape never appears.");
  }
  const flying = lifecycle.filter((r) => r.status !== "completed");
  if (meta.cycle.in_flight && flying.length !== 1) {
    refuse(`${state}: declares a cycle in flight and its history holds ${flying.length} unfinished runs.`);
  }
  if (!meta.cycle.in_flight && flying.length !== 0) {
    refuse(`${state}: declares nothing in flight and its history holds ${flying.length} unfinished runs.`);
  }
  return { lifecycle, flying };
}

// ---- the claims -----------------------------------------------------------
// Each returns a list of findings. A claim with no findings held.

/* CLAIM 1 - THE VERDICT COUNTS ONLY THE RUNS THAT FINISHED. 20m read `all 12
   succeeded` five times with one of the twelve still going, and proved it by the
   pair either side of a completion: the row changed and the badge did not. */
function claimVerdict({ state, meta, seen }, { lifecycle, flying }) {
  const out = [];
  const drawn = seen.rows.length;
  const finished = drawn - flying.filter((r) => lifecycle.indexOf(r) < drawn).length;
  const verdict = seen.verdict || "";
  const m = /all (\d+) succeeded/.exec(verdict);
  if (meta.cycle.in_flight) {
    if (!/still going/.test(verdict)) {
      out.push(`the verdict does not name the run in flight: "${verdict}"`);
    }
    if (m && Number(m[1]) === drawn) {
      out.push(`the verdict counts every drawn run as succeeded (${m[1]} of ${drawn}) ` +
        `while one has not finished: "${verdict}"`);
    }
  } else {
    if (/still going/.test(verdict)) {
      out.push(`nothing is in flight and the verdict says otherwise: "${verdict}"`);
    }
    if (!m || Number(m[1]) !== drawn) {
      out.push(`every drawn run finished and succeeded, and the verdict does not say so: "${verdict}"`);
    }
  }
  void finished;
  return out;
}

/* CLAIM 2 - A NODE NOTHING CAN EVER MEASURE NEVER PROMISES FIGURES. The image
   push, the migrate/seed task and the human approval carry `observer: actions`
   in the topology, which is the field that says what could ever measure this.
   At rest all three say so. During a run the run layer speaks first and one of
   them promises numbers that will never arrive. */
function claimNeverMeasured({ seen }, index) {
  const out = [];
  for (const node of seen.nodes) {
    const known = index[node.id];
    if (!known || known.observer !== "actions") continue;
    const text = node.text || "";
    if (text.includes(PROMISE)) {
      out.push(`${node.id} (${known.label}) promises figures nothing will ever measure: "${node.state}"`);
    } else if (!NOT_MEASURED.some((p) => text.includes(p))) {
      out.push(`${node.id} (${known.label}) does not say that nothing measures it: "${node.state}"`);
    }
  }
  return out;
}

/* CLAIM 3 - A FIGURE PRINTED WHILE A CYCLE IS IN FLIGHT SAYS WHICH CYCLE IT IS
   FROM. 20m measured twelve minutes of prod.rds at full colour with the previous
   cycle's numbers while prod was being deleted.

   THIS COMMENT USED TO SAY `nothing publishes until a cycle ends, so every
   figure drawn during one belongs to the cycle before it`, and that premise was
   false - a job publishes from a step inside itself and then keeps running.
   Stating it here made the gate REQUIRE the disclaimer on figures the run in
   flight had just written, so it did not merely miss ADR-0062 D1, it asserted
   it. Both fixture states below hold records written by the run BEFORE the one
   in flight, which is the case this claim is about and is still worth checking;
   the other case cannot be held still at all, and is claim 4. */
function claimFiguresDated({ meta, seen }, index) {
  const out = [];
  const under = new Set(meta.cycle.in_flight ? meta.cycle.environments : []);
  for (const node of seen.nodes) {
    const known = index[node.id];
    if (!known || !known.env) continue;
    const state = node.state || "";
    if (!/\d/.test(state)) continue;                    // nothing numeric was printed
    const qualified = QUALIFIERS.some((q) => state.includes(q));
    if (under.has(known.env) && !qualified) {
      out.push(`${node.id} (${known.env}) prints a figure from the cycle before this one ` +
        `and does not say so: "${state}"`);
    }
    if (!under.has(known.env) && qualified) {
      out.push(`${node.id} (${known.env}) calls its figure earlier, and no run is touching ` +
        `${known.env}: "${state}"`);
    }
  }
  return out;
}

/* THE CONTROL THAT MUST DIFFER. Two renderings that agree would make every claim
   above true of a page that draws nothing at all. What must differ is named
   rather than hashed: the verdict, because one state has a run in flight, and at
   least one node's state line, because that is where the other two claims live.
   On 2026-08-05 a control inherited the defect it was controlling for; naming
   the difference first is the cheap version of not doing that again. */
function controlDiffers(a, b) {
  const out = [];
  if ((a.seen.verdict || "") === (b.seen.verdict || "")) {
    out.push(`both states print the same run-history verdict, "${a.seen.verdict}" - ` +
      `one of them is supposed to have a run in flight`);
  }
  const byId = Object.fromEntries(b.seen.nodes.map((n) => [n.id, n.state]));
  const moved = a.seen.nodes.filter((n) => byId[n.id] !== undefined && byId[n.id] !== n.state);
  if (!moved.length) {
    out.push("no node on the map says anything different between the two states, so the " +
      "in-flight fixture is not in flight as far as the page is concerned");
  }
  return out;
}

async function main() {
  if (!fs.existsSync(path.join(SITE, "index.html"))) {
    refuse("site/index.html does not exist. Run `make site-page` first.");
  }
  const index = topologyIndex(readJSON(TOPOLOGY, "the map's own data"));
  if (!Object.keys(index).length) refuse("site/data/topology.json indexed no nodes at all.");

  const wanted = arg("--state");
  const states = wanted ? [wanted] : ["in-flight", "at-rest"];
  const chromium = await loadChromium();
  const notFound = [];
  const box = { overlay: null };
  const { server, port } = await serve(notFound, box);
  const origin = `http://127.0.0.1:${port}`;
  const launch = { args: ["--no-sandbox"] };
  if (process.env.CHROMIUM_PATH) launch.executablePath = process.env.CHROMIUM_PATH;
  const browser = await chromium.launch(launch);

  const readings = [];
  let sequenced = null;
  let firstNews = null;
  try {
    for (const state of states) {
      notFound.length = 0;
      box.overlay = null;
      const reading = await render(browser, origin, state, notFound);
      reading.audit = auditFixture(reading);
      readings.push(reading);
    }
    if (!wanted) {
      notFound.length = 0;
      sequenced = await sequence(browser, origin, box, notFound);
      notFound.length = 0;
      firstNews = await sequenceFirstNews(browser, origin, box, notFound);
    }
  } finally {
    await browser.close();
    server.close();
  }

  if (arg("--dump", false) !== false || process.argv.includes("--dump")) {
    for (const r of readings) {
      console.log(`\n--- ${r.state} --- ${r.seen.history}`);
      for (const n of r.seen.nodes) console.log(`  ${n.id.padEnd(24)}${n.state || ""}`);
    }
    console.log("");
  }

  const CLAIMS = [
    ["the verdict counts only the runs that finished", claimVerdict],
    ["a node nothing can ever measure never promises figures", claimNeverMeasured],
    ["a figure printed while a cycle is in flight says which cycle it is from", claimFiguresDated]
  ];

  let failed = 0;
  for (const r of readings) {
    for (const [name, fn] of CLAIMS) {
      const findings = fn(r, fn === claimVerdict ? r.audit : index);
      if (findings.length) {
        failed += 1;
        console.log(`FAIL  ${r.state}: ${name}`);
        findings.forEach((f) => console.log(`        ${f}`));
      } else {
        console.log(`ok    ${r.state}: ${name}`);
      }
    }
  }

  if (sequenced) {
    if (process.argv.includes("--dump")) {
      console.log(`\n--- the publish underneath a running page: ${sequenced.mine.length} nodes ---`);
      const was = Object.fromEntries(sequenced.before.nodes.map((n) => [n.id, n.state]));
      for (const id of sequenced.mine) {
        const now = sequenced.after.nodes.find((n) => n.id === id);
        console.log(`  ${id.padEnd(20)}${was[id] || ""}\n  ${"".padEnd(20)}${now ? now.state : "(gone)"}`);
      }
      console.log("");
    }
    const name = "a figure the run in flight published is not called the previous cycle's";
    const findings = claimPublishedFigureOwnsItself(sequenced);
    if (findings.length) {
      failed += 1;
      console.log(`FAIL  sequence: ${name}`);
      findings.forEach((f) => console.log(`        ${f}`));
    } else {
      console.log(`ok    sequence: ${name}`);
    }
  }

  if (firstNews) {
    const window = firstNews.seenAt === null
      ? `never, inside ${firstNews.walked[firstNews.walked.length - 1].at / 1000}s`
      : `(${(firstNews.seenAt - firstNews.step) / 1000}s, ${firstNews.seenAt / 1000}s]`;
    const name = "the page's first word about a run does not arrive on its slowest clock";
    const findings = claimFirstNews(firstNews);
    if (findings.length) {
      failed += 1;
      console.log(`FAIL  sequence: ${name}`);
      findings.forEach((f) => console.log(`        ${f}`));
    } else {
      console.log(`ok    sequence: ${name}`);
    }
    console.log(`      first news in ${window}, ` +
      `${firstNews.reads} GitHub request${firstNews.reads === 1 ? "" : "s"} spent getting it`);
    if (process.argv.includes("--dump")) {
      firstNews.walked.forEach((w) =>
        console.log(`        +${String(w.at / 1000).padStart(3)}s  reads ${w.reads}  ${w.verdict}`));
    }
  }

  if (readings.length === 2) {
    const diff = controlDiffers(readings[0], readings[1]);
    if (diff.length) {
      console.error("\npage-inflight: the control does not differ from the subject.");
      diff.forEach((d) => console.error(`  ${d}`));
      process.exit(2);
    }
    console.log("ok    the two states differ, so the control is a control");
  } else {
    console.log(`note  only "${readings[0].state}" was read, so the control did not run`);
  }

  if (failed) {
    console.error(`\npage-inflight: ${failed} claim${failed === 1 ? "" : "s"} did not hold.`);
    process.exit(1);
  }
  console.log("\npage-inflight: every claim held, in both states.");
}

await main();
