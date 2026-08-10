#!/usr/bin/env node
/**
 * The gate over the page's TENSE - what it claims about WHEN a figure is true.
 *
 * Every number the map draws comes out of a file published when a cycle ENDS.
 * So while a run is going the page is describing the cycle before it, and at
 * rest it is describing a cycle rather than the present. On 2026-08-09 a live
 * stage cycle was watched (Phase 20h) and the page said three things in the
 * present tense that were not about the present:
 *
 *   1. A phase that finished mid-run printed the PREVIOUS cycle's duration
 *      beside a green `done`, with no label. The apply had taken 8m 30s; the
 *      page said 8m 26s. Four seconds - a defect that answers rather than one
 *      that stops, and invisible to any eye.
 *   2. `ECR push` and `migrate + seed` read `not run yet` minutes after
 *      running. Neither is a Terraform resource, so no timeline will ever carry
 *      them: the sentence was not stale, it was permanently false.
 *   3. A stage verified gone from AWS kept every icon at full colour while
 *      prod, in the identical state, stayed grey. `absent` means "no record",
 *      never "not in AWS", and the two had been drawn alike since the map
 *      existed.
 *
 * None of the three was visible to a check, because there was no check: the
 * `last time` label appeared nowhere outside site/index.html. This gate is that
 * check, and it is built like check-live-state.mjs for the same reason - the
 * decision runs in the visitor's browser, so a copy of it in Python would be
 * one definition on two hosts. It LIFTS THE BLOCKS OUT OF THE BUILT PAGE:
 *
 *     site/index.html
 *       ==== RUN HISTORY TENSE - begin ====      the dashboard's script
 *         historyTally(runs)
 *       ==== RUN HISTORY TENSE - end ====
 *
 *       ==== PAGE TENSE - begin ====             the map's script
 *         figuresAreOlder(observation)
 *         envTense(observation, env)
 *         underWayHere(observation, env)
 *         nodeTense(node, record, envs, underWay)
 *       ==== PAGE TENSE - end ====
 *
 * TWO BLOCKS AND ONE SET, because the page is two scripts and the map's is
 * WRAPPED - deliberately, so that neither script has to know the other's
 * identifier list. historyTally() joined the set in 22 and is the same species:
 * the run-history badge scored a run that had not finished as one that had
 * succeeded, counting failures among completed runs and dividing by every run
 * there was. It was first written inside the map's wrapper, where its caller
 * could not see it - renderHistory() threw on every tick and took the whole
 * re-read down with it, which only check-page-freshness.mjs could see. A
 * function lives beside its caller; this gate follows it there rather than
 * making the page put them in one scope to be testable.
 *
 * The blocks are evaluated in ONE context, so a name defined in either is
 * callable from a case, and the coupling check below is run against everything
 * outside BOTH of them.
 *
 * The cases are FLAT JSON FILES rather than a directory each: unlike the live
 * state machine, which folds one whole observation into one whole answer, these
 * are three small functions and a case is one call and one expected value. A
 * directory per call would be ceremony over a two-line fixture.
 *
 *     scripts/check-page-tense.mjs
 *     scripts/check-page-tense.mjs --case a-destroyed-environment-is-not-a-live-one
 *
 * Exit status: 0 if every case matches, 1 otherwise.
 */
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(HERE);
const PAGE = path.join(ROOT, "site", "index.html");
const CASES = path.join(ROOT, "tests", "fixtures", "page-tense", "cases");

// Two blocks, in two scripts, evaluated as one set. Adding a third is adding a
// line here; what may not happen is a tense decision living in neither.
const BLOCKS = [
  { begin: "==== PAGE TENSE - begin", end: "==== PAGE TENSE - end" },
  { begin: "==== RUN HISTORY TENSE - begin", end: "==== RUN HISTORY TENSE - end" },
];
const API = ["figuresAreOlder", "envTense", "underWayHere", "nodeTense", "historyTally"];

function refuse(why) {
  console.log(`page-tense-check: REFUSED\n${why}`);
  process.exit(1);
}

/** Comments out, so a sentence ABOUT a call cannot stand in for the call. */
function strip(source) {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, " ")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}

