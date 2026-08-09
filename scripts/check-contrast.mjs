#!/usr/bin/env node
/**
 * THE GATE UNDER ADR-0047 D6: no state on the map rides a boundary the eye
 * cannot find, and the floor is WCAG 1.4.11's 3:1.
 *
 * Three of the six states went under that floor without anybody choosing it.
 * Nobody edited a state colour to be fainter; `color-mix(... , var(--line))`
 * eats contrast quietly, and the next palette edit will do it again. This is
 * what refuses.
 *
 * WHY A BROWSER, when every other gate here is a script over a file.
 *
 * Because the thing under test is what the visitor's engine RESOLVES, and the
 * one measurement this project has already got wrong was got wrong in a colour
 * parser: `color-mix()` resolves to `color(srgb 0.44 0.62 0.90)`, whose
 * components are already 0..1, the parser divided them by 255, and six
 * different colours came back at 20.92:1. A reading that is wrong and looks
 * like a finding is this project's recurring shape - the pipe that measured
 * grep's exit status, the bytecode cache that measured itself. So the engine
 * resolves the colour, and the arithmetic that follows is checked by a CONTROL
 * on every single run: black on white must read 21.00, through the hex
 * notation AND through the srgb-float notation color-mix() produces. If either
 * control is off, nothing else this script printed means anything and it
 * refuses without a verdict.
 *
 * WHAT IT READS. `site/index.html` - the BUILT page, not the template - and it
 * lifts the <style> blocks out of it, exactly as check-live-state.mjs lifts the
 * run-layer state machine out of the same file. A copy of the palette in a
 * fixture would be one definition on two hosts, which is how the image scan
 * came to scan postgres.
 *
 * WHAT IT MEASURES, stated because a contrast number without a model is a
 * number nobody can reproduce:
 *
 *   the probe colour        the state's boundary, as computed
 *   its backdrop            the node's OWN background, composited down through
 *                           its ancestors until something opaque stops it.
 *                           Under `background-clip: border-box` - the default -
 *                           the element's background runs under its border, so
 *                           that is genuinely what the boundary sits on.
 *   opacity                 an element with `opacity` is composited as a GROUP:
 *                           boundary and background together, over what is
 *                           behind them. `absent` is dimmed that way, and a
 *                           model that ignored it would flatter the state that
 *                           is furthest under the floor.
 *   the ratio               WCAG 2.x relative luminance, (L1+.05)/(L2+.05)
 *
 * Both themes, because `prefers-color-scheme: dark` is a different palette and
 * the light one is not evidence about it.
 *
 * WHAT IT CANNOT SEE. Whether the state is legible - only whether its boundary
 * is findable. The second channel ADR-0047 D6 requires is a WORD on the node,
 * and no colour measurement can check that a word is there. That is the map's
 * own gate's job, and it is not this one's.
 *
 *     make contrast-check
 *     node scripts/check-contrast.mjs            # same thing
 *     node scripts/check-contrast.mjs --verbose  # prints the composite stack
 */
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CONTRACT = path.join(ROOT, "assets/contrast-contract.json");
const VERBOSE = process.argv.includes("--verbose");

function refuse(message) {
  console.error(`contrast-check: ${message}`);
  process.exit(2);
}

// Playwright lives with the suites that use it, not at the repository root, so
// this refuses rather than guessing a location - the same rule collect-suites.py
// follows for the interpreters it needs.
async function loadChromium() {
  const candidates = [
    process.env.PLAYWRIGHT_MODULE,
    path.join(ROOT, "tests/playwright/node_modules/@playwright/test/index.js"),
    path.join(ROOT, "tests/playwright/node_modules/playwright/index.js"),
  ].filter(Boolean);
  const found = [];
  for (const candidate of candidates) {
    if (!fs.existsSync(candidate)) continue;
    found.push(candidate);
    // These packages are CommonJS. import() of CJS puts module.exports on
    // `default`, and whether a named export is also synthesised depends on what
    // the lexer could see - so take either, rather than assuming the shape.
    const mod = await import(pathToFileURL(candidate).href);
    const chromium = mod.chromium || (mod.default && mod.default.chromium);
    if (chromium) return chromium;
  }
  if (found.length) {
    refuse(
      "Playwright is installed but exports no `chromium`:\n  " +
        found.join("\n  ") +
        "\n  A browser is what resolves color-mix(); there is no fallback that would be evidence."
    );
  }
  refuse(
    "Playwright is not installed where this expects it.\n" +
      "  Looked in: " + candidates.join(", ") + "\n" +
      "  Run `npm ci` in tests/playwright, or set PLAYWRIGHT_MODULE."
  );
}

