#!/usr/bin/env node
/**
 * THE INSTRUMENT UNDER PHASE 20e — how tall the dashboard is, and what sticks
 * out of the box it was put in.
 *
 * This is a MEASUREMENT, not a gate. It has no verdict and nothing in CI
 * depends on it. It exists because every figure this phase has argued from -
 * 10.5 screens, 4.2, 5.8, "52px wider than a 390px viewport" - was produced by
 * a harness that was written in a session and thrown away with it. The numbers
 * outlived the thing that made them, which is how a figure becomes folklore:
 * quoted, un-reproducible, and eventually wrong without anybody editing it.
 *
 * WHY IT MOCKS THE SOURCES. The page reads three things this sandbox cannot
 * reach - the GitHub Actions API, `status/*.json` in the public bucket, and the
 * self-service endpoint. Measured with them unreachable the page renders its
 * banners and its "no observation" panels, and is SHORTER than the page a
 * visitor gets. ADR-0047's own discovery said so in the same breath as its
 * figures. So the sources come from tests/fixtures/page-measure/, frozen, with
 * `meta.now` pinning the clock: `12 min ago` stays `12 min ago` forever, and
 * two measurements six months apart are comparable.
 *
 *     at-rest     nothing running, both environments destroyed - the page most
 *                 of the time, and both status files are REAL captures
 *     in-flight   a deploy running, stage stale against it, prod up with every
 *                 optional field present - the tallest honest shape
 *
 * A layout decided on `at-rest` alone would be decided on the page's short day.
 *
 * WHAT IT REFUSES TO MEASURE. A page that failed to read a source renders a
 * banner and carries on, so a broken mock looks like a short page rather than
 * like an error - the empty result that looks clean, which this project has
 * been bitten by twice. So: every request that leaves the origin and is not
 * mocked is recorded and refuses the run, and the page is asked afterwards
 * whether it drew a source-failure banner. Either one aborts without printing
 * a figure.
 *
 * WHAT IT MEASURES, and why the second one is the point:
 *
 *   height        document.documentElement.scrollHeight, and that over the
 *                 viewport height - "screens", the unit this phase argues in
 *   beyond-parent every box whose border edge sticks out of its PARENT'S
 *                 padding edge, by more than 1px
 *   content-wide  every box whose own content is wider than its own box
 *   packing       every phase's height against the height of the ROW it is in,
 *                 and the air that difference adds up to - the comb, as a
 *                 number. Same question of the three panels above the map.
 *   broken words  a word the line box SPLIT. A Range over one word reports one
 *                 client rect when it sits on one line and two when it does
 *                 not, so `environme|nt` is a measurement rather than a thing
 *                 somebody happened to notice. Places that break long
 *                 identifiers on purpose say so in CSS (`overflow-wrap:
 *                 anywhere`) and are not asked.
 *   the floor     what the narrowest node would have to be: the widest single
 *                 word any node draws, and the whole name on one line, each
 *                 plus the chrome around it. --node-min is a claim about this
 *                 number, and until 20j nothing had measured it.
 *
 * PACKING IS MEASURED WITH THE CUTS CLOSED ONLY. Opening every <details> changes
 * the page below the map and nothing inside it, so the second reading would be
 * the same numbers twice.
 *
 * The document's scrollWidth is also printed, and it is the LEAST useful of the
 * three. 20a measured exactly that, at four viewports, and passed at all four
 * while a phase row was 7px wider than the box it was packed into and every
 * node head up to 22px wider than its own node: a box that overflows its parent
 * never reaches the document if anything above it clips. An instrument aimed at
 * the wrong scope reads green. This one asks every box about its own container.
 *
 *     node scripts/measure-page.mjs                        # both fixtures
 *     node scripts/measure-page.mjs --fixture in-flight
 *     node scripts/measure-page.mjs --viewport 390x844
 *     node scripts/measure-page.mjs --json /tmp/page.json  # everything measured
 *     node scripts/measure-page.mjs --top 30               # more overflow rows
 *
 * CHROMIUM_PATH= on a machine whose chromium is not the pinned build, exactly
 * as for check-contrast.mjs.
 *
 * Exit status: 0 when it measured, 2 when it refused to.
 */
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SITE = path.join(ROOT, "site");
const FIXTURES = path.join(ROOT, "tests/fixtures/page-measure");