/** Lift every block out of the built page and evaluate them in one context. */
function loadTense() {
  if (!fs.existsSync(PAGE)) {
    refuse(`site/index.html does not exist. Build it with \`make site-page\`.`);
  }
  const html = fs.readFileSync(PAGE, "utf8");
  const context = vm.createContext({});
  // Where each block sits, so the coupling check below can cut ALL of them out
  // of the page before looking for calls. Cutting only one would let a function
  // satisfy the check with its own definition, in the other block.
  const spans = [];
  // Which block defines which name, decided by evaluating each block ALONE.
  // Needed by the same-script check at the bottom: a name has to be traced to
  // the script it is really declared in, not to the first block in the list.
  const defines = [];
  for (const { begin, end } of BLOCKS) {
    const opens = html.split(begin).length - 1;
    const closes = html.split(end).length - 1;
    if (opens !== 1 || closes !== 1) {
      // The marker is the whole coupling between the page and this gate. A gate
      // that silently found nothing to check is the empty result that reads as
      // clean, which this repository has been caught by twice.
      refuse(
        `expected exactly one \`${begin}\` and one \`${end}\` in site/index.html, ` +
          `found ${opens} and ${closes}. The block this gate checks is identified by them; ` +
          `renaming one leaves the gate testing nothing at all.`
      );
    }
    // Both markers sit INSIDE comments, so the slice starts after the opening
    // comment's `*/` and stops before the closing comment's `/*`.
    const from = html.indexOf(begin);
    const to = html.indexOf(end);
    const body = html.slice(from + begin.length, to);
    const source = body.slice(body.indexOf("*/") + 2, body.lastIndexOf("/*"));
    spans.push([from, to + end.length]);
    try {
      vm.runInContext(source, context, { filename: `site/index.html#${begin}` });
    } catch (e) {
      refuse(`the block at \`${begin}\` does not evaluate: ${e}`);
    }
    const alone = vm.createContext({});
    vm.runInContext(source, alone, { filename: `site/index.html#${begin}` });
    defines.push(API.filter((n) => vm.runInContext(`typeof ${n} === "function"`, alone)));
  }
  const api = {};
  for (const name of API) {
    const fn = vm.runInContext(`typeof ${name} === "function" ? ${name} : null`, context);
    if (!fn) refuse(`no lifted block defines ${name}()`);
    api[name] = fn;
  }
  // A DECISION NOTHING CONSULTS IS NOT A DECISION. Everything below this line
  // proves what the block ANSWERS; none of it can see whether the renderer
  // asks. A block that is correct and unused renders exactly the page this
  // phase was written to fix, and every case here would still be green - the
  // "gate that has only ever been seen green" shape, arriving from the one
  // direction the cases cannot look. So each function is required to be called
  // at least once OUTSIDE its own block, in the same built page.
  //
  // This is a coupling check, not a rendering check: it says the answer is
  // asked for, never that it reaches the pixels. What draws a node is not in a
  // liftable block and is not gated here.
  //
  // COMMENTS ARE STRIPPED FIRST, and finding that out cost the break test its
  // first reading: the phase header's own comment says "figuresAreOlder() is
  // that question", so the check passed with every call to it deleted. A
  // coupling check satisfied by PROSE ABOUT the coupling is the instrument
  // this repository keeps catching itself with. The stripper is deliberately
  // crude - block comments, then `//` to end of line unless it is preceded by
  // a colon, which is every URL in this file - and it is allowed to be, because
  // its only failure mode is refusing a page that is fine, loudly.
  //
  // EVERY block is cut out, not just the one a function came from: with two
  // blocks in one context, cutting one leaves the other's definition standing
  // in the text, and `historyTally(` would have been "called" by its own
  // signature.
  //
  // AND THE CALL MUST BE IN THE SAME <script> AS THE BLOCK. This half was added
  // after a defect that was green here and red in check-page-freshness.mjs on
  // another host: historyTally() was defined inside the map's script, which is
  // WRAPPED in an IIFE on purpose, and called from the dashboard's script,
  // which cannot see into it. `historyTally(` was present outside the blocks,
  // so the check above passed - it was reading the call as text, and the call
  // threw ReferenceError on every tick. Nothing else could see it: the block
  // lifts and evaluates perfectly on its own, the cases all pass, and a cold
  // load never goes through the caller. A text gate cannot know about scopes,
  // but it can know that a wrapped script is not a place to put a function
  // somebody else calls.
  const ordered = spans.slice().sort((a, b) => a[0] - b[0]);
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => ({
    from: m.index,
    to: m.index + m[0].length,
  }));
  const scriptOf = (at) => scripts.findIndex((s) => at >= s.from && at < s.to);
  // One script's text with every block cut out of it, comments stripped.
  const callable = scripts.map((s) => {
    let text = "";
    let cut = s.from;
    for (const [from, to] of ordered) {
      if (from < s.from || to > s.to) continue;
      text += html.slice(cut, from);
      cut = to;
    }
    return strip(text + html.slice(cut, s.to));
  });

  for (const name of API) {
    const home = defines.findIndex((names) => names.includes(name));
    const calledIn = callable
      .map((text, i) => (text.indexOf(name + "(") === -1 ? -1 : i))
      .filter((i) => i !== -1);
    if (!calledIn.length) {
      refuse(
        `${name}() is defined in a lifted block and called nowhere outside the blocks.\n` +
          `The page would render exactly as it did before the block existed, and every ` +
          `case in this gate would still pass.`
      );
    }
    if (home === -1) continue; // no block claims it: the check above is all there is
    const homeScript = scriptOf(spans[home][0]);
    if (!calledIn.includes(homeScript)) {
      refuse(
        `${name}() is defined in the block in script #${homeScript + 1} and called only from ` +
          `script #${calledIn.map((i) => i + 1).join(", #")}.\n` +
          `  The two scripts on this page do not share a scope - the map's is wrapped, ` +
          `deliberately - so\n  that call throws ReferenceError at run time and takes its ` +
          `caller's whole render pass with it.\n  Move the function beside its caller.`
      );
    }
  }
  return api;
}