function readContract() {
  if (!fs.existsSync(CONTRACT)) {
    refuse(`${path.relative(ROOT, CONTRACT)} is missing. There is nothing to check against.`);
  }
  let contract;
  try {
    contract = JSON.parse(fs.readFileSync(CONTRACT, "utf8"));
  } catch (error) {
    refuse(`${path.relative(ROOT, CONTRACT)} is not valid JSON: ${error.message}`);
  }
  if (typeof contract.floor !== "number") refuse("the contract declares no numeric `floor`.");
  if (!Array.isArray(contract.states) || contract.states.length === 0) {
    // A contract with no states would print a clean table and a green verdict,
    // which is the empty result that looks like success.
    refuse("the contract names no states. Zero states checked is not a pass.");
  }
  if (!Array.isArray(contract.control) || contract.control.length === 0) {
    refuse("the contract carries no control. An instrument nobody checked has no verdict to give.");
  }
  const ids = contract.states.map((s) => s.id);
  const duplicate = ids.find((id, i) => ids.indexOf(id) !== i);
  if (duplicate) refuse(`the contract names the state "${duplicate}" twice.`);
  return contract;
}

function readStyles(pageRelative) {
  const page = path.join(ROOT, pageRelative);
  if (!fs.existsSync(page)) {
    refuse(`${pageRelative} does not exist. Run \`make site-page\` first.`);
  }
  const html = fs.readFileSync(page, "utf8");
  const blocks = [...html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((m) => m[1]);
  if (blocks.length === 0) {
    refuse(`${pageRelative} contains no <style> block. There is no palette to measure.`);
  }
  return blocks.join("\n");
}

function fixture(css, contract) {
  const open = contract.chain
    .map((n) => `<${n.tag}${n.class ? ` class="${n.class}"` : ""}>`)
    .join("");
  const close = [...contract.chain].reverse().map((n) => `</${n.tag}>`).join("");

  const probes = [
    ...contract.control.map(
      (c, i) => `<div id="control-${i}" style="${c.style}">control</div>`
    ),
    ...contract.states.map(
      (s) => `<div id="state-${s.id}" class="${s.class}"><div class="head"><span class="name">${s.id}</span></div></div>`
    ),
  ].join("");

  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><style>${css}</style></head><body>${open}${probes}${close}</body></html>`;
}

// Everything below runs INSIDE the page, serialised and evaluated by the engine
// whose colour resolution is the point of using a browser at all. It therefore
// closes over nothing: every helper it needs is declared inside it.
function MEASURE(spec) {
  function parse(value) {
    const v = String(value).trim();
    let m = v.match(/^rgba?\(([^)]+)\)$/);
    if (m) {
      const parts = m[1].split(/[,/\s]+/).filter(Boolean).map(Number);
      if (parts.length < 3 || parts.some(Number.isNaN)) return null;
      return { r: parts[0] / 255, g: parts[1] / 255, b: parts[2] / 255, a: parts.length > 3 ? parts[3] : 1 };
    }
    // color(srgb x y z / a) - components ALREADY 0..1. Dividing these by 255 is
    // the exact defect this gate was built after; the control catches it.
    m = v.match(/^color\(srgb\s+([^)]+)\)$/);
    if (m) {
      const parts = m[1].split(/[,/\s]+/).filter(Boolean).map(Number);
      if (parts.length < 3 || parts.some(Number.isNaN)) return null;
      return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
    }
    if (v === "transparent") return { r: 0, g: 0, b: 0, a: 0 };
    return null;
  }

  function over(top, bottom) {
    const a = top.a + bottom.a * (1 - top.a);
    if (a === 0) return { r: 0, g: 0, b: 0, a: 0 };
    return {
      r: (top.r * top.a + bottom.r * bottom.a * (1 - top.a)) / a,
      g: (top.g * top.a + bottom.g * bottom.a * (1 - top.a)) / a,
      b: (top.b * top.a + bottom.b * bottom.a * (1 - top.a)) / a,
      a: a,
    };
  }

  function lum(c) {
    const f = (x) => (x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4));
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  }

  function ratio(x, y) {
    const a = lum(x), b = lum(y);
    const hi = Math.max(a, b), lo = Math.min(a, b);
    return (hi + 0.05) / (lo + 0.05);
  }

  // The stack BEHIND an element: its ancestors' backgrounds, composited from
  // the element outwards, each one dimmed by its own opacity group. Stops at
  // the first fully opaque result; refuses to invent a page colour if it never
  // gets one.
  function backdrop(el) {
    let acc = { r: 0, g: 0, b: 0, a: 0 };
    const trail = [];
    let node = el.parentElement;
    while (node) {
      const cs = getComputedStyle(node);
      const bg = parse(cs.backgroundColor);
      if (!bg) return { error: "unparseable background on <" + node.tagName.toLowerCase() + ">: " + cs.backgroundColor };
      const op = parseFloat(cs.opacity);
      const dimmed = { r: bg.r, g: bg.g, b: bg.b, a: bg.a * (Number.isNaN(op) ? 1 : op) };
      acc = over(acc, dimmed);
      trail.push(node.tagName.toLowerCase() + (node.className ? "." + String(node.className).trim().split(/\s+/).join(".") : "") + " " + cs.backgroundColor + (op !== 1 ? " @" + op : ""));
      if (acc.a >= 0.999) return { colour: acc, trail: trail };
      node = node.parentElement;
    }
    return { error: "nothing behind this element is opaque; refusing to assume a page colour" };
  }

  const out = [];
  for (const item of spec) {
    const el = document.getElementById(item.dom);
    if (!el) { out.push({ id: item.id, error: "probe element " + item.dom + " is not in the fixture" }); continue; }
    const target = item.on === "self" ? el : el;
    const cs = item.on === "self" ? getComputedStyle(target) : getComputedStyle(target, item.on);
    const raw = cs.getPropertyValue(item.property);
    const fg = parse(raw);
    if (!fg) { out.push({ id: item.id, error: "cannot read " + item.property + " as a colour: " + JSON.stringify(raw) }); continue; }

    const behind = backdrop(el);
    if (behind.error) { out.push({ id: item.id, error: behind.error }); continue; }

    const own = parse(getComputedStyle(el).backgroundColor);
    if (!own) { out.push({ id: item.id, error: "cannot read the element's own background: " + getComputedStyle(el).backgroundColor }); continue; }

    // Inside the group: the boundary sits on the element's own background,
    // which runs under it (background-clip: border-box).
    const inner = over(own, behind.colour);
    const edge = over(fg, inner);

    // The group as a whole is then composited over what is behind it.
    const op = parseFloat(getComputedStyle(el).opacity);
    const group = Number.isNaN(op) ? 1 : op;
    const seenEdge = over({ r: edge.r, g: edge.g, b: edge.b, a: group }, behind.colour);
    const seenInner = over({ r: inner.r, g: inner.g, b: inner.b, a: group }, behind.colour);

    out.push({
      id: item.id,
      raw: raw,
      opacity: group,
      ratio: ratio(seenEdge, seenInner),
      edge: [seenEdge.r, seenEdge.g, seenEdge.b],
      against: [seenInner.r, seenInner.g, seenInner.b],
      trail: behind.trail,
    });
  }
  return out;
}

function hex(c) {
  return (
    "#" +
    c
      .map((x) => Math.round(Math.max(0, Math.min(1, x)) * 255).toString(16).padStart(2, "0"))
      .join("")
  );
}

async function main() {
  const contract = readContract();
  const css = readStyles(contract.page);
  const chromium = await loadChromium();

  const spec = [
    ...contract.control.map((c, i) => ({
      id: c.id,
      dom: `control-${i}`,
      on: "self",
      property: "border-top-color",
      control: c.expect,
    })),
    ...contract.states.map((s) => ({
      id: s.id,
      dom: `state-${s.id}`,
      on: s.probe.on,
      property: s.probe.property,
    })),
  ];

  const launch = {};
  if (process.env.CHROMIUM_PATH) launch.executablePath = process.env.CHROMIUM_PATH;
  const browser = await chromium.launch(launch);

  const results = {};
  for (const theme of ["light", "dark"]) {
    const context = await browser.newContext({ colorScheme: theme });
    const page = await context.newPage();
    await page.setContent(fixture(css, contract), { waitUntil: "load" });
    results[theme] = await page.evaluate(MEASURE, spec);
    await context.close();
  }
  await browser.close();

  const problems = [];

  // The instrument first. Nothing below this means anything until it passes,
  // so a control that is off is a REFUSAL and not a failing check: a failing
  // check invites reading the table underneath it.
  console.log("control  — black on white must read 21.00 through every notation the CSS uses");
  for (const theme of ["light", "dark"]) {
    for (const item of spec.filter((s) => s.control)) {
      const got = results[theme].find((r) => r.id === item.id);
      if (!got || got.error) {
        refuse(`the control "${item.id}" could not be measured in the ${theme} theme: ${got ? got.error : "missing"}`);
      }
      const ok = Math.abs(got.ratio - item.control) < 0.005;
      console.log(`  ${theme.padEnd(5)}  ${got.ratio.toFixed(2).padStart(6)}  ${item.id}`);
      if (!ok) {
        refuse(
          `the control "${item.id}" reads ${got.ratio.toFixed(2)} in the ${theme} theme, not ${item.control.toFixed(2)}.\n` +
            "  The instrument is wrong, so no verdict is available. Nothing above is evidence."
        );
      }
    }
  }

  console.log(`\nstate encoding — floor ${contract.floor.toFixed(1)}:1 (WCAG 1.4.11), boundary against the node's own background`);
  console.log(`  ${"state".padEnd(12)}${"light".padStart(8)}${"dark".padStart(8)}`);
  for (const state of contract.states) {
    const row = {};
    for (const theme of ["light", "dark"]) {
      const got = results[theme].find((r) => r.id === state.id);
      if (!got) refuse(`the state "${state.id}" was not measured in the ${theme} theme.`);
      if (got.error) refuse(`the state "${state.id}" could not be measured in the ${theme} theme: ${got.error}`);
      row[theme] = got;
    }
    const mark = (theme) => {
      if (state.exempt) return " ";
      return row[theme].ratio < contract.floor ? "<" : " ";
    };
    const note = state.exempt ? "  exempt — the word carries it" : "";
    console.log(
      `  ${state.id.padEnd(12)}` +
        `${row.light.ratio.toFixed(2).padStart(7)}${mark("light")}` +
        `${row.dark.ratio.toFixed(2).padStart(7)}${mark("dark")}` +
        note
    );
    if (VERBOSE) {
      for (const theme of ["light", "dark"]) {
        console.log(`      ${theme}: ${row[theme].raw} -> ${hex(row[theme].edge)} on ${hex(row[theme].against)}` + (row[theme].opacity !== 1 ? ` (opacity ${row[theme].opacity})` : ""));
        for (const line of row[theme].trail) console.log(`        behind: ${line}`);
      }
    }
    if (state.exempt) continue;
    for (const theme of ["light", "dark"]) {
      if (row[theme].ratio < contract.floor) {
        problems.push(
          `${state.id} (${state.what}) is ${row[theme].ratio.toFixed(2)}:1 in the ${theme} theme, under the ${contract.floor.toFixed(1)}:1 floor`
        );
      }
    }
  }

  if (problems.length) {
    console.log("\ncontrast-check: FAILED");
    for (const p of problems) console.log(`  ${p}`);
    console.log(
      "\n  ADR-0047 D6: no state rides a boundary the eye cannot find. Raise the\n" +
        "  colour, or carry the state on a second channel and say so in\n" +
        "  assets/contrast-contract.json."
    );
    return 1;
  }
  console.log(`\ncontrast-check: ${contract.states.length} states, both themes, none under the floor`);
  return 0;
}

main().then(
  (code) => process.exit(code),
  (error) => {
    console.error("contrast-check: " + (error && error.stack ? error.stack : error));
    process.exit(2);
  }
);
