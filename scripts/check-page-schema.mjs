#!/usr/bin/env node
/**
 * THE GATE UNDER ADR-0099: the estate's second layout is the same board.
 *
 * The rows are checked by check-page-inflight.mjs. This renders the BUILT page
 * over tests/fixtures/page-schema/ - both runtimes up, with a count in every
 * part class the page can draw - switches the board to its schema layout, and
 * holds it to six claims:
 *
 *   1. the picture is the board: every noun the rows draw is drawn once, by
 *      the same id, carrying the SAME state word it carried in the rows (D1 -
 *      the visitor switches layout, never truth)
 *   2. every part and every edge the generated schema names is on the page,
 *      once, and every edge's ends resolve to something drawn (D2, D3)
 *   3. a part's class and figure are what the fixture's own documents say -
 *      `0/1` is `short`, a dead letter is `alarm`, a Service is `declared`
 *   4. a destroyed environment's parts carry no counts
 *   5. a layer switched off hides its edges and dims its tiles, and nothing
 *      else moves; switched back on, everything returns (D4)
 *   6. back in the rows, the picture is gone and the tiles are not doubled
 *
 * and, over the `stale` state, a seventh: a count the panel would not draw as
 * current is grey in the picture too.
 *
 * Same Playwright and chromium as the other page gates, same CHROMIUM_PATH
 * escape hatch, same refusal on a source nobody mocked. It installs nothing.
 *
 *   node scripts/check-page-schema.mjs            # every state
 *   node scripts/check-page-schema.mjs --state up # one
 */
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SITE = path.join(ROOT, "site");
const FIXTURE = path.join(ROOT, "tests/fixtures/page-schema");
// The run layer the rows draw their figures from. Shared with the in-flight
// gate on purpose: a second copy of ten documents is a second fixture to age.
const LAYER = path.join(ROOT, "tests/fixtures/page-inflight/layer");
const SCHEMA = path.join(SITE, "data/schema.json");
const TOPOLOGY = path.join(SITE, "data/topology.json");
const VIEWPORT = { width: 1440, height: 900 };
const SETTLE_MS = 700;
const OPTIONAL_ABSENT = new Set([
  "/status/countdown.json", "/status/progress/stage.json", "/status/progress/prod.json", "/status/progress/lab.json"
]);

function refuse(message) {
  console.error("page-schema-check: REFUSED\n" + message);
  process.exit(2);
}
function arg(flag, fallback = null) {
  const i = process.argv.indexOf(flag);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}
function readJSON(file, what) {
  if (!fs.existsSync(file)) refuse(`${path.relative(ROOT, file)} is missing - ${what}.`);
  try { return JSON.parse(fs.readFileSync(file, "utf8")); }
  catch (e) { refuse(`${path.relative(ROOT, file)} is not JSON: ${e.message}`); }
}
async function loadChromium() {
  const candidates = [
    process.env.PLAYWRIGHT_MODULE,
    path.join(ROOT, "tests/playwright/node_modules/@playwright/test/index.js"),
    path.join(ROOT, "tests/playwright/node_modules/playwright/index.js")
  ].filter(Boolean);
  for (const c of candidates) {
    if (!fs.existsSync(c)) continue;
    const mod = await import(pathToFileURL(c).href);
    const chromium = mod.chromium || (mod.default && mod.default.chromium);
    if (chromium) return chromium;
  }
  refuse("Playwright is not installed where this expects it.\n  Looked in: " + candidates.join(", ") +
    "\n  Run `npm ci` in tests/playwright, or set PLAYWRIGHT_MODULE.");
}

const MIME = { ".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8",
               ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
               ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon" };

function serve(notFound) {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://127.0.0.1");
    const rel = decodeURIComponent(url.pathname).replace(/^\/+/, "");
    let file = path.join(LAYER, rel);
    if (!(file.startsWith(LAYER) && fs.existsSync(file) && !fs.statSync(file).isDirectory())) file = path.join(SITE, rel);
    if (rel === "" || rel.endsWith("/")) file = path.join(SITE, rel, "index.html");
    if (!file.startsWith(SITE) && !file.startsWith(LAYER)) {
      notFound.push("/" + rel); res.writeHead(403); res.end("refused"); return;
    }
    if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      if (!OPTIONAL_ABSENT.has("/" + rel)) notFound.push("/" + rel);
      res.writeHead(404, { "content-type": "text/plain" }); res.end("not found"); return;
    }
    res.writeHead(200, { "content-type": MIME[path.extname(file)] || "application/octet-stream" });
    res.end(fs.readFileSync(file));
  });
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve({ server, port: server.address().port })));
}