/** Exact and total. `undefined` and a missing key are not the same answer, and
 *  a subset comparison would pass a function that returns nothing at all. */
function same(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

function main() {
  const i = process.argv.indexOf("--case");
  const argCase = i !== -1 ? process.argv[i + 1] : null;
  const api = loadTense();

  if (!fs.existsSync(CASES)) refuse(`${path.relative(ROOT, CASES)} does not exist`);
  let files = fs.readdirSync(CASES).filter((f) => f.endsWith(".json")).sort();
  if (argCase) {
    files = files.filter((f) => f === argCase + ".json");
    if (!files.length) refuse(`no case named ${argCase}`);
  }
  if (!files.length) {
    refuse("no cases found. A gate with nothing to check is not a green gate.");
  }

  let failed = 0;
  let checks = 0;
  for (const file of files) {
    const name = file.replace(/\.json$/, "");
    const doc = JSON.parse(fs.readFileSync(path.join(CASES, file), "utf8"));
    if (!doc.checks || !doc.checks.length) {
      refuse(`${file} declares no checks. An empty case is a green case, which is worse than a red one.`);
    }
    const findings = [];
    for (const c of doc.checks) {
      if (!api[c.fn]) findings.push(`names ${c.fn}(), which the block does not define`);
      else {
        checks++;
        let got;
        try {
          got = api[c.fn].apply(null, c.args);
        } catch (e) {
          findings.push(`${c.fn}() threw: ${e}`);
          continue;
        }
        if (!same(c.expect, got)) {
          findings.push(
            `${c.fn}(${c.args.map((a) => JSON.stringify(a)).join(", ")})\n` +
              `        expected ${JSON.stringify(c.expect)}\n` +
              `        got      ${JSON.stringify(got)}`
          );
        }
      }
    }
    if (findings.length) {
      failed++;
      console.log(`FAIL  ${name}`);
      for (const f of findings) console.log(`      ${f}`);
    } else {
      console.log(`ok    ${name}`);
    }
  }

  if (failed) {
    console.log(`\npage-tense-check: ${failed} of ${files.length} cases disagree with the page`);
    process.exit(1);
  }
  console.log(`\n${files.length} cases, ${checks} calls: the page says when its figures are true`);
}

main();
