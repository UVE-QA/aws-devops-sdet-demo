#!/usr/bin/env node
/**
 * The gate over the page's RUN-LAYER STATE MACHINE (ADR-0043 D3).
 *
 * Everything else the map draws is folded on the runner, in Python, and gated
 * there - node-states-check and results-check exist because a join written
 * twice would be one definition on two hosts. This one cannot move: it reads
 * the GitHub Actions API live, in the visitor's browser, and there is no run to
 * fold afterwards. So instead of copying the logic into Python to test it, this
 * gate LIFTS THE BLOCK OUT OF THE BUILT PAGE and runs that, verbatim.
 *
 *     site/index.html
 *       ==== RUN-LAYER STATE MACHINE - begin ====
 *         useEstate(estate)
 *         phaseNodes(p)
 *         bindingState(observation, bindings)
 *         runLayerStates(observation, phases)
 *       ==== RUN-LAYER STATE MACHINE - end ====
 *
 * Since schema 3 a phase REFERENCES the resource nodes it acts on instead of
 * holding them, and since Phase 24 it does not draw them either: the estate is
 * a contour of its own, answered by observation. The snapshot still carries an
 * `estate` beside its phases and this gate still hands it over with
 * useEstate() - not to resolve anything now, but because knowing which ids are
 * NOUNS is what makes claim 4 checkable.
 *
 * What it defends, in the three sentences 20c wrote down while watching a live
 * cycle and could not check afterwards:
 *
 *   1. A node with no step of its own is NEVER reported as running on its own
 *      behalf. It inherits its phase and is marked `via: "phase"`, because
 *      Terraform creates one resource at a time and the page cannot know which.
 *   2. A phase whose steps are over in a run that is still going is `finished`,
 *      which is not the same thing as never having run. Its figures publish at
 *      the end of the cycle, and until then the page has to say so.
 *   3. A suite node answers for ITS OWN step. suite.db.stage is drawn in the
 *      quality gate and its report comes out of a step in Provision, so a suite
 *      that inherited its phase lit in the wrong minute - and prod, whose gate
 *      does bind its db step, disagreed with stage about the same suite.
 *   4. AN ESTATE NODE NEVER REACHES THE RUN LAYER (Phase 24, ADR-0054 D3).
 *      Claim 1 was the best available answer while a resource was a child of
 *      the phase that made it; it is not an answer at all for `prod.rds`, which
 *      four verbs touch and which stood at full colour with the previous
 *      cycle's figures for twelve measured minutes while prod was being
 *      deleted, because the destroy phase could not reach it. A noun is
 *      answered by observation now. This one is checked against EVERY case, not
 *      against a case written for it.
 *
 * The phases it folds are a FROZEN snapshot in tests/fixtures/live-state/, not
 * site/data/topology.json, for the reason check-results.py freezes its
 * inventory: this gate is about the state machine. If it read the live map,
 * adding a node would redden it, and the person who added the node would learn
 * that the fixture is stale - which is how a gate teaches people to ignore it.
 *
 *     scripts/check-live-state.mjs                     # every case
 *     scripts/check-live-state.mjs --case apply-running
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
const FX = path.join(ROOT, "tests", "fixtures", "live-state");
const CASES = path.join(FX, "cases");

const BEGIN = "==== RUN-LAYER STATE MACHINE - begin";
const END = "==== RUN-LAYER STATE MACHINE - end";

function refuse(why) {
  console.log(`live-state-check: REFUSED\n${why}`);
  process.exit(1);
}

/** Lift the block out of the built page and evaluate it in its own context. */
function loadStateMachine() {
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
  // comment's `*/` and stops before the closing comment's `/*`. Getting either
  // end wrong hands `vm` an unterminated comment, which is a loud failure -
  // deliberately not a quiet one that trims a function off the end.
  const body = html.slice(html.indexOf(BEGIN) + BEGIN.length, html.indexOf(END));
  const source = body.slice(body.indexOf("*/") + 2, body.lastIndexOf("/*"));
  const context = vm.createContext({});
  const EXPORTS = "({ bindingState, runLayerStates, useEstate, phaseNodes })";
  try {
    vm.runInContext(source + "\n;" + EXPORTS, context, {
      filename: "site/index.html#run-layer",
    });
  } catch (e) {
    refuse(`the extracted block does not evaluate: ${e}`);
  }
  const api = vm.runInContext(EXPORTS, context);
  for (const name of ["bindingState", "runLayerStates", "useEstate", "phaseNodes"]) {
    if (typeof api[name] !== "function") refuse(`the extracted block defines no ${name}`);
  }
  return api;
}