function readState(state) {
  const dir = path.join(FIXTURE, state);
  if (!fs.existsSync(dir)) refuse(`no state called "${state}" in ${path.relative(ROOT, FIXTURE)}.`);
  const meta = readJSON(path.join(dir, "meta.json"), "the fixture's clock and its expectations");
  if (!meta.now) refuse(`${state}/meta.json declares no \`now\`.`);
  if (!meta.expect || !meta.expect.parts) refuse(`${state}/meta.json declares no \`expect.parts\`; a gate with nothing declared beside the documents would be re-deriving the page's reading from them.`);
  return {
    meta,
    runs: readJSON(path.join(dir, "runs.json"), "the run history"),
    jobs: readJSON(path.join(dir, "jobs.json"), "the current run's steps"),
    quota: readJSON(path.join(dir, "quota.json"), "the endpoint's quota reply"),
    status: {
      stage: readJSON(path.join(dir, "status-stage.json"), "stage's observation"),
      prod: readJSON(path.join(dir, "status-prod.json"), "prod's observation"),
      lab: readJSON(path.join(dir, "status-lab.json"), "the lab's observation")
    }
  };
}

async function installRoutes(page, origin, src, unmocked) {
  await page.route("**/*", async (route) => {
    const url = route.request().url();
    if (url.startsWith(origin)) {
      const m = /\/status\/(stage|prod|lab)\.json/.exec(url);
      if (m) return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(src.status[m[1]]) });
      return route.continue();
    }
    if (/^https:\/\/[^/]+\.lambda-url\.[^/]+\.on\.aws\//.test(url) && route.request().method() === "GET" && /[?&]quota\b/.test(url)) {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(src.quota) });
    }
    if (url.startsWith("https://api.github.com/")) {
      const body = /\/jobs(\?|$)/.test(url) ? src.jobs : src.runs;
      return route.fulfill({
        status: 200, contentType: "application/json",
        headers: { "x-ratelimit-remaining": "57",
                   "x-ratelimit-reset": String(Math.floor(Date.parse(src.meta.now) / 1000) + 1800),
                   "access-control-expose-headers": "x-ratelimit-remaining, x-ratelimit-reset" },
        body: JSON.stringify(body)
      });
    }
    unmocked.push(url);
    return route.abort();
  });
}

/* What is read off the page, in the browser. Classes and data attributes,
   computed display for the edges - no pixels. */
const OBSERVE_TILES = () => [...document.querySelectorAll("#estate-envs .node[data-id]")]
  .map((n) => ({ id: n.dataset.id, word: n.dataset.word || "", env: (n.closest(".estate-env") || {}).querySelector
    ? ((n.closest(".estate-env").querySelector("header .envtag") || {}).textContent || "") : "" }));
const OBSERVE_PICTURE = () => {
  const host = document.querySelector("#estate-schema");
  const grids = [...host.querySelectorAll(".schema-grid")];
  return {
    rowsHidden: document.querySelector("#estate-envs").hidden,
    pictureHidden: host.hidden,
    toolsHidden: document.querySelector("#estate-tools").hidden,
    note: (document.querySelector("#schema-note") || {}).textContent || "",
    grids: grids.map((g) => ({
      boards: JSON.parse(g.dataset.edges || "[]"),
      off: g.dataset.off || "",
      tiles: [...g.querySelectorAll(".node[data-id]")].map((n) => ({
        id: n.dataset.id, word: n.dataset.word || "", layer: n.dataset.layer || "",
        opacity: Number(getComputedStyle(n).opacity), lane: (n.closest(".lane-cell") || {}).dataset ? n.closest(".lane-cell").dataset.lane : ""
      })),
      parts: [...g.querySelectorAll(".part[data-part]")].map((p) => ({
        id: p.dataset.part, classes: [...p.classList].filter((c) => c !== "part"), text: p.textContent,
        layer: p.dataset.layer || "", opacity: Number(getComputedStyle(p).opacity),
        dashed: getComputedStyle(p).borderTopStyle === "dashed"
      })),
      edges: [...g.querySelectorAll("path.edge")].map((e) => ({
        from: e.dataset.from, to: e.dataset.to, layer: [...e.classList].filter((c) => c !== "edge")[0] || "",
        shown: getComputedStyle(e).display !== "none", title: (e.querySelector("title") || {}).textContent || "",
        resolves: Boolean((g.querySelector(`[data-part="${e.dataset.from}"]`) || g.querySelector(`.node[data-id="${e.dataset.from}"]`)) &&
                          (g.querySelector(`[data-part="${e.dataset.to}"]`) || g.querySelector(`.node[data-id="${e.dataset.to}"]`)))
      }))
    })),
    allTiles: document.querySelectorAll(".node[data-id]").length
  };
};

