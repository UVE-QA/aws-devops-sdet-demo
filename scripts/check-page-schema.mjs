#!/usr/bin/env node
/**
 * THE GATE UNDER ADR-0099: the estate's second layout is the same board.
 *
 * The rows are checked by check-page-inflight.mjs. This renders the BUILT page
 * over tests/fixtures/page-schema/ - both runtimes up, with a count in every
 * part class the page can draw - switches the board to its schema layout, and
 * holds it to six claims, for stage (ECS) and for the lab (EKS):
 *
 *   1. the picture is the board: every noun the rows draw is drawn once, by
 *      the same id, carrying the SAME state word it carried in the rows, in
 *      the place its lane puts it (D1 - the visitor switches layout, never
 *      truth); a noun on a layer that is off is hidden, not missing
 *   2. every part the generated schema names is on the page once; every edge
 *      on a layer that is on is drawn, none on a layer that is off, and every
 *      drawn edge's ends resolve to something drawn (D2, D3)
 *   3. a part's class and figure are what the fixture's own documents say -
 *      `0/1` is `short`, a dead letter is `alarm`, a Service is `declared`
 *   4. a destroyed environment's parts carry no counts
 *   5. a layer switched on adds its edges and its nouns, and nothing else
 *      moves; switched off again, they go (D4)
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
  "/status/countdown.json",
  // ADR-0100: the run history the cycle writes; absent means the page asks
  // GitHub, which is the path every older claim was written against.
  "/status/runs.json", "/status/progress/stage.json", "/status/progress/prod.json", "/status/progress/lab.json"
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
  const boards = [...host.querySelectorAll(".schema-board")];
  const shown = (el) => Boolean(el) && !el.hidden && !el.closest("[hidden]") && getComputedStyle(el).display !== "none";
  return {
    rowsHidden: document.querySelector("#estate-envs").hidden,
    pictureHidden: host.hidden,
    toolsHidden: document.querySelector("#estate-tools").hidden,
    note: (document.querySelector("#schema-note") || {}).textContent || "",
    layersOn: [...document.querySelectorAll("#estate-tools [data-layer]")].filter((b) => b.getAttribute("aria-pressed") === "true").map((b) => b.dataset.layer),
    boards: boards.map((g) => ({
      env: g.dataset.env,
      tiles: [...g.querySelectorAll(".node[data-id]")].map((n) => ({
        id: n.dataset.id, word: n.dataset.word || "", layer: n.dataset.layer || "", shown: shown(n),
        lane: (n.closest("[data-lane]") || { dataset: {} }).dataset.lane || ""
      })),
      // A part is a chip, or the state line of a part drawn as a tile.
      parts: [...g.querySelectorAll("[data-part]")].map((p) => ({
        id: p.dataset.part, classes: [...p.classList].filter((c) => !["part", "nstate", "part-state"].includes(c)), text: p.textContent,
        dashed: getComputedStyle(p).borderTopStyle === "dashed" || Boolean(p.closest(".node.pseudo") && p.classList.contains("declared")),
        tile: Boolean(p.closest(".node.pseudo") && p.classList.contains("nstate"))
      })),
      edges: [...g.querySelectorAll("path.edge")].map((e) => ({
        from: e.dataset.from, to: e.dataset.to, layer: [...e.classList].filter((c) => c !== "edge")[0] || "",
        title: (e.querySelector("title") || {}).textContent || "",
        resolves: ["from", "to"].every((k) => shown(g.querySelector(`[data-node="${e.dataset[k]}"]`) ||
          g.querySelector(`.node[data-id="${e.dataset[k]}"]`) || g.querySelector(`[data-part="${e.dataset[k]}"]`)))
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
  const pictures = {};
  for (const env of ["stage", "lab", "prod"]) {
    await page.click(`#estate-tools button[data-env="${env}"]`);
    await page.waitForTimeout(400);
    pictures[env] = await page.evaluate(OBSERVE_PICTURE);
  }
  await page.click('#estate-tools button[data-env="lab"]');
  await page.click('#estate-tools button[data-layer="identity"]');
  await page.waitForTimeout(400);
  const identityOn = await page.evaluate(OBSERVE_PICTURE);
  await page.click('#estate-tools button[data-layer="identity"]');
  await page.waitForTimeout(400);
  const identityBack = await page.evaluate(OBSERVE_PICTURE);
  await page.click('#estate-tools button[data-layout="rows"]');
  await page.waitForTimeout(400);
  const back = await page.evaluate(OBSERVE_PICTURE);
  await context.close();
  if (unmocked.length) refuse("the page asked for a source nobody mocked:\n  " + [...new Set(unmocked)].join("\n  "));
  if (notFound.length) refuse("the page asked this gate's own server for documents it does not have:\n  " + [...new Set(notFound)].join("\n  "));
  return { state, meta: src.meta, rows, rowsCount, pictures, identityOn, identityBack, back, schema };
}

// ------------------------------------------------------------------ claims
const boardOf = (pic) => pic.boards.length === 1 ? pic.boards[0] : null;
const offLayers = (r, pic) => (r.schema.layers || []).map((l) => l.id).filter((id) => !pic.layersOn.includes(id));

function claimPictureIsTheBoard(r, env) {
  const out = [];
  const pic = r.pictures[env];
  const g = boardOf(pic);
  if (!g) return [`expected one board for ${env}; found ${pic.boards.length}`];
  if (!pic.rowsHidden || pic.pictureHidden || pic.toolsHidden) out.push("the schema layout did not take the board over: rows shown, picture hidden, or the tools hidden");
  if (g.env !== env) out.push(`the picture draws ${g.env}, not ${env}`);
  const nouns = r.schema.environments[env].nouns;
  const drawn = g.tiles.map((t) => t.id);
  const off = offLayers(r, pic);
  for (const n of nouns) {
    const k = drawn.filter((d) => d === n.id).length;
    if (k !== 1) out.push(`${n.id} is drawn ${k} times in the picture; once is the board`);
    const t = g.tiles.find((x) => x.id === n.id);
    if (t && n.layer && off.includes(n.layer) && t.shown) out.push(`${n.id} is on the ${n.layer} layer, which is off, and is shown`);
    if (t && !(n.layer && off.includes(n.layer)) && !t.shown) out.push(`${n.id} is hidden and its layer is not off`);
    if (t && t.lane !== n.lane) out.push(`${n.id} sits in ${t.lane || "no lane"}; the schema puts it in ${n.lane}`);
  }
  for (const t of g.tiles) if (!nouns.some((n) => n.id === t.id)) out.push(`${t.id} is in the picture and not in the schema`);
  const rowWord = {};
  r.rows.forEach((t) => { rowWord[t.id] = t.word; });
  for (const t of g.tiles) {
    if (rowWord[t.id] !== undefined && rowWord[t.id] !== t.word) out.push(`${t.id} says "${t.word}" in the picture and "${rowWord[t.id]}" in the rows - a layout that changes the word is a second opinion`);
  }
  return out;
}

function claimEveryPartAndEdge(r, env) {
  const out = [];
  const pic = r.pictures[env];
  const g = boardOf(pic); if (!g) return out;
  const sch = r.schema.environments[env];
  const drawn = g.parts.map((p) => p.id);
  for (const p of sch.parts) {
    const k = drawn.filter((d) => d === p.id).length;
    if (k !== 1) out.push(`part ${p.id} is drawn ${k} times`);
  }
  const off = offLayers(r, pic);
  // An edge from the Ingress to a Service drawn inside its tile is the
  // containment already drawn: the page draws no line from a box into
  // itself, and this claim does not ask for one.
  const placed = {}; sch.parts.forEach((p) => { placed[p.id] = p; });
  const nested = (e) => placed[e.from] && placed[e.to] && placed[e.from].kind === "ingress" && placed[e.to].kind === "service";
  const wanted = sch.edges.filter((e) => !off.includes(e.layer) && !nested(e));
  if (g.edges.length !== wanted.length) out.push(`${g.edges.length} edges drawn; ${wanted.length} are on a layer that is on (${pic.layersOn.join(", ")})`);
  for (const e of g.edges) {
    if (off.includes(e.layer)) out.push(`edge ${e.from} -> ${e.to} is drawn and its layer ${e.layer} is off`);
    if (!e.resolves) out.push(`edge ${e.from} -> ${e.to} points at something the picture does not draw`);
    if (!/(infra|charts)\//.test(e.title)) out.push(`edge ${e.from} -> ${e.to} carries no source in its title: "${e.title}"`);
    if (!(r.schema.layers || []).some((l) => l.id === e.layer)) out.push(`edge ${e.from} -> ${e.to} is on no layer (${e.layer || "none"})`);
  }
  // The note counts the edges on the layers that are on - the nested ones
  // among them, shown as containment rather than as lines.
  const onLayer = sch.edges.filter((e) => !off.includes(e.layer)).length;
  if (!new RegExp(`^${onLayer} of ${sch.edges.length} edges`).test(pic.note)) out.push(`the note says "${pic.note.slice(0, 40)}…", not ${onLayer} of ${sch.edges.length}`);
  return out;
}

function claimPartsReadTheCounts(r, env) {
  const out = [];
  const g = boardOf(r.pictures[env]); if (!g) return out;
  const by = {}; g.parts.forEach((p) => { by[p.id] = p; });
  for (const [id, want] of Object.entries(r.meta.expect.parts)) {
    if (!id.startsWith(env + ".")) continue;
    const p = by[id];
    if (!p) { out.push(`expected part ${id} is not drawn`); continue; }
    if (!p.classes.includes(want.class)) out.push(`${id} is [${p.classes.join(" ")}], the documents say ${want.class}`);
    if (!p.text.includes(want.figure)) out.push(`${id} prints "${p.text}", which does not carry "${want.figure}"`);
    const dashedWanted = want.class === "declared" || want.class === "absent";
    if (!p.tile && p.dashed !== dashedWanted) out.push(`${id} is ${p.dashed ? "dashed" : "solid"}; ${want.class} is drawn ${dashedWanted ? "dashed" : "solid"}`);
  }
  for (const p of g.parts) {
    const spec = r.schema.environments[env].parts.find((x) => x.id === p.id);
    if (spec && !spec.observe && !(p.classes.includes("declared") && p.text.includes("declared"))) {
      out.push(`${p.id} has no observation and is drawn [${p.classes.join(" ")}] "${p.text}" rather than declared`);
    }
  }
  return out;
}

function claimDestroyedHasNoCounts(r) {
  const out = [];
  const g = boardOf(r.pictures.prod);
  if (!g || g.env !== "prod") return [`switching to prod drew ${g ? g.env : "nothing"}`];
  for (const p of g.parts) {
    const spec = r.schema.environments.prod.parts.find((x) => x.id === p.id);
    if (spec.observe && !p.classes.includes("absent")) out.push(`prod is destroyed and ${p.id} is [${p.classes.join(" ")}] "${p.text}"`);
    if (spec.observe && /\d\/\d/.test(p.text)) out.push(`prod is destroyed and ${p.id} prints a count: "${p.text}"`);
  }
  return out;
}

function claimLayerSwitch(r) {
  const out = [];
  const before = boardOf(r.pictures.lab), on = boardOf(r.identityOn), back = boardOf(r.identityBack);
  if (!before || !on || !back) return ["the lab's picture was not drawn through the identity switch"];
  if (!r.identityOn.layersOn.includes("identity")) out.push("the identity button did not switch the layer on");
  const sch = r.schema.environments.lab;
  const identityEdges = sch.edges.filter((e) => e.layer === "identity").length;
  if (on.edges.filter((e) => e.layer === "identity").length !== identityEdges) out.push(`with identity on, ${on.edges.filter((e) => e.layer === "identity").length} identity edges are drawn; the schema has ${identityEdges}`);
  if (before.edges.some((e) => e.layer === "identity")) out.push("an identity edge is drawn with the layer off");
  if (on.edges.length - before.edges.length !== identityEdges) out.push("switching identity on changed edges of another layer");
  const identityNouns = sch.nouns.filter((n) => n.layer === "identity").map((n) => n.id);
  for (const id of identityNouns) {
    const b = before.tiles.find((t) => t.id === id), a = on.tiles.find((t) => t.id === id);
    if (!b || b.shown) out.push(`${id} is on the identity layer and shown with it off`);
    if (!a || !a.shown) out.push(`${id} is on the identity layer and hidden with it on`);
  }
  const others = before.tiles.filter((t) => !identityNouns.includes(t.id));
  for (const t of others) {
    const a = on.tiles.find((x) => x.id === t.id);
    if (!a || a.shown !== t.shown || a.word !== t.word) out.push(`${t.id} moved when identity was switched on`);
  }
  if (on.parts.length !== before.parts.length) out.push("a layer switch changed the parts; it may only add its own nouns and edges");
  if (back.edges.length !== before.edges.length || back.tiles.filter((t) => t.shown).length !== before.tiles.filter((t) => t.shown).length) out.push("switching identity off again did not restore the picture");
  return out;
}

function claimRowsComeBackAlone(r) {
  const out = [];
  if (!r.back.pictureHidden || r.back.rowsHidden) out.push("back in the rows, the picture is still shown or the rows still hidden");
  if (r.back.boards.length) out.push(`back in the rows, ${r.back.boards.length} board(s) are still in the document - a hidden second copy of the estate`);
  if (r.back.allTiles !== r.rowsCount) out.push(`${r.back.allTiles} tiles after the round trip, ${r.rowsCount} before it`);
  return out;
}

function claimStaleIsGrey(r) {
  const out = [];
  for (const [env, stale] of Object.entries(r.meta.expect.stale || {})) {
    if (!stale) continue;
    const g = boardOf(r.pictures[env]); if (!g) continue;
    for (const p of g.parts) {
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
    for (const env of ["stage", "lab"]) {
      say(r.state, `${env}: the picture is the board, same ids, same words, each in its lane`, claimPictureIsTheBoard(r, env));
      say(r.state, `${env}: every part once; every edge on a layer that is on, with a source`, claimEveryPartAndEdge(r, env));
      say(r.state, `${env}: a part's class and figure are what the documents say`, claimPartsReadTheCounts(r, env));
    }
    say(r.state, "a destroyed environment's parts carry no counts", claimDestroyedHasNoCounts(r));
    say(r.state, "a layer switched on adds its edges and its nouns, and nothing else moves", claimLayerSwitch(r));
    say(r.state, "back in the rows, the picture is gone and the tiles are not doubled", claimRowsComeBackAlone(r));
    if (r.meta.expect.stale && Object.keys(r.meta.expect.stale).length) {
      say(r.state, "a stale reading is grey in the picture too", claimStaleIsGrey(r));
    }
  }
  if (findings.length) {
    console.error("\npage-schema-check: FAILED\n  " + findings.join("\n  "));
    process.exit(1);
  }
  const g = readings[0].pictures.stage.boards[0], l = readings[0].pictures.lab.boards[0];
  console.log(`page-schema-check: ${readings.length} states; stage ${g.tiles.length} tiles, ${g.parts.length} parts, ${g.edges.length} edges; ` +
    `lab ${l.tiles.length} tiles, ${l.parts.length} parts, ${l.edges.length} edges; every claim holds`);
}

main().catch((e) => refuse(e.stack || String(e)));