function readJSON(p) {
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

/** Exact, both directions. A subset check would pass a machine that reports
 *  nothing at all, which is the failure mode with the most ways in. */
function compare(expected, got) {
  const findings = [];
  for (const kind of ["phases", "nodes"]) {
    const want = expected[kind] || {};
    const have = got[kind] || {};
    for (const id of Object.keys(want)) {
      if (!(id in have)) {
        findings.push(`${kind}.${id}: expected ${JSON.stringify(want[id])}, the machine reported nothing`);
        continue;
      }
      const a = JSON.stringify(want[id], Object.keys(want[id]).sort());
      const b = JSON.stringify(have[id], Object.keys(want[id]).sort());
      if (a !== b) findings.push(`${kind}.${id}: expected ${a}, got ${JSON.stringify(have[id])}`);
    }
    for (const id of Object.keys(have)) {
      if (!(id in want)) {
        findings.push(`${kind}.${id}: the machine reported ${JSON.stringify(have[id])}, the case expects nothing`);
      }
    }
  }
  return findings;
}

function main() {
  const argCase = process.argv.indexOf("--case") !== -1 ? process.argv[process.argv.indexOf("--case") + 1] : null;
  const { runLayerStates, useEstate } = loadStateMachine();

  const phasesFile = path.join(FX, "phases.json");
  if (!fs.existsSync(phasesFile)) refuse(`${path.relative(ROOT, phasesFile)} does not exist`);
  const snapshot = readJSON(phasesFile);
  const phases = snapshot.phases;
  // THE ESTATE IS WHAT CLAIM 4 IS MEASURED AGAINST. Without it this gate cannot
  // tell a NOUN from a step, so its strongest claim would quietly become
  // unverifiable - the empty result that reads as clean, which this repository
  // has been caught by twice. A refusal, not a quiet zero. Regenerate it with
  // tests/fixtures/live-state/refresh.py.
  if (!snapshot.estate) {
    refuse(
      `${path.relative(ROOT, phasesFile)} carries no \`estate\`. This gate needs it to know ` +
        `which ids are NOUNS: since Phase 24 the run layer may not report on one at all ` +
        `(ADR-0054 D3), and without the estate that claim cannot be checked.`
    );
  }
  useEstate(snapshot.estate);
  // Claim 4, and the reason phaseNodes() got smaller: AN ESTATE NODE NEVER
  // APPEARS IN THE RUN LAYER AT ALL. It is checked against every case rather
  // than against the one case somebody remembered to write, because the defect
  // it replaces - prod.rds at full colour for twelve measured minutes while
  // prod was being deleted - arrived through a phase nobody was looking at.
  const ESTATE_IDS = new Set([
    ...snapshot.estate.environments.flatMap((e) => (e.nodes || []).map((n) => n.id)),
    ...(snapshot.estate.permanent || []).map((n) => n.id),
  ]);
  if (!ESTATE_IDS.size) {
    refuse(
      `${path.relative(ROOT, phasesFile)} carries an \`estate\` holding no nodes, so the ` +
        `claim that none of them reaches the run layer would hold vacuously everywhere.`
    );
  }

  if (!fs.existsSync(CASES)) refuse(`${path.relative(ROOT, CASES)} does not exist`);
  let dirs = fs.readdirSync(CASES).filter((d) => fs.statSync(path.join(CASES, d)).isDirectory()).sort();
  if (argCase) {
    dirs = dirs.filter((d) => d === argCase);
    if (!dirs.length) refuse(`no case named ${argCase}`);
  }
  if (!dirs.length) {
    refuse("no cases found. A gate with nothing to check is not a green gate.");
  }

  let failed = 0;
  for (const name of dirs) {
    const dir = path.join(CASES, name);
    const observation = readJSON(path.join(dir, "observation.json"));
    const expected = readJSON(path.join(dir, "expected.json"));
    let got;
    try {
      got = runLayerStates(observation, phases);
    } catch (e) {
      console.log(`FAIL  ${name}\n      the machine threw: ${e}`);
      failed++;
      continue;
    }
    const findings = compare(expected, got);
    for (const id of Object.keys(got.nodes || {})) {
      if (ESTATE_IDS.has(id)) {
        findings.push(
          `nodes.${id}: an ESTATE node reached the run layer (${JSON.stringify(got.nodes[id])}). ` +
            `A noun is answered by observation and by nothing else (ADR-0054 D3); ` +
            `phaseNodes() must return a phase's own steps only.`
        );
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
    console.log(`\nlive-state-check: ${failed} of ${dirs.length} cases disagree with the page`);
    process.exit(1);
  }
  console.log(`\n${dirs.length}/${dirs.length} observations fold as the page says they do`);
}

main();