async function render(browser, origin, state, notFound, schema) {
  const src = readState(state);
  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();
  await page.clock.setFixedTime(new Date(src.meta.now));
  const unmocked = [];
  await installRoutes(page, origin, src, unmocked);
  await page.goto(origin + "/index.html", { waitUntil: "load" });
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(SETTLE_MS);
  // The estate part, then the rows' reading, then the picture.
  await page.click('#parts button[data-show="estate"]');
  await page.waitForTimeout(200);
  const rows = await page.evaluate(OBSERVE_TILES);
  const rowsCount = await page.evaluate(() => document.querySelectorAll(".node[data-id]").length);
  await page.click('#estate-tools button[data-layout="schema"]');
  await page.waitForTimeout(SETTLE_MS);
  const picture = await page.evaluate(OBSERVE_PICTURE);
  await page.click('#estate-tools button[data-ecs="prod"]');
  await page.waitForTimeout(400);
  const prod = await page.evaluate(OBSERVE_PICTURE);
  await page.click('#estate-tools button[data-ecs="stage"]');
  await page.click('#estate-tools button[data-layer="network"]');
  await page.waitForTimeout(400);
  const networkOff = await page.evaluate(OBSERVE_PICTURE);
  await page.click('#estate-tools button[data-layer="network"]');
  await page.waitForTimeout(400);
  const networkBack = await page.evaluate(OBSERVE_PICTURE);
  await page.click('#estate-tools button[data-layout="rows"]');
  await page.waitForTimeout(400);
  const back = await page.evaluate(OBSERVE_PICTURE);
  await context.close();
  if (unmocked.length) refuse("the page asked for a source nobody mocked:\n  " + [...new Set(unmocked)].join("\n  "));
  if (notFound.length) refuse("the page asked this gate's own server for documents it does not have:\n  " + [...new Set(notFound)].join("\n  "));
  return { state, meta: src.meta, rows, rowsCount, picture, prod, networkOff, networkBack, back, schema };
}

// ------------------------------------------------------------------ claims
const one = (r) => r.picture.grids.length === 1 ? r.picture.grids[0] : null;

function claimPictureIsTheBoard(r) {
  const out = [];
  const g = one(r);
  if (!g) return [`expected one grid at ${VIEWPORT.width}px (both boards side by side); found ${r.picture.grids.length}`];
  if (!r.picture.rowsHidden || r.picture.pictureHidden || r.picture.toolsHidden) out.push("the schema layout did not take the board over: rows shown, picture hidden, or the tools hidden");
  const boards = g.boards;
  if (boards.join(",") !== "stage,lab") out.push(`the picture draws ${boards.join(",")}, not stage beside the lab`);
  const nouns = boards.reduce((a, e) => a.concat(r.schema.environments[e].nouns.map((n) => n.id)), []);
  const drawn = g.tiles.map((t) => t.id);
  for (const id of nouns) {
    const k = drawn.filter((d) => d === id).length;
    if (k !== 1) out.push(`${id} is drawn ${k} times in the picture; once is the board`);
  }
  for (const t of g.tiles) if (!nouns.includes(t.id)) out.push(`${t.id} is in the picture and not in the schema`);
  const rowWord = {};
  r.rows.forEach((t) => { rowWord[t.id] = t.word; });
  for (const t of g.tiles) {
    if (rowWord[t.id] !== undefined && rowWord[t.id] !== t.word) out.push(`${t.id} says "${t.word}" in the picture and "${rowWord[t.id]}" in the rows - a layout that changes the word is a second opinion`);
  }
  for (const t of g.tiles) {
    const lane = r.schema.environments[t.id.split(".")[0]].nouns.find((n) => n.id === t.id).lane;
    if (t.lane !== lane) out.push(`${t.id} sits in lane ${t.lane}; the schema puts it in ${lane}`);
  }
  return out;
}