const VIEWPORTS = [
  { name: "2560x1440", width: 2560, height: 1440, note: "the stated primary target" },
  { name: "1920x1080", width: 1920, height: 1080 },
  { name: "1440x900", width: 1440, height: 900 },
  { name: "390x844", width: 390, height: 844, note: "the phone" }
];

function refuse(message) {
  console.error(`measure-page: ${message}`);
  process.exit(2);
}

function arg(flag, fallback = null) {
  const i = process.argv.indexOf(flag);
  return i === -1 ? fallback : process.argv[i + 1];
}

// Same loader as check-contrast.mjs: Playwright lives with the suites that use
// it, and guessing a location is not evidence.
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

function readFixture(name) {
  const dir = path.join(FIXTURES, name);
  if (!fs.existsSync(dir)) {
    refuse(`no fixture set called "${name}" in ${path.relative(ROOT, FIXTURES)}.`);
  }
  const read = (file) => {
    const p = path.join(dir, file);
    if (!fs.existsSync(p)) refuse(`${path.relative(ROOT, p)} is missing.`);
    try {
      return JSON.parse(fs.readFileSync(p, "utf8"));
    } catch (e) {
      refuse(`${path.relative(ROOT, p)} is not valid JSON: ${e.message}`);
    }
  };
  const meta = read("meta.json");
  if (!meta.now) refuse(`${name}/meta.json declares no \`now\`; the clock would drift and the figures with it.`);
  return {
    name,
    meta,
    runs: read("runs.json"),
    jobs: read("jobs.json"),
    status: { stage: read("status-stage.json"), prod: read("status-prod.json") }
  };
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

function serveSite() {
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://127.0.0.1");
    let file = path.join(SITE, decodeURIComponent(url.pathname));
    if (url.pathname.endsWith("/")) file = path.join(file, "index.html");
    if (!file.startsWith(SITE) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
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

// ---- what runs inside the page -------------------------------------------
// One function, stringified once, so the browser and this file cannot drift.
function measureInPage() {
  const round = (n) => Math.round(n * 100) / 100;

  function describe(el) {
    if (!el || el === document.body) return "body";
    let s = el.tagName.toLowerCase();
    if (el.id) s += "#" + el.id;
    const cls = (el.className && typeof el.className === "string" ? el.className : "")
      .trim().split(/\s+/).filter(Boolean).slice(0, 2);
    if (cls.length) s += "." + cls.join(".");
    return s;
  }
  function pathOf(el) {
    const parts = [];
    let cur = el;
    for (let i = 0; i < 4 && cur && cur !== document.body; i += 1) {
      parts.unshift(describe(cur));
      cur = cur.parentElement;
    }
    return parts.join(" > ");
  }

  const beyondParent = [];
  const contentWide = [];

  for (const el of document.querySelectorAll("body *")) {
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;

    // Its own content against its own box. A table inside a clipping wrapper
    // shows up here and nowhere else.
    const self = el.scrollWidth - el.clientWidth;
    if (self > 1 && el.clientWidth > 0) {
      contentWide.push({
        path: pathOf(el),
        over: round(self),
        box: round(el.clientWidth),
        content: round(el.scrollWidth),
        overflowX: cs.overflowX
      });
    }

    // Its border edge against its parent's padding edge. Absolute and fixed
    // boxes are measured against a different containing block, so they are not
    // asked this question.
    if (cs.position === "absolute" || cs.position === "fixed") continue;
    const p = el.parentElement;
    if (!p || p === document.body) continue;
    const pcs = getComputedStyle(p);
    const pr = p.getBoundingClientRect();
    const left = pr.left + parseFloat(pcs.borderLeftWidth || "0");
    const right = pr.right - parseFloat(pcs.borderRightWidth || "0");
    const over = Math.max(r.right - right, left - r.left);
    if (over > 1) {
      beyondParent.push({
        path: pathOf(el),
        parent: pathOf(p),
        over: round(over),
        width: round(r.width),
        parentWidth: round(right - left),
        parentOverflowX: pcs.overflowX
      });
    }
  }

  // ---- the packing ---------------------------------------------------------
  // A box against the ROW it shares, rather than against its parent. Rows are
  // recovered from the boxes' own tops rather than from the grid, because a
  // phase that spans two columns is still one row and a panel that spans two
  // rows is in both - the geometry is the ground truth here, not the CSS.
  function rowsOf(items) {
    const rows = [];
    for (const it of items) {
      let row = rows.find((r) => Math.abs(r.top - it.top) < 4);
      if (!row) { row = { top: it.top, height: 0, items: [] }; rows.push(row); }
      row.items.push(it);
    }
    rows.sort((a, b) => a.top - b.top);
    for (const r of rows) {
      r.height = round(Math.max(...r.items.map((i) => i.height)));
      // Against the ROW, not against the box: a stretched box IS the row's
      // height, and the air is the part of it nothing is drawn in.
      for (const i of r.items) i.air = round(Math.max(0, r.height - (i.filled ?? i.height)));
    }
    return rows;
  }
  const boxOf = (el, label, extra = {}) => {
    const b = el.getBoundingClientRect();
    return { label, top: round(b.top + window.scrollY), width: round(b.width), height: round(b.height), ...extra };
  };
  // FILLED, NOT JUST TALL. Since 20j the phases are stretched to their row, so a
  // box's height stops answering "how much of it is used" - and an instrument
  // that reported air as zero here would be hiding the comb rather than
  // measuring it. `filled` is where the last thing in the box ends.
  const filledHeight = (el) => {
    const box = el.getBoundingClientRect();
    const last = el.lastElementChild;
    if (!last) return round(box.height);
    const cs = getComputedStyle(el);
    return round(last.getBoundingClientRect().bottom - box.top + parseFloat(cs.paddingBottom || "0") +
      parseFloat(cs.borderBottomWidth || "0"));
  };
  const host = document.querySelector("#rows");
  const phases = host
    ? [...host.querySelectorAll(":scope > .phase")].map((ph) =>
        boxOf(ph, (ph.querySelector(":scope > header b") || { textContent: "?" }).textContent.trim(), {
          wide: ph.dataset.wide === "1",
          nodes: ph.querySelectorAll(":scope > .set > .node").length,
          headHeight: round(ph.querySelector(":scope > header").getBoundingClientRect().height),
          filled: filledHeight(ph)
        })
      )
    : [];
  const panels = [...document.querySelectorAll(".top > .panel")].map((p) =>
    boxOf(p, [...p.classList].filter((c) => c !== "panel").join(".") || "panel", { filled: filledHeight(p) })
  );
  const packing = {
    columns: host ? getComputedStyle(host).gridTemplateColumns.split(" ").filter(Boolean).length : 0,
    mapHeight: host ? round(host.getBoundingClientRect().height) : 0,
    mapRows: rowsOf(phases),
    topRows: rowsOf(panels)
  };
  packing.air = round(packing.mapRows.reduce((a, r) => a + r.items.reduce((b, i) => b + i.air, 0), 0));

  // ---- a broken word -------------------------------------------------------
  // Deliberately breakable text says so: `overflow-wrap: anywhere` is on the
  // identifier fields, the ARNs and the long links, and it is INHERITED, so the
  // question is asked of the text node's own parent and answers for its
  // ancestors too.
  const broken = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    if (!n.nodeValue || !n.nodeValue.trim()) continue;
    const parent = n.parentElement;
    if (!parent) continue;
    const cs = getComputedStyle(parent);
    if (cs.display === "none" || cs.visibility === "hidden") continue;
    if (cs.overflowWrap === "anywhere" || cs.wordBreak === "break-all") continue;
    const words = /[^\s]{4,}/g;
    let m;
    while ((m = words.exec(n.nodeValue))) {
      const range = document.createRange();
      range.setStart(n, m.index);
      range.setEnd(n, m.index + m[0].length);
      if ([...range.getClientRects()].filter((r) => r.width > 0.5).length > 1) {
        broken.push({ word: m[0], where: pathOf(parent) });
      }
    }
  }

  // ---- the floor, derived --------------------------------------------------
  // For every node the map draws: the widest single word in its name, and the
  // whole name on one line. Each is reported as the NODE width it implies, by
  // adding back everything between the name's box and the node's - the icon,
  // the gaps, the padding - so the number can be compared with --node-min.
  const floors = [];
  for (const node of document.querySelectorAll("#rows .node")) {
    const name = node.querySelector(".head .name");
    if (!name) continue;
    const chrome = node.getBoundingClientRect().width - name.getBoundingClientRect().width;
    let widest = 0;
    let word = "";
    for (const tn of [...name.childNodes].filter((x) => x.nodeType === 3)) {
      const words = /[^\s]+/g;
      let m;
      while ((m = words.exec(tn.nodeValue))) {
        const range = document.createRange();
        range.setStart(tn, m.index);
        range.setEnd(tn, m.index + m[0].length);
        const w = [...range.getClientRects()].reduce((a, r) => a + r.width, 0);
        if (w > widest) { widest = w; word = m[0]; }
      }
    }
    if (!widest) continue;
    const whole = document.createRange();
    whole.selectNodeContents(name);
    const lines = [...whole.getClientRects()].filter((r) => r.width > 0.5);
    floors.push({
      word,
      lines: lines.length,
      wholeWord: round(widest + chrome),
      oneLine: round(lines.reduce((a, r) => a + r.width, 0) + chrome),
      nodeWidth: round(node.getBoundingClientRect().width)
    });
  }

  // Same shape, same place: collapse the twelve identical table rows into one
  // row with a count, keeping the worst.
  function group(list, key) {
    const byKey = new Map();
    for (const item of list) {
      const k = key(item);
      const seen = byKey.get(k);
      if (!seen) byKey.set(k, { ...item, count: 1 });
      else {
        seen.count += 1;
        if (item.over > seen.over) Object.assign(seen, item, { count: seen.count });
      }
    }
    return [...byKey.values()].sort((a, b) => b.over - a.over);
  }

  const doc = document.documentElement;
  return {
    height: doc.scrollHeight,
    docOverflowX: round(doc.scrollWidth - doc.clientWidth),
    beyondParent: group(beyondParent, (i) => i.path + " | " + i.parent),
    contentWide: group(contentWide, (i) => i.path),
    packing,
    broken: (() => {
      const byKey = new Map();
      for (const b of broken) {
        const k = b.word + " | " + b.where;
        const seen = byKey.get(k);
        if (seen) seen.count += 1;
        else byKey.set(k, { ...b, count: 1 });
      }
      return [...byKey.values()];
    })(),
    floors: floors.sort((a, b) => b.wholeWord - a.wholeWord),
    banner: (() => {
      const b = document.querySelector(".banner.bad");
      return b ? b.textContent.trim().replace(/\s+/g, " ").slice(0, 160) : null;
    })()
  };
}

async function main() {
  if (!fs.existsSync(path.join(SITE, "index.html"))) {
    refuse("site/index.html does not exist. Run `make site-page` first.");
  }
  const chromium = await loadChromium();
  const wanted = arg("--fixture");
  const sets = (wanted ? [wanted] : ["at-rest", "in-flight"]).map(readFixture);
  const viewportFilter = arg("--viewport");
  const viewports = viewportFilter ? VIEWPORTS.filter((v) => v.name === viewportFilter) : VIEWPORTS;
  if (!viewports.length) refuse(`no viewport called "${viewportFilter}".`);
  const top = Number(arg("--top", "12"));

  const { server, port } = await serveSite();
  const origin = `http://127.0.0.1:${port}`;
  const launch = { args: ["--no-sandbox"] };
  if (process.env.CHROMIUM_PATH) launch.executablePath = process.env.CHROMIUM_PATH;
  const browser = await chromium.launch(launch);

  const results = [];
  for (const fixture of sets) {
    for (const viewport of viewports) {
      for (const cuts of ["closed", "open"]) {
        const context = await browser.newContext({
          viewport: { width: viewport.width, height: viewport.height }
        });
        const page = await context.newPage();
        await page.clock.setFixedTime(new Date(fixture.meta.now));

        const unmocked = [];
        await page.route("**/*", async (route) => {
          const url = route.request().url();
          if (url.startsWith(origin)) {
            if (/\/status\/(stage|prod)\.json/.test(url)) {
              const env = url.includes("stage") ? "stage" : "prod";
              return route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify(fixture.status[env])
              });
            }
            return route.continue();
          }
          if (url.startsWith("https://api.github.com/")) {
            const body = /\/jobs(\?|$)/.test(url) ? fixture.jobs : fixture.runs;
            return route.fulfill({
              status: 200,
              contentType: "application/json",
              headers: { "x-ratelimit-remaining": "57", "x-ratelimit-reset": String(Math.floor(Date.parse(fixture.meta.now) / 1000) + 1800) },
              body: JSON.stringify(body)
            });
          }
          // Anything else leaving the origin is a source nobody declared. It is
          // recorded rather than quietly failed, because a page missing a
          // source is a SHORTER page, not an obviously broken one.
          unmocked.push(url);
          return route.abort();
        });

        await page.goto(origin + "/index.html", { waitUntil: "load" });
        // The two readers resolve and render; the map draws from the same
        // observation. There is no event that says "settled", so this waits for
        // the network to go quiet and then a beat for the layout.
        await page.waitForLoadState("networkidle");
        await page.waitForTimeout(400);

        if (cuts === "open") {
          await page.evaluate(() => {
            document.querySelectorAll("details").forEach((d) => { d.open = true; });
          });
          await page.waitForTimeout(300);
        }

        const measured = await page.evaluate(measureInPage);
        if (unmocked.length) {
          await browser.close();
          server.close();
          refuse(
            "the page asked for a source nobody mocked, so this measurement would be of a page " +
              "missing part of itself:\n  " + [...new Set(unmocked)].join("\n  ")
          );
        }
        if (measured.banner) {
          await browser.close();
          server.close();
          refuse(
            `the page drew a source-failure banner - "${measured.banner}". A page that could not read ` +
              "its sources is shorter than the real one, and its figures mean nothing."
          );
        }
        results.push({ fixture: fixture.name, viewport: viewport.name, cuts, ...measured,
          screens: Math.round((measured.height / viewport.height) * 10) / 10 });
        await context.close();
      }
    }
  }
  await browser.close();
  server.close();

  // ---- report -------------------------------------------------------------
  console.log("page height - document.scrollHeight, and screens of the viewport it was measured in\n");
  console.log("  fixture     viewport    cuts      height    screens   doc overflow-x");
  for (const r of results) {
    console.log(
      "  " + r.fixture.padEnd(12) + r.viewport.padEnd(12) + r.cuts.padEnd(10) +
      (r.height + "px").padStart(7) + "  " + String(r.screens).padStart(8) + "   " +
      (r.docOverflowX > 1 ? r.docOverflowX + "px" : "-")
    );
  }

  for (const r of results) {
    if (!r.beyondParent.length && !r.contentWide.length) continue;
    console.log(`\n${r.fixture} · ${r.viewport} · cuts ${r.cuts}`);
    if (r.beyondParent.length) {
      console.log("  beyond its parent's padding edge");
      for (const f of r.beyondParent.slice(0, top)) {
        console.log(
          `    ${String(f.over + "px").padStart(8)}  ${f.path}` +
          (f.count > 1 ? `  (x${f.count})` : "") +
          `\n              in ${f.parent}  ${f.width}px in ${f.parentWidth}px` +
          (f.parentOverflowX !== "visible" ? `  parent overflow-x: ${f.parentOverflowX}` : "")
        );
      }
      if (r.beyondParent.length > top) console.log(`    ... ${r.beyondParent.length - top} more`);
    }
    if (r.contentWide.length) {
      console.log("  content wider than its own box");
      for (const f of r.contentWide.slice(0, top)) {
        console.log(
          `    ${String(f.over + "px").padStart(8)}  ${f.path}` +
          (f.count > 1 ? `  (x${f.count})` : "") +
          `\n              ${f.content}px of content in a ${f.box}px box, overflow-x: ${f.overflowX}`
        );
      }
      if (r.contentWide.length > top) console.log(`    ... ${r.contentWide.length - top} more`);
    }
  }

  // ---- the packing, and what it costs in air ------------------------------
  console.log("\nthe packing - every box against the height of the row it shares\n");
  for (const r of results) {
    if (r.cuts !== "closed") continue;
    console.log(`${r.fixture} · ${r.viewport} · map ${r.packing.mapHeight}px in ${r.packing.columns} columns · air ${r.packing.air}px`);
    for (const [what, rows] of [["top", r.packing.topRows], ["map", r.packing.mapRows]]) {
      for (const row of rows) {
        console.log(`  ${what} row  ${String(row.height + "px").padStart(8)}`);
        for (const it of row.items) {
          console.log(
            `    ${String((it.filled ?? it.height) + "px").padStart(8)} filled  air ${String(it.air + "px").padStart(8)}` +
            `  w ${String(it.width + "px").padStart(8)}` +
            (it.nodes !== undefined ? `  ${it.wide ? "wide" : "    "} ${String(it.nodes).padStart(2)} nodes  head ${it.headHeight}px` : "") +
            `  ${it.label}`
          );
        }
      }
    }
  }

  // ---- a word the line box split ------------------------------------------
  console.log("\nbroken words - a word split across two lines, outside the fields that break on purpose\n");
  for (const r of results) {
    if (!r.broken.length) continue;
    console.log(`${r.fixture} · ${r.viewport} · cuts ${r.cuts}`);
    for (const b of r.broken) console.log(`    ${b.word}${b.count > 1 ? ` (x${b.count})` : ""}   ${b.where}`);
  }
  if (!results.some((r) => r.broken.length)) console.log("  none, at any viewport measured");

  // ---- the floor the map is folded at -------------------------------------
  console.log("\nthe floor - what the narrowest node would have to be, derived from what a node draws\n");
  const allFloors = results.filter((r) => r.cuts === "closed").flatMap((r) => r.floors);
  const worstWord = allFloors.reduce((a, b) => (b.wholeWord > a.wholeWord ? b : a), allFloors[0]);
  const worstLine = allFloors.reduce((a, b) => (b.oneLine > a.oneLine ? b : a), allFloors[0]);
  if (worstWord) {
    console.log(`  every word whole   ${worstWord.wholeWord}px   the widest is "${worstWord.word}"`);
    console.log(`  every name unwrapped ${worstLine.oneLine}px`);
    console.log("  --node-min is the claim these two numbers are about.");
  }

  const jsonOut = arg("--json");
  if (jsonOut) {
    fs.writeFileSync(jsonOut, JSON.stringify({ measured: results }, null, 2));
    console.log(`\nwritten: ${jsonOut}`);
  }
}

main();
