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
 * one definition on two hosts. It LIFTS THE BLOCK OUT OF THE BUILT PAGE:
 *
 *     site/index.html
 *       ==== PAGE TENSE - begin ====
 *         figuresAreOlder(observation)
 *         envTense(observation, env)
 *         nodeTense(node, record, envs)
 *       ==== PAGE TENSE - end ====
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

const BEGIN = "==== PAGE TENSE - begin";
const END = "==== PAGE TENSE - end";
const API = ["figuresAreOlder", "envTense", "nodeTense"];

function refuse(why) {
  console.log(`page-tense-check: REFUSED\n${why}`);
  process.exit(1);
}

/** Lift the block out of the built page and evaluate it in its own context. */
function loadTense() {
  if (!fs.existsSync(PAGE)) {
    refuse(`site/index.html does not exist. Build it with \`make site-page\`.`);
  }
  const html = fs.readFileSync(PAGE, "utf8");
  const opens = html.split(BEGIN).length - 1;
  const closes = html.split(END).length - 1;
  if (opens !== 1 || closes !== 1) {
    // The marker is the whole coupling between the page and this gate. A gate
    // that silently found nothing to check is the empty result that reads as
    // clean, which this repository has been caught by twice.
    refuse(
      `expected exactly one begin marker and one end marker in site/index.html, ` +
        `found ${opens} and ${closes}. The block this gate checks is identified by them; ` +
        `renaming one leaves the gate testing nothing at all.`
    );
  }
  // Both markers sit INSIDE comments, so the slice starts after the opening
  // comment's `*/` and stops before the closing comment's `/*`.
  const body = html.slice(html.indexOf(BEGIN) + BEGIN.length, html.indexOf(END));
  const source = body.slice(body.indexOf("*/") + 2, body.lastIndexOf("/*"));
  const context = vm.createContext({});
  try {
    vm.runInContext(source, context, { filename: "site/index.html#page-tense" });
  } catch (e) {
    refuse(`the extracted block does not evaluate: ${e}`);
  }
  const api = {};
  for (const name of API) {
    const fn = vm.runInContext(`typeof ${name} === "function" ? ${name} : null`, context);
    if (!fn) refuse(`the extracted block defines no ${name}()`);
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
  const outside = html.slice(0, html.indexOf(BEGIN)) + html.slice(html.indexOf(END));
  for (const name of API) {
    if (outside.indexOf(name + "(") === -1) {
      refuse(
        `${name}() is defined in the PAGE TENSE block and called nowhere outside it.\n` +
          `The page would render exactly as it did before the block existed, and every ` +
          `case in this gate would still pass.`
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