function claimEveryPartAndEdge(r) {
  const out = [];
  const g = one(r); if (!g) return out;
  const parts = g.boards.reduce((a, e) => a.concat(r.schema.environments[e].parts.map((p) => p.id)), []);
  const drawn = g.parts.map((p) => p.id);
  for (const id of parts) {
    const k = drawn.filter((d) => d === id).length;
    if (k !== 1) out.push(`part ${id} is drawn ${k} times`);
  }
  const edges = g.boards.reduce((a, e) => a + r.schema.environments[e].edges.length, 0);
  if (g.edges.length !== edges) out.push(`${g.edges.length} edges drawn, the schema names ${edges}`);
  for (const e of g.edges) {
    if (!e.resolves) out.push(`edge ${e.from} -> ${e.to} points at something the picture does not draw`);
    if (!/(infra|charts)\//.test(e.title)) out.push(`edge ${e.from} -> ${e.to} carries no source in its title: "${e.title}"`);
    if (!["network", "runtime", "data", "identity"].includes(e.layer)) out.push(`edge ${e.from} -> ${e.to} is on no layer (${e.layer || "none"})`);
  }
  if (!new RegExp(`^${edges} edges`).test(r.picture.note)) out.push(`the note says "${r.picture.note.slice(0, 40)}…", not ${edges} edges`);
  return out;
}

function claimPartsReadTheCounts(r) {
  const out = [];
  const g = one(r); if (!g) return out;
  const by = {}; g.parts.forEach((p) => { by[p.id] = p; });
  for (const [id, want] of Object.entries(r.meta.expect.parts)) {
    const p = by[id];
    if (!p) { out.push(`expected part ${id} is not drawn`); continue; }
    if (!p.classes.includes(want.class)) out.push(`${id} is [${p.classes.join(" ")}], the documents say ${want.class}`);
    if (!p.text.includes(want.figure)) out.push(`${id} prints "${p.text}", which does not carry "${want.figure}"`);
    const dashedWanted = want.class === "declared" || want.class === "absent";
    if (p.dashed !== dashedWanted) out.push(`${id} is ${p.dashed ? "dashed" : "solid"}; ${want.class} is drawn ${dashedWanted ? "dashed" : "solid"}`);
  }
  // Every declared part says so, and none is coloured.
  for (const p of g.parts) {
    const spec = r.schema.environments[p.id.split(".")[0]].parts.find((x) => x.id === p.id);
    if (spec && !spec.observe && !(p.classes.includes("declared") && p.text.includes("declared"))) {
      out.push(`${p.id} has no observation and is drawn [${p.classes.join(" ")}] "${p.text}" rather than declared`);
    }
  }
  return out;
}

function claimDestroyedHasNoCounts(r) {
  const out = [];
  const g = r.prod.grids[0];
  if (!g || g.boards[0] !== "prod") return [`switching the ECS side to prod drew ${g ? g.boards.join(",") : "nothing"}`];
  for (const p of g.parts.filter((x) => x.id.startsWith("prod."))) {
    const spec = r.schema.environments.prod.parts.find((x) => x.id === p.id);
    if (spec.observe && !p.classes.includes("absent")) out.push(`prod is destroyed and ${p.id} is [${p.classes.join(" ")}] "${p.text}"`);
    if (spec.observe && /\d\/\d/.test(p.text)) out.push(`prod is destroyed and ${p.id} prints a count: "${p.text}"`);
  }
  return out;
}

function claimLayerOff(r) {
  const out = [];
  const on = one(r), off = r.networkOff.grids[0], back = r.networkBack.grids[0];
  if (!on || !off || !back) return out;
  if (!/\bnetwork\b/.test(off.off)) out.push(`the grid does not say network is off (data-off="${off.off}")`);
  const hidden = off.edges.filter((e) => !e.shown);
  if (hidden.length !== off.edges.filter((e) => e.layer === "network").length || hidden.some((e) => e.layer !== "network")) {
    out.push(`with network off, ${hidden.length} edges are hidden and ${hidden.filter((e) => e.layer !== "network").length} of them are not network's`);
  }
  if (off.edges.filter((e) => e.shown && e.layer === "network").length) out.push("a network edge is still shown with the layer off");
  if (on.edges.some((e) => !e.shown)) out.push("an edge is hidden with every layer on");
  // Dimmed RELATIVE to the same tile with every layer on: an absent noun is
  // already faint, and that is its own statement, not the switch's.
  const before = {}; on.tiles.forEach((t) => { before[t.id] = t.opacity; });
  const dimmed = off.tiles.filter((t) => t.opacity < before[t.id] - 0.01);
  if (!dimmed.length || dimmed.some((t) => t.layer !== "network")) out.push(`with network off, the dimmed tiles are ${dimmed.map((t) => t.id).join(", ") || "none"}`);
  if (off.tiles.filter((t) => t.layer === "network").some((t) => t.opacity >= before[t.id] - 0.01)) out.push("a network tile is not dimmed with the layer off");
  if (back.edges.some((e) => !e.shown) || back.off) out.push("switching network back on did not bring its edges back");
  if (off.tiles.length !== on.tiles.length || off.parts.length !== on.parts.length) out.push("a layer switch removed something; it may only dim");
  return out;
}

function claimRowsComeBackAlone(r) {
  const out = [];
  if (!r.back.pictureHidden || r.back.rowsHidden) out.push("back in the rows, the picture is still shown or the rows still hidden");
  if (r.back.grids.length) out.push(`back in the rows, ${r.back.grids.length} grid(s) are still in the document - a hidden second copy of the estate`);
  if (r.back.allTiles !== r.rowsCount) out.push(`${r.back.allTiles} tiles after the round trip, ${r.rowsCount} before it`);
  return out;
}

function claimStaleIsGrey(r) {
  const out = [];
  const g = one(r); if (!g) return out;
  for (const [env, stale] of Object.entries(r.meta.expect.stale || {})) {
    if (!stale) continue;
    for (const p of g.parts.filter((x) => x.id.startsWith(env + "."))) {
      const spec = r.schema.environments[env].parts.find((x) => x.id === p.id);
      if (spec.observe && !p.classes.includes("unobserved")) out.push(`${env}'s reading is stale and ${p.id} is drawn as current: [${p.classes.join(" ")}]`);
    }
  }
  return out;
}

async function main() {
  if (!fs.existsSync(path.join(SITE, "index.html"))) refuse("site/index.html does not exist. Run `make site-page` first.");
  const schema = readJSON(SCHEMA, "the generated schema");
  readJSON(TOPOLOGY, "the map's own data");
  const wanted = arg("--state");
  const states = wanted ? [wanted] : ["up", "stale"];
  const chromium = await loadChromium();
  const notFound = [];
  const { server, port } = await serve(notFound);
  const origin = `http://127.0.0.1:${port}`;
  const launch = { args: ["--no-sandbox"] };
  if (process.env.CHROMIUM_PATH) launch.executablePath = process.env.CHROMIUM_PATH;
  const browser = await chromium.launch(launch);
  const readings = [];
  try {
    for (const state of states) {
      notFound.length = 0;
      readings.push(await render(browser, origin, state, notFound, schema));
    }
  } finally {
    await browser.close();
    server.close();
  }
  const findings = [];
  const say = (state, name, out) => {
    console.log(`  ${out.length ? "FAIL" : "ok  "}  ${state.padEnd(6)} ${name}`);
    out.forEach((f) => { findings.push(`${state}: ${name}: ${f}`); });
  };
  console.log("page-schema-check:");
  for (const r of readings) {
    say(r.state, "the picture is the board, same ids, same words, in the schema's lanes", claimPictureIsTheBoard(r));
    say(r.state, "every part and every edge the schema names, once, with a source", claimEveryPartAndEdge(r));
    say(r.state, "a part's class and figure are what the documents say", claimPartsReadTheCounts(r));
    say(r.state, "a destroyed environment's parts carry no counts", claimDestroyedHasNoCounts(r));
    say(r.state, "a layer off hides its edges and dims its tiles, and nothing else moves", claimLayerOff(r));
    say(r.state, "back in the rows, the picture is gone and the tiles are not doubled", claimRowsComeBackAlone(r));
    if (r.meta.expect.stale && Object.keys(r.meta.expect.stale).length) {
      say(r.state, "a stale reading is grey in the picture too", claimStaleIsGrey(r));
    }
  }
  if (findings.length) {
    console.error("\npage-schema-check: FAILED\n  " + findings.join("\n  "));
    process.exit(1);
  }
  const g = readings[0].picture.grids[0];
  console.log(`page-schema-check: ${readings.length} states, ${g.tiles.length} tiles, ${g.parts.length} parts, ${g.edges.length} edges; every claim holds`);
}

main().catch((e) => refuse(e.stack || String(e)));
