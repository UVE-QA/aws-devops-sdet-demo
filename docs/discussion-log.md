# Discussion Log — Decisions & Rationale

Compact record of the design decisions made while preparing this project,
kept so the context is not lost and does not need re-deriving. Summary only —
not a transcript. New decisions go to `docs/decisions/` as ADRs.

## Current state (update at every phase gate)

**As of 2026-08-09 (20e.1 — the composition on the real page).** ADR-0047 D1-D6
and ADR-0048 implemented; ADR-0049 records what building it decided.

**The first screen is the dashboard now, not an introduction to one.** Four
blocks: identity with the links — the repository link was at 100% of scroll
depth — environments one line each with the Launch button as that panel's
footer, the request path with the TOOL on every hop, and the run in flight
collapsed to three lines with the whole list one disclosure away. In a run that
is over the window is the FAILING step, never the last one: collapsing a failed
run to its final line shows a green tick where the thing broke. Below them the
map, and below that a fold and five cuts, each answering its own question in its
own header.

**The map is one grid, and its column count is computed.** The serpentine was
exact and it was a stretch of road. `layout.columns` comes out of the generator
— eight phases, two of them six nodes or more, ten columns today — and the page
decides only how many fit. It folds into whole ROWS, because taking the fitted
count directly gave nine of ten at 1920 and left phase 8 alone on a second row
with a screen of air beside it: the exact picture ADR-0047 D5 was written after,
rebuilt by the code meant to end it.

**Measured with the same fixtures either side**, four viewports, cuts closed and
open: 4781px → 1935px at 1920x1080, 4.4 screens → 1.8, and 1.3 at 2560x1440,
which is the stated primary target. The sketch's 1.1 screens was measured with
placeholder figures and no launch control on the page; those are the honest
halves of the environments panel and they cost about 400px.

**The break test that matters is BREAK 5**, and it is not about contrast. The
sketch drew the `working` edge as `repeating-linear-gradient`, which is the
natural way to say "dashed" in the same channel as the colour — and an element
painted with a gradient resolves `background-color` to `transparent`, which is
what the gate reads. It measures 1.00:1 in both themes and refuses. Copying the
sketch verbatim would have shipped a state that was on the page and off the
instrument. The general rule is now ADR-0049 D4: a channel that carries state
has to be one the gate can read, or it is decoration.

Two refusals were added and both were exercised: a request-path hop citing a
node the map does not draw, and the panel's editorial input deleted. The panel
that says where a request goes cannot outlive the infrastructure it draws.

Found on the way: `docs/demo-script.md` said "thirty-nine ADRs" and there are
fifty — a count in prose, in the document that is read aloud at an interview.
Replaced with no number; the page counts them.

**As of 2026-08-09 (20e.1 — the floor is met before the layout).** Three
decisions and a gate; the composition itself is not started. **ADR-0048.**

**The three that blocked space, decided before a line of layout.** The Launch
button becomes the Environments panel's footer: it acts on what that panel
observes, and its refusals — one at a time, a daily quota — are statements about
environment state, so the refusal and its reason are finally in the same box. Not
the identity bar, which is navigation and no place for a control that spends
money, and not the current-cycle panel, whose content varies. The legend becomes
a cut in the map's header, because D6 put a word on every node and a legend is no
longer a decoder — and explicitly, the sketch's `State encoding` strip does NOT
go on the page: it is evidence for a decision, not an element of a dashboard. A
node's figures live on one state line, `<word> · <figure>`, word first, with no
separator printed when there is no figure.

**The gate needed a browser, and that is not a preference.** `make
contrast-check` lifts the `<style>` blocks out of the BUILT page — the move
`check-live-state.mjs` already makes on the same file — and measures them in
chromium, because the engine is what resolves `color-mix()` and the one contrast
measurement this project has taken was wrong in a colour parser. A control runs
first on every invocation: black on white must read 21.00 through both
notations, and a control that is off refuses without a verdict rather than
printing a table under a broken instrument.

**It reproduced ADR-0047's table to the hundredth on five of six states**, in
both themes, written from scratch and sharing no code with the discovery's
throwaway script. The sixth is a finding: `absent` reads 1.15 / 1.12 against
1.34 / 1.35, and the older figure is not a different model but an unreachable
one — `#d8dbe2` against pure white is 1.27, so no background yields 1.34.
Superseded, with nothing following from it.

**The palette moved first, on the current page.** working 2.67→3.22, done
2.41→3.37, suite 1.98→3.38 in the light theme, at the smallest 5% step that
clears the floor with a margin in both. Every boundary is now a token in
`:root`, so `.node.done` and `.phase.done` share one definition instead of two
matching literals. The fix landed in its own commit before the gate: a gate
arriving red on a shared dependency reddens every open pull request over
findings none of them introduced, which the image scan already did once.

Broken seven ways, green control either side. The one that matters is not about
contrast — the discovery's own parser defect replanted verbatim, caught by the
control at 1.01 before a single state printed. The one the gate exists for is
`--ok` lightened with no state colour edited, `done` falling from 3.37 to 1.68.

ADR-0047 D5's computed span total was deferred rather than done: it is
computable today, nothing would read it, and a number nothing reads has never
been exercised.

**As of 2026-08-09 (20e.0 — the dashboard is composed, not scrolled).** The
discovery step ran and renamed its own phase. **ADR-0047.**

**"Navigable" was the wrong target, and it was the previous session's own word.**
A section index makes a long strip traversable; it does not make it stop being a
long strip. Asked directly, the requirement is a DASHBOARD rather than a long
list of resources — where things are, how they connect, which tools are used, in
what order, composed in blocks, with the detail under cuts. The desktop monitor
is the primary target and the phone is last in the queue, both stated rather than
inferred.

The complaint was measured instead of quoted, at four viewports and with three
remote sources unreachable, so every figure understates the live page: 3.6
screens at 1920x1080, 10.5 at 390x844, and **0 in-page anchors, 0 `<nav>`, 0
sticky elements** — the page has no navigation affordance at all, which makes the
complaint literal rather than figurative. The per-cycle map is 46% of the page on
a laptop, and the repository link — the one thing a thirty-second visitor needs —
sits in the footer at 100% of scroll depth.

**Then a channel nobody had measured.** Five of the map's six states ride a 1px
border and nothing else, and three are under WCAG 1.4.11's 3:1 floor in the light
theme: working 2.67, done 2.41, suite 1.98. Solid versus dashed at one pixel is
not a channel, which is exactly what had been reported by eye. The pulse does not
rescue the state that has it — a 1px ring fading to `opacity: 0`, fainter than
the border it sits on for most of every beat.

**The first contrast measurement was wrong and looked like a finding.**
`color-mix()` resolves to `color(srgb 0.44 0.62 0.90)`, the parser divided those
by 255, and six different colours came back at 20.92:1 in light and 1.23:1 in
dark. Both readings are indistinguishable from real ones. What settled it was a
control inside the measurement — black on white must read 21:1, through both
notations — and it is printed on every run now. The pipe lesson in a new
instrument: there the shell stood between the defect and the reading, here the
colour parser did.

The tools turned out to be missing rather than their icons: Terraform, Docker,
Playwright, pytest and Alembic appear nowhere on the map, and `TEST` does not
distinguish Playwright from pytest. Named in text, with vendor marks left as
separate work exactly as `assets/github-logo/NOTICE.md` already did for GitHub's.

The sketch is 1.1 screens at 1920x1080 and 1.0 at 2560x1440, with 0 boxes
overflowing their own parent at any viewport — measured per-parent rather than
against the document, which is 20a's lesson and which immediately caught a table
74px past its container that the document measure could not have seen. `auto-fit`
left phase 8 alone on a second row with a screen of air beside it, so the column
count is deterministic and its span total must be COMPUTED rather than written
down. Collapse follows GitHub Actions: the header answers whether anything is
wrong and names the FAILING step, the lines inside carry per-step status — the
first version collapsed to "the current step", which for a finished run is the
last one, a green tick where the thing broke.

Six things are open and named rather than dropped, the contrast gate among them.
Nothing was applied, no AWS call was made, and `site/` and `assets/` were not
touched.

**As of 2026-08-08 (20f — the teardown prices the cycle it just ended).** The
computation ADR-0045 built by hand now runs where a lifetime actually closes.
**ADR-0046.**

**The session opened by finding that the plan described a decision nobody had
taken.** 20e's line about moving the per-node prose into hover was a spontaneous
example, written into `docs/next-phases.md` with a costed collision worked out
beneath it — in the one document a session reads to learn what to do next. The
usual stale document says something that WAS true; this one said something that
never was, and the analysis underneath made it read as more considered rather
than less. 20e is restated around the requirement as it was actually given: the
dashboard is a long strip you cannot navigate, which is wayfinding rather than
density, and the phase now opens with a discovery step of its own and runs after
the wiring.

The pairing rule is what ADR-0045 said had to exist first, and its fourth clause
is deliberately weak: ADR-0038 adopts orphans before a teardown, so only a pair
with NOTHING in common is refused. `orphan_deletes` was already computed and
nothing refused on it — the detector existed at the wrong threshold, wired to
nothing. The anchor rides an existing rule rather than a new one, and is read
over anonymous HTTPS because the object is public and the cheapest new path is
the one that is not new.

**The break test broke, and the instrument was the defect.** Four different
one-clause breaks each reddened the same fixture; the identical loop then
reported all four green. CPython validates a `.pyc` on (mtime in whole seconds,
source size), every break left `fold-cost.py` at exactly 18911 bytes, and the
loop ran inside a second. Measuring the five variants settled in seconds what
reasoning had not. Five gates load a script under test through `importlib`; all
five now write no cache. The re-run then found a clause that had never been
tested at all.

`make publish-prefixes-check` went red unprompted on `cost/`, the first prefix
added since ADR-0044, and named the remedy — the deletion of 2026-08-08
prevented rather than repeated, by a gate catching something it was not shown in
advance. End to end on the real cycle: $0.018339 .. $0.023797, which is what 20d
computed by hand. No cycle was ordered; the next teardown is the first live
exercise.

**As of 2026-08-08 (20d — cost is a lifetime, not a creation).** A cycle's cost is
computed by a command from the cycle's own timelines and a captured rate table,
instead of being worked out by hand in a session and written into a document.
**ADR-0045.**

**The obvious design was killed by reading the cycle before writing the fold.**
Every timeline carries `elapsed_seconds` per resource and it is the natural thing
to multiply by a rate — and it is how long TERRAFORM took to create the resource,
while the meter runs for as long as the resource EXISTS. The load balancer of
2026-08-08 was created in 173 seconds and then stood for 1582 more. An estimate on
the creation figures would have reported a ninth of its cost and looked entirely
reasonable doing it.

The same read produced the second decision: the estimate is a BAND, not a figure.
Terraform reports when it started and finished creating a thing; AWS starts
charging somewhere in between and the stream cannot see where. For RDS the two
ends are 852 and 1381 seconds — 62% apart, which a single number with two decimal
places would have hidden.

Three inputs, three homes, none holding two kinds of thing: prices CAPTURED from
the Price List API with their SKUs and filters, the shape DERIVED from `infra/`
and recorded nowhere so nothing can go stale, the judgement about what is worth
metering EDITORIAL and saying so. `make rates-check` reads the kinds out of the
configuration — a NAT gateway added to the network module reddens a gate instead
of costing money invisibly — and the fold refuses from the other side for a kind
it observes and cannot price. On the real cycle: 0 UNPRICED across 32 resources.

**The cycle came out at $0.0183 .. $0.0238, and five sixths of it accrued outside
every phase.** The plan asked for cost per phase, which is not a property a
lifetime has. Overlap attribution is what is well defined, and the first thing it
says is that the phases are not where the money is: $0.0029 during the apply,
$0.0154 while the environment was simply up.

Thirteen break tests, green controls either side. One did not test what it was
aimed at — a forced `closed = True` crashed the fold instead of producing a
plausible wrong answer, and had to be re-aimed at `state` alone. One gap the log
names rather than hides: every coverage refusal but the last was measured while
the rate table was still missing, so each carried two findings, and the green
control after the capture is the only clean one in the file.

ADR-0039 D3 is amended in four clauses and its promised reconciliation against a
real bill is RETIRED (ADR-0045 D6), not deferred. A promise the project has
decided not to keep is worse than one it never made.

**As of 2026-08-08 (Ops, the site sync deleted the results).** Twenty minutes
after 20c closed, its own validation command returned 403.
`scripts/publish-site.sh` syncs `site/` with `--delete` and excluded three
prefixes; ADR-0042 had added a fourth thing the lifecycle writes - `results/` -
hours earlier, and nothing added the line. **ADR-0044.**

It stayed harmless because the two scripts only meet on a push to `main` that
touches `site/`, and the push that finally did was 20c's own page release: the
commit teaching the map to read those results is the commit that deleted them.
The bucket has no versioning, so cycle 31276975666's folded results are gone.
The timeline, the node states and every Playwright report survive, being under
excluded prefixes - so the map's Terraform half is intact and its suite half is
empty until a cycle runs, which is expected rather than a defect in the page.

**It was established by a control that differs in one variable**, after a 403, an
empty listing and a silent `gh run view --log` had each decided nothing on its
own: `timeline/` and `results/` are written by the same script in the same run,
minutes apart, and one is excluded and present while the other is not excluded
and empty. Fixed in one line, and the rule - which had been a comment predicting
its own breach - is now `make publish-prefixes-check`.

Two documented traps were walked into while break-testing it, both in the
primer, both read that morning: a `git checkout --` restored a deliberate break
and discarded the still-uncommitted fix, and the `--delete` guard was a substring
test that the file's own comment made impossible to fire.

**As of 2026-08-08 (20c CLOSED, a node answers for its own step).** The page
reads the two files the previous session filled and never opened, so 180
collected tests and a real cycle's verdicts stop being true and invisible. The
three findings from watching that cycle turned out to be one structural mistake:
**liveness was attached to the box a node is drawn in, and a box is a layout
decision.** **ADR-0043.**

A suite node now carries its own `live` binding, checked against the workflow by
the same code that checks a phase's — four refusals at build time. A node with no
binding inherits its phase and is MARKED as having inherited, so seven nodes stop
claiming to be running while Terraform creates one. A phase whose steps are over
in a run still going says so, instead of showing the sentence a phase that has
NEVER run shows. And stage and prod stop disagreeing about `db`: prod's gate
phase happened to bind its db step and stage's did not, which is why one suite
behaved differently in two environments with nothing looking wrong in either.

The state machine is the one fold that cannot move to Python — it reads the
Actions API in the visitor's browser, and there is no run afterwards to fold — so
the gate lifts the marked block OUT OF THE BUILT PAGE and runs it verbatim
against twelve recorded observations. Ten break tests, all three findings put
back among them; the sharpest line in the log is `suite.db.stage` reported as
nothing while its step ran. A fourth defect surfaced writing the gate rather than
watching the cycle: the phase clock restarted at every bound step, so a
four-minute apply read as ten seconds old — and the comment sitting above that
code had been describing the correct behaviour all along.

$0, no AWS call, verified offline against fixtures and a headless render. Next is
20d, unblocked, with 20c's cycle as the first bill to reconcile against.

**As of 2026-08-08 (20c, the suites answer for themselves).** The map's suite
nodes stop being described and start being asked: an inventory COLLECTED by the
tools that run the suites, and a fold from the reporters' own output onto the
nodes. **ADR-0042.** 180 tests across five suites, byte-identical on three hosts;
the db suite was GIVEN a collector rather than a description, and the two copies
of its assertion - the local gate and the one baked into the image, which is what
AWS runs - can no longer drift silently.

Then the cycle, which is the half nothing offline can stand in for. Apply
`31276975666` lit the apply half 20b.2 never reached: `nodes-apply.json` had
never existed, and the map now carries real per-group durations and identifiers.
Real results reached the suite nodes - api 52, regression 12, smoke 2 - and
**db came back `incomplete, 1 passed, 1 not_run` for a suite that had passed
both checks.** A race was assumed, a fix for it was written before the log was
read, and one `grep` refuted it: `aws logs get-log-events --output text` joins an
array with TABS, so three events arrived as one line. Fixed at the capture; the
real bytes are a fixture, and what that fixture pins is that the fold NAMED the
gap instead of filling it in.

Teardown confirmed against the AWS CLI under a live credential, not against
Terraform state and not against the green run: the account is empty. Next is the
page - it reads neither the inventory nor the results, so all of the above is
true and invisible - carrying three findings that came from WATCHING the cycle:
a running phase pulses every node while terraform creates one, a finished phase
falls back to "nothing recorded yet" until the run publishes at the end, and
`suite.db.stage` is drawn in a phase where its step does not run.

**As of 2026-08-08 (Ops, the gate that sees a free leftover).** The teardown can
see a leftover that costs nothing, and the two IAM roles that blocked every
`deploy-stage` for three days are gone. **ADR-0041.** The account is empty and a
cycle of any kind is unblocked; next is 20c, which can finally light the apply
half 20b.2 never reached.

The finding is not that a check was wrong. `scripts/sweep-orphans.sh` reported
`verdict: clean, exit 0` against the live account with both roles alive, and
every part of it behaved as designed: the teardown's own gate asks whether any
BILLABLE resource remains and a role is free; a partial teardown had dropped the
roles out of state; and the tagging API does not index `iam:role`, so the sweep's
fail-closed confirmation — which would have gone red — was never handed one.
Three gates, all green, all honest, and the environment was not empty.

**The wrong-region explanation died to a control inside the same answer**, which
is the methodological point of the session. `get-resources` in us-east-1 does
answer and does return IAM: it hands back the
`token.actions.githubusercontent.com` OIDC provider, and no role at all, though
the two permanent `github-deploy` roles carry the same tags in the same state
level and were asked for in the same call. Only the resource type differs. A
second query built as its own control would have produced an empty result to
interpret, and this project has a standing record of where that goes.

So discovery inverts. For kinds nothing indexes, the names come from the
CONFIGURATION — a collision can only happen on a name the configuration will
create — and `adopt_orphans.RULES` already listed them. The prefix scan that was
designed first, and approved, turned out to be unrunnable: the deploy role has
`iam:GetRole` on exactly two ARNs and neither `iam:ListRoles` nor
`iam:ListRoleTags`, so scanning needed a new account-wide grant applied to a
PERMANENT state level in order to build a gate. Reading the policy before writing
the code is what caught it.

**The session then put a defect into its own patch.** Adopting the orphan role
alone would have been worse than adopting nothing: `DeleteRole` refuses while a
policy is attached, so the import hands `terraform destroy` a `DeleteConflict` —
red, still leaking, launch lock kept, public button shut. It was caught by asking
AWS what was attached BEFORE removing anything, and the answer was that the
teardown had leaked four objects rather than two. The usual shape hides this
entirely: when an apply COMPLETED the policies sit in state beside the role and
`destroy` removes them first, so importing the role alone is correct — it is
wrong in exactly the shape that orphans a role, which is the shape that recurs.
Patch 1 stayed unpushed until patch 2 mapped the dependents.

The break test was never planted. The same command said `clean, exit 0` at 17:50
and `orphans, exit 1` at 19:20 in the same account with only the code changed;
both halves are in the session log. Then `destroy.yml` adopted 4 of 4 and every
step went green — which is the shape that has fooled this project before, so the
verdict came from `aws iam get-role`: gone, gone.

Two smaller things, both this session's own: CI went red on `site-data-check`
because the map publishes the ADR count and 41 stopped being true, and the gate's
message sent the reader to `infra/` and `tests/` while the drift was in
`docs/decisions/`. And one measurement measured the wrong thing — `gh run list
-L 1` returned the `publish-site` run, so a green `ci exit: 0` was about a
different workflow. Same family as the layout check that measured the document
instead of the box.

Chat session links are no longer published (`.claude/settings.json`,
`attribution.sessionUrl: false`). The six already in history stay: the URL
resolves only for the account that owns the session, so it is not a credential,
and rewriting them would change 32 SHAs and falsify a line in a recorded
break-test log. The setting is UNPROVEN until a Claude Code session on the devbox
commits something.

**As of 2026-08-08 (20b.1, the stream and the fold).** Terraform's own `-json`
event stream is captured in all eight apply and destroy invocations across the
four AWS workflows, folded into `timeline/<env>/<run id>-<job>.json` and back
into a legible per-resource log, and gated by `make timeline-check` in `ci.yml`.
Nothing was applied, no AWS API was called, and nothing on the page draws it:
20b was split so that everything decidable without a cycle could be settled at
$0, the way 19 was split.

The claim under gate is one sentence — a run that dies mid-apply must not be
reported as a cycle that happened — and three signals decide it, the weakest
winning: the `.rc` written after terraform returns, the exit code, and the
terminal `change_summary`. The third signal is why a `.cmd` file exists, and
that came from the streams rather than from the documentation: **an apply killed
before it finishes emits a `change_summary` whose operation is `"plan"`**, so a
fold reading only the stream would report a half-finished apply as a plan.

The fixtures are real terraform runs and `apply-killed` was really killed — a
sleeping resource and a `kill -9`, not a truncated file. `apply-complete-no-rc`
was added because `apply-killed` turned out to be over-determined: three signals
are missing there at once, so removing any single rule leaves it correctly
incomplete and the case cannot show which rule works. With the isolated case,
break test 4 said something better than it was aimed at — removing the
missing-`.rc` rule made that case `errored` rather than green, because the next
rule down catches `None` too.

Two things the plan did not have, both silent if missed: the published key needs
the JOB as well as the run id, because self-service launches an environment and
destroys it again inside ONE run and the second timeline would have overwritten
the first; and `publish-site.sh` syncs with `--delete`, so without a third
`--exclude` the next push to `main` would have deleted every published timeline
while the map kept working from the one published minutes earlier. Seven break
tests red, both controls green, tree committed first.

The fixtures were AUTHORED against OpenTofu 1.10.6, the only binary the chat
session could reach, and that caveat is discharged: regenerated on the devbox
with terraform 1.15.8, all six expectations held with no edit. The evidence is
not the identical event counts — those would look the same if nothing had been
regenerated — but `"terraform":"1.15.8"`, `@module: terraform.ui`, `ui: 1.3`
where the fork wrote `tofu` and `ui: 1.2`. The fold survived a gap larger than
any version bump. Recorded rather than fixed: the devbox runs 1.15.8 while the
workflows pin 1.15.5.

**As of 2026-08-08 (20a CLOSED, the map on the page).** The front page renders
the map. The hand-written "What happens, in the order it happens" section — the
one telling every visitor there were five permanent state levels while standing
on the sixth — is gone, and in its place `site/index.html` draws
`site/data/topology.json`: the band above the cycle, the permanent levels, the
serpentine of phases, the cut that names every resource block, and the counts.
Nothing there is maintained beside `infra/` any more.

The page is a BUILD OUTPUT now, which the plan did not have. The map needs the
icon sprite inline, so `assets/index.template.html` is the source and `make
site-page` builds it. That buys a new way to be wrong — a committed output
invites being edited in place, and the edit lives exactly until the next build
silently reverts it — so `make site-page-check` requires the committed page to
be byte-identical to a fresh build, and runs in `ci.yml`. Six ways to make it
red were exercised, five red and both controls green, exit codes to a file with
the tree committed first. The pilot page, its template and its target are gone;
`publish-site` syncs with `--delete`, so the published copy went with the commit.

Two layout defects, and what is worth carrying is not either one but how they
hid: the pilot's `scrollWidth == clientWidth` was green at all four viewports
and was measuring the DOCUMENT. A box that overflows its own parent never
reaches it. The serpentine packer charged one gap per join where a row renders
`phase | gap | arrow | gap | phase`, and at 1180 the first row was 1132px inside
a 1125px box; `.node .head` was up to 22px wider than its node. Both were found
by measuring a box against ITS OWN container.

Closed with two fixes to the session machinery that this day earned twice:
`make session-close` printed the wrong summary whenever a day held more than one
— `ls | tail -1` sorts alphabetically, and 2026-08-08 held four — and the same
assumption appeared a second time in the same script, where it also counted
`*.log` evidence as sessions. That one landed on the right file by accident on
the tree it was measured against, and returned the LOG as soon as this session
added one: the accident was one commit deep. Both orderings now come from INDEX's last row, which
this script already refuses to let go non-chronological: one ordering, not two.
And the primer's WORKING chat name was taken from the phase title in the cursor,
which does not change while a sub-phase spans sessions — 20a took three and all
three would have opened under one name. It comes from the cursor's NEXT ALLOWED
STEP now, the line that differs, and which exists because the previous session
wrote it.

**As of 2026-08-08 (20a, the generator and the drift gate).** The fixture is
gone: `site/data/topology.json` is generated from `infra/` and `tests/` by
`scripts/generate-topology.py`, and `make site-data-check` runs in `ci.yml`. It
is a COVERAGE gate — every resource block under `infra/` belongs to exactly one
display group, including the group meaning deliberately not shown — plus a drift
check that the committed file is byte-identical to a fresh generation. Five ways
to make it red were exercised, exit codes written to a file, the tree committed
first.

It refused on its FIRST run against unmodified `infra/`, and was right: nine
resource blocks carry `count` or `for_each`, and the hand-built fixture had
counted each as one, so "116 resources" was never the number of things AWS
creates. The repair is a change of unit rather than a better guess — every count
says resource BLOCKS, the nine are acknowledged by name with reasons, and a tenth
arriving without an entry is red. Then the same check reported two blocks that do
not repeat, because it matched `for_each` four spaces inside a `dynamic` block:
Phase 19g's finding, in a different file, in a session that had read it that
morning. Indentation is a claim about formatting; the question is about depth.

Nothing observed is written by the generator — no duration, cost, identifier or
result — so the map renders entirely unobserved until 20b and 20c. That is a
visible regression in the exhibit and the honest one.

Two things were added on review. The map had no devbox and no GitHub, because
neither is in `infra/` and the map is generated from `infra/`; they are not
phases either, since nothing creates or destroys them, so they became a band
ABOVE the cycle — and the GitHub card's claim about the trust path is tied to
`aws_iam_openid_connect_provider.github` through a `backed_by` field, so deleting
the provider turns the card red rather than leaving it lying. Lightsail's icon was then
added from the same package release and the same `48` set as the others, so it
shares their viewBox — the `64` set was taken first and would have been a
different visual weight. GitHub keeps a glyph, and for a different reason: its
brand page NAMES this case and permits it, where AWS's pages neither permit nor
exclude a public page, but the mark may not be redrawn, so the asset has to be
downloaded. Adding that one icon made four written numbers false at once —
"seventeen" three times and "~48 KB" once, one of them inside the very file that
explains why the icons are safe to use. Sixth time in two days that the stale
thing was a number. And the
front page's prose was asked to survive under a cut — it does, GENERATED from the
same file, because keeping it as prose would have preserved the exact class of
defect this phase exists to end. The generator now emits every resource's
terraform address, so the cut names all 116 blocks the map folds into 26 marks.

Looking at it again found three things, and the third is older than the session:
a terraform address is one unbroken token and pushed the phone 103px past its
viewport with the cut OPEN, while the same page with the cut SHUT fitted and said
nothing; opening the cut summoned a scrollbar and the map had been laid out
against the wider viewport; and `.node .head` is up to 22px wider than its own
node at every width, on the pre-patch build too. The pilot's
`scrollWidth == clientWidth` was true — of the DOCUMENT. The head spills into the
node's own padding, where neither a screenshot nor that measure could see it.
Left unfixed on purpose: layout here is decided by looking, not by reasoning. Rendering it revealed a
defect no check here could have named: a node with no `state` took the absent CSS
class and the MEASURED body, printing `undefineds` where the seconds go. Nothing
in the JSON was wrong. `site/index.html` was deliberately not touched, by
agreement at the start of the session, so 20a stays open on that half. $0.

**As of 2026-08-08 (20a, the layout pilot).** Half of 20a is done: the layout,
built in a sandbox and LOOKED AT rather than reasoned about, because it is the
only part of Phase 20 that cannot be derived from the repository. The finding is
that a picture makes claims like a sentence does — folding the chain node by node
drew VPC → Secrets Manager → RDS → ALB as a sequence, and Terraform creates those
from a graph. ADR-0026's rule, written about JSON documents, reaches diagrams
unchanged. Sequence moved up a level: the PHASE carries order, the nodes inside
it are a set with no arrows, phases fold serpentine, and the phone falls out of
the same code at one column. Desktop and laptop are declared the intended view in
the page itself rather than engineered around.

ADR-0039 forbade guessing about the AWS Architecture Icons, so three of AWS's own
pages were read: the answer is that none of them names a public web page, in
either direction. What was taken is a decision in the absence of a "no", not a
permission, and `assets/aws-icons/NOTICE.md` keeps those two apart. Seventeen
unmodified icons in one inline sprite; a test suite, a human approval and a
teardown keep project glyphs, because they are not AWS services.

Two tools were wrong and both were caught by measuring twice: a raw headless
`--window-size=390` screenshot showed a clipped phone layout that does not exist,
and `make docs-check` reddened on this session's own cursor entry for naming a
target 20a has not built yet. The fixture is where the schema came from, on
purpose — the layout decided what `topology.json` must carry, so the generator
inherits a contract instead of inventing a shape. Still to build in 20a: the
generator, the drift gate and its break tests, and folding the map into
`site/index.html`, which was deliberately untouched. $0.

**As of 2026-08-08 (earlier, Phase 20.0).** Phase 20.0 is closed: the project
has a cursor forward again, and it points at making the cycle visible without a
log. The session that decided it found its own subject first — FIVE
reader-facing places described the applied, publicly-pressed, closed
`infra/self-service` as written and never applied, including the live dashboard,
which told every visitor there were five permanent state levels while standing on
the sixth. README contradicted itself inside one file. A sixth fell out on the
way past: architecture's "seven state levels" heading, correct while there were
five permanent ones and never revisited.

No gate could have seen any of it. `make docs-check` verifies that every path,
target, route and workflow a document NAMES exists; nothing checks that what a
document CLAIMS is true, and two of the five files are not even in its document
list. Third arrival of the species in three days, and the largest: 19g found two
documents disagreeing with the control store, this found five disagreeing with
the account, in the files an outside reader opens, on a public repository, for
six days.

The answer is deliberately not a bigger linter — a check for "not applied"
catches this instance and nothing else, and the next stale claim will be a number
or a tense. **ADR-0039 D1** generates the architecture section from `infra/`
behind a drift gate, so the class ends instead of being policed, and prose
survives only as a second rendering of the same generated file. Phase 20 is
planned as 20a (map + gate, $0), 20b (timeline from Terraform's own `-json`
events), 20c (tests panel generated from the suites) and 20d (cost computed from
measured seconds, reconciled once against a real bill). Whole phase under $0.20.

D4 was corrected mid-session by the user and the correction is better: the map is
PERMANENT, not a panel that appears while a cycle runs — at rest it carries the
last measured cycle with its date, which is what a visitor almost always sees.
Two consequences the plan did not have: an identifier is not an ARN, and
per-resource live pulsing would need the deploy role writing the bucket ADR-0026
keeps it away from, so live is per PHASE and the two ways to buy more are priced
and untaken. One cost figure was invented and caught in review — $0.09 and $0.17
are 16a's and 16b's cycles, and 19c has no recorded figure at all.

A second sweep, run after `session-close` had already printed clean, found SIX
more stale places — and none of them a phrase. They were COUNTS: "Three levels
are permanent for that one reason" above a list of four, "Seven root levels: five
permanent", "twenty-seven ADRs" against thirty-nine, the `tf-workflow` skill's
"seven root levels" with a list missing `infra/self-service`, and
`docs/session-primer.md` itself listing seven levels without the sixth permanent
one — the file every session reads first, wrong since 19b. Eleven stale places in
total. The first sweep had grepped for the wording it had already found, and a
count goes stale without a word changing around it.

Two consequences taken rather than noted. ADR-0039 D1 now requires
`topology.json` to carry the counts, with prose rendering them instead of
spelling them out. And the working agreements gain a rule the day earned:
**verify before reporting, without being asked** — this session reported the
primer as fine on the strength of the Mac copy matching the repository, which was
true and irrelevant, because the repository was wrong.

Nothing applied. **$0.** Next allowed step: 20a.

**As of 2026-08-08.** Phase 19g is CLOSED, and with it Phase 19. A launch was
cancelled mid-apply at 00:44:15 and the run's own teardown reclaimed it by
00:49:09 — 4m45s, zero manual AWS calls, no watchdog, no blunt path, nobody
dispatching anything. That sentence had ended four consecutive session summaries
as a prediction; it is now evidence, and it arrived on the first launch of the
day rather than after several.

The mechanism was read, not assumed. The sweep returned `orphans` and exit 1 on
five resources; adoption imported four of them, including
`module.rds.aws_db_instance.this` at two minutes old, and named the fifth
UNADOPTABLE rather than dropping it — a listener, which leaves with its load
balancer, and did. Each of the three defects found on 2026-08-07 met its own
case for the first time in that single run: `rds:db` was reported at all (the
colon/slash parser), an instance adopted while still `creating` no longer killed
the destroy on a null address, and the live sweep printed ZERO `unconfirmed`
lines where the day before it printed two. `release-lock` released the lock,
which by ADR-0036 D2 happens only on `destroy=success` — a second job agreeing
independently with the first.

Two findings arrived before the button was pressed, and both are about
documents rather than infrastructure. The endpoint was NOT parked: two files
said the kill switch had been thrown by hand after 19c, and the control store
had no such item, so the public button had been live since 19g's launches
cleared it. Decided this session, and now recorded: **it stays live** — that is
the finished state of Phase 19, not an oversight in it. And a day's three
launches belong to the UTC DAY, not to a session: 19f's break test and 19g's two
launches shared one cap, which is why the counter read 3 where a summary
described 2. The first explanation offered for that discrepancy — that session
files are named locally and the counter bins by UTC — was wrong, and checking it
took one command: 19f's file is named `2026-08-07` and its launch ran at 17:51
local on 08-06. Both name the UTC day. A plausible cause arriving alongside a
symptom is what ADR-0037 got wrong about the `creating` instance one day
earlier.

Shipped: `scripts/watch-launch.sh`, the watch loop as a checked-in script. It
had been typed into a terminal on three separate days and broke the same two
ways every time — started outside the repository, and killed by an SSH
disconnect — neither of which is a property of the loop. No field it prints may
be blank; every one is a value, `none`, or `ERR`, and the account is re-read on
every tick, because `alb=none` is what a torn-down environment and an expired
token look like alike.

Phase 17 (prod data continuity) remains open and optional. Cost of the run:
about $0.03.

**As of 2026-08-07 (later that day).** Phase 19g SHIPPED and did not close. A
teardown now ADOPTS what it does not manage before it destroys (ADR-0038). The
shape was decided by reading the three candidates against the code rather than
comparing their descriptions: re-dispatch re-runs a destroy that still does not
manage the cluster and the security groups, because those are free and the blunt
path only deletes what bills; widen puts Terraform's dependency graph inside a
Lambda and spends the IAM narrowness that makes the blunt path safe. Adoption
works one layer earlier, and the ordering then dissolves rather than being
patched - the watchdog's existing dispatch has always been the retry, and it was
ineffective only because the destroy it dispatched could not adopt. Its input is
the 19f gate itself, so the check that names the remainder is now the input to
the thing that removes it, and the two cannot disagree about what an orphan is.

Two cancelled launches, and three defects, each found by the previous fix
WORKING. The one underneath everything: `confirm_exists` read a resource's kind
as everything up to the first SLASH, and AWS separates kind from name with a
slash OR a colon - so `rds:db`, `rds:subgrp`, `logs:log-group` and
`secretsmanager:secret` were four `case` arms that had never once been reached,
and every resource of those kinds answered `unconfirmed`. Adoption reads
`orphans` and not `unconfirmed`, which is correct - importing what nobody has
confirmed is acting on an unanswered question - so the RDS instance was never
offered to it. That also corrects a diagnosis: ADR-0037 recorded the missed
instance as a consequence of its `creating` status, and it was never reportable
at all. The defect was invisible where it was tested, because none of those
kinds is tagged once an environment is gone - including on a deliberate
read-only run against the empty account ninety minutes before it fired. A gate
is only exercised by the case it was built for.

With the parser fixed, the second launch adopted 4 of 4 INCLUDING
`module.rds.aws_db_instance.this` - the resource whose absence from state has
failed every teardown since 2026-08-05 - and the destroy died on a null endpoint
address, because an instance three minutes old has none and Terraform evaluates
the configuration during a destroy too. That state was unreachable before
adoption existed. The fix moved the failure rather than removing it. Third:
`cloudwatch:alarm` and `elasticloadbalancing:listener` had no existence rule and
turned `unconfirmed` in the first sweep this project has ever run against a LIVE
environment rather than the remains of one.

Both destroys that finished were green with the account verified empty and a
positive control in the same command. Both were dispatched by hand to skip a
ninety-minute wait, so "reclaimed with nobody in the loop" remains a prediction
and the phase stays open - the same sentence 19c, 19e and 19f each ended on. One
uninterrupted cancelled launch is what is left, and the day's three launches are
spent. The first launch was lost to a sequencing error of mine: the patch was
applied on the devbox and not pushed, and the workflow comes from `main`.

**As of 2026-08-07.** Phase 19f is DONE and did not meet its criterion, which is
the honest shape of the result rather than a failure to report it. ADR-0037's D2,
D3 and D4 all shipped and all three were confirmed by one cancelled launch: the
security-group chain was revoked against real groups, and the group that had held
a destroy for 15m22s the day before left without comment; the verification step
and the new orphan sweep both RAN on a job that had already failed, where the
identical situation on 2026-08-06 produced a run that reported success while an
ECS cluster survived. The remainder still took three manual AWS calls.

The gap is now exact, and it is an ORDERING rather than a missing check. A
cancelled apply creates resources that never enter state. Terraform can neither
delete them nor delete what depends on them - here an unmanaged RDS instance and
the managed subnet group that cannot go while the instance holds it. The
watchdog's blunt path removes the billable orphans, which is precisely what
unblocks Terraform, but only after the dispatched destroy has already failed on
them, and nothing dispatches the destroy that would then succeed. Three candidate
shapes are written down as 19g: re-dispatch, widen the blunt path, or import the
orphans into state.

Three things were learned by running rather than by reading, and two of them
would have shipped as green. D3 is not safe as the ADR wrote it: the verification
step was last, so it had only ever run with live credentials, and `always()` lets
it run after a FAILED credentials step - at which point every `aws` call answers
nothing, which is exactly what an empty account looks like. The tagging API was
wrong in both directions inside one hour, missing an RDS instance that was still
`creating` and reporting a security group a minute after AWS had deleted it; the
stale direction would have reddened every teardown from its first day, and since
a red destroy job keeps the launch lock, the public button would have stayed shut
until its TTL after every launch. And an exclusion for ECS task definitions,
removed on the theory that a more general confirmation mechanism subsumed it,
turned 22 deregistered revisions into `unconfirmed` and the gate red on an
account that was empty - the same failure arrived at from the other side.

Also true: `tag:GetResources` is now on the deploy role, applied locally to
infra/bootstrap-oidc, and was checked against the ROLE with
`simulate-principal-policy` rather than under demo-admin, which holds the grant
anyway - a control that inherits the privilege of whoever runs it proves nothing.

**As of 2026-08-05 (later that day).** Phase 19c RAN and is NOT closed. The
button was pressed anonymously from a browser for the first time, a full cycle
deployed and destroyed itself, the dashboard reported it while it ran, and the
90-minute TTL was read out of the lock the code writes rather than out of a
document. Both watchdog paths fired against real environments, including the
blunt one, which deleted a live ECS service, ALB and RDS instance in that order
with the AWS CLI as the witness rather than the function's own answer.

Three defects were fixed on the way, and all three had survived because nothing
that could see them had ever looked. The reply carried `access-control-allow-origin`
TWICE - once from the handler, once from the Function URL's cors block - which
is invalid, and which the browser is the only client able to notice: the CORS
layer only joins in when a request carries an `Origin`, so curl without one
looks healthy, and preflight is answered by the Lambda service instead of the
function, so it cannot show the pair either. Both probes run that morning were
built so they could not see it. `release-lock` had never worked at all: all
three repository variables it reads were absent, two of them written down in
preflight-inventory since 19b and never created, and a missing `vars.X` expands
to an empty string rather than an error, so the failure surfaced three jobs
away from the omission. And the page had been left pointing at an empty
endpoint by 19b itself.

What keeps the phase open is not a defect but a state. A run cancelled mid-apply
leaves an S3 state lock AND resources that never reached state; `destroy` dies on
the lock, `release-lock` releases anyway because it never asks how destroy went,
and the watchdog's `dispatch_destroy` skips its own record when the lock is gone -
so the grace period never starts and the blunt path cannot engage in exactly the
case it was written for. The log shows it re-dispatching every five minutes while
an ALB and an RDS billed. Getting out took force-unlock and deleting three
unmanaged orphans by hand; the recovery the watchdog documents - "re-run destroy" -
burned two full fifteen-minute timeouts failing. That needs a decision, not a
patch, and it is 19d.

Also true and worth keeping: `run_url` in the `locked` refusal can never be
filled, because the lock is taken before the dispatch and `workflow_dispatch`
returns no run id - 19b proved that refusal against a hand-seeded item carrying a
field the real writer never writes. And the kill switch does not stop a GET: with
it engaged the endpoint still issues a nonce, while `infra/self-service/README.md`
says it "refuses every request".

The endpoint is parked again, by hand, with the honest reason in the store. The
account is empty, verified with a positive control in the same command.

**As of 2026-08-05.** Phase 19b is CLOSED: the sixth permanent level is
APPLIED, the button exists, and it is deliberately parked behind its own kill
switch until 19c presses it on purpose. Twenty-five resources, about $0.45 a
month standing, of which $0.40 is the one Secrets Manager secret that holds the
GitHub App's private key - the single static credential this project now admits
to, pasted by hand and readable by one role.

Every refusal 19b owns was seen firing against the real table: the kill switch
from a message shaped like the one AWS Budgets actually sends, restored by
deleting the item so it releases rather than sticks; `store_unavailable` from
BOTH halves, naming `issue_nonce` on the GET and `get_flag(killswitch)` on the
POST; `locked` naming its holder and its run_url, with `gh run list` showing
nothing queued and a positive control in the same command; and `daily_cap` with
two assertions rather than one, because the cap is evaluated after the lock is
taken and a refusal that kept the lock would wedge the button until its
deadline. What could not be shown is exactly what ends in a dispatch - the
takeover of an expired lock, the TTL, the watchdog's blunt path - and that is
19c.

Two defects were found by APPLYING, and both had been green the day before under
`make tf-validate`, `make iac-scan` and 21 in-process assertions. The
concurrency reservation ADR-0034 called the endpoint's independent cost bound
cannot be applied at all while the account's Lambda quota is 10, because a
reservation may not take the unreserved pool below 10; no quota increase was
asked for, since three rarely-invoked functions do not need one and the account
ceiling is then the bound. And a public function URL has required TWO policy
statements since October 2025 - `InvokeFunctionUrl` AND `InvokeFunction` - while
the provider writes only the first, so every request was refused 403 with the
function never invoked, and the missing half was the half nobody wrote. The fix
took provider `~> 6.0` on this level alone and produced zero drift.

The two dead ends are worth more than the fix. An organization policy was
"ruled out" using `AvailablePolicyTypes`, a field AWS documents as unreliable,
and only later ruled out properly with `list-roots`. And a throwaway function
with its own URL reproduced the 403 exactly, which read as proof that the
account was at fault - it was not, because the same single statement had been
added to it by hand. **A control that reproduces the defect is not a control**,
which is the 15a lesson arriving from the other side.

A third finding came from USING a guardrail rather than testing it: nothing in
this repository turns the kill switch off, and its refusal names the budget
alarm however it was engaged. And `CKV_AWS_301` fired for the first time only
because the fix made the public grant visible to Checkov at all - the provider's
half was never in the code - which became the repository's first inline skip,
scoped to one resource so that any OTHER public Lambda still fails.

Open and deliberately undecided: whether the button should be anonymous. The
owner asked twice whether a stranger should be able to spend his money and
proposed an approval-by-email or an on/off window instead; the answer was build
as designed, then decide. Nothing changed, so there is no ADR - but the cheapest
form, if it is taken up, is inverting the default of the kill switch that
already exists, with a deadline the code compares against rather than a DynamoDB
TTL, whose deletion is best-effort and can lag two days.

**As of 2026-08-02.** Phase 19a is WRITTEN and NOT APPLIED. The sixth permanent
level exists in git - control store, launch Lambda behind a Function URL, an
EventBridge-scheduled watchdog, a kill-switch Lambda on an SNS topic, and a
callback role that can delete exactly one item in one table - together with the
launch workflow (launch -> destroy `if: always()` -> release-lock
`if: always()`, stage only), 21 in-process assertions over every refusal, and
the dashboard button behind a flag pointing at an empty string. No AWS API was
called and nothing was applied, so the button does not exist.

The finding is a guardrail that would have eaten its owner. ADR-0035 says a
resource with a missing deadline is EXPIRED rather than exempt; applied
literally, that rule destroys the owner's own stage environment, which carries
no deadline because no deadline is exactly what "a human is watching this one"
looks like. The rule is not wrong - its SCOPE was unstated, and ADR-0035 already
says the guardrails do not apply to the owner's own runs. The cost of that
sentence in code is a `Launch` tag, empty for an owner cycle and set by the
public launch workflow: the watchdog acts only where it is non-empty, and inside
that scope a missing deadline is still expired. It is enforced twice, because a
filter in a handler is a claim and an IAM condition is a fact - and the `Null`
test in that condition is NOT redundant with the `StringNotEquals`, because for
a resource with no tag at all a `StringNotEquals` evaluates TRUE, which is the
quiet default that turns a policy into decoration.

The plan also did not know the Lambda runtime ships no crypto: minting a GitHub
App installation token means signing an RS256 JWT, so PyJWT and cryptography are
vendored by `make self-service-package`, which refuses when pip is missing and
when nothing was vendored, and Terraform refuses a package under 500 KB - an
empty zip deploys happily and fails at the first request, where nothing is
watching. Four break tests fired locally (a store failure read as zero launches,
the kill switch read after the nonce, the cap refusal keeping its lock, a
missing deadline read as permission), each restored from a copy taken first.
None of the five refusals has yet been proven against the real table, which is
19b.

Running the validation corrected the chat twice, and both corrections were about
a TOOL rather than about the code. `terraform fmt` does not align across a
multi-line value - `sid` before `actions = [` stands alone, and so does `Version`
before `Statement = [{` - so the approximate fmt checker written in the sandbox
measured an assumption about the tool instead of the tool, which is the same
shape as a break test that fails to break and as `docker compose config` giving
two answers on two hosts. And Checkov found CKV_AWS_297, EventBridge Scheduler
without a customer-managed key: four CMK skips were predicted correctly from
reading the resources and the fifth was invisible from the code, which is the
difference between a skip list written and a skip list run. Everything else was
green first time, including `infra/self-service` under `make tf-validate` and
all four CI jobs on the push.

**As of 2026-08-02.** Phase 19 has its decisions and does not yet have a line
of its code. **ADR-0034** puts the trigger on a Lambda Function URL and a GitHub
App at a new permanent level, and says the thing the phase makes true: the
button reverses this project's one direction of trust. Everywhere else GitHub
authenticates to AWS over OIDC and no static AWS key exists; here AWS must
authenticate to GitHub, where no OIDC exists, so a long-lived GitHub credential
enters the project and the claim becomes "no static AWS keys anywhere, and
exactly one static GitHub credential, in Secrets Manager, readable by one Lambda
role". The lock, the day counter and the kill switch are state ABOUT a cycle, so
they live above the environments - the sixth arrival at the ADR-0027 rule. The
public path reaches stage and cannot reach prod by IAM rather than by an input,
and the nonce is written down as a speed bump rather than as authorization,
because the design goal is not that only the right people can press the button
but that it does not matter who does.

**ADR-0035** is the five refusals, with numbers instead of adjectives: TTL 90
minutes, three launches a day, about $0.30/day worst case against the $0.09 and
$0.17 cycles already measured. The cap fails CLOSED, since an unreadable counter
is not zero launches today - the same sentence as the expired SSO token that
printed nine empty lines that looked exactly like a clean account. And one
finding, which amends the plan rather than implementing it: the out-of-band
watchdog cannot be a cron on the Lightsail devbox. A cron has no human, the
devbox reaches AWS through a device code somebody types, and unattended
therefore means a static credential on disk. The domain actually distrusted is
GitHub Actions rather than AWS - and a watchdog independent of AWS could not act
during an AWS outage anyway - so EventBridge Scheduler plus a Lambda buys the
same independence at no credential. Phase 19 is now 19a (scaffold, $0), 19b
(apply and prove four refusals without a cycle) and 19c (one live launch, the
TTL proven by killing it, and the blunt teardown path broken on purpose).

**As of 2026-08-02.** Phase 18 (remaining documentation) is CLOSED, pulled
forward of Phases 17 and 19 for the same reason Phase 12 was pulled forward of
13 in the MVP track: it changes no infrastructure and the phases after it
benefit from it existing first. Three documents: `docs/cost-control.md` (the
permanent-vs-per-cycle cost split, and the two cycle costs already measured
closing 16a and 16b, cited rather than re-derived), `docs/interview-talking-points.md`
(five roles, every point traced to an ADR or a session summary), and
`docs/lightsail-devbox.md` (the devbox's role versus the AWS deploy target, the
SSH tunnel, and the two non-default login flags this project has needed since
Phase 1). No ADR — no structural decision, nothing to record beyond the phase
gate itself. None of the three joins the LIVING set `docs-check` enforces; every
ADR number, `make` target and repository path they cite was checked by hand
against the working copy instead, the same four kinds of claim the mechanical
check makes for the narrower living set.

**As of 2026-08-01.** Phase 16 was split on arrival, and both halves are now
CLOSED. **16a** added the rest of the read/update surface (GET by id, PATCH,
pagination, the full negative matrix), an inline edit control for Playwright to
drive, and `updated_at`, all recorded in **ADR-0031** before the code; the
database assertion after a UI action proves an UPDATE rather than an insert with
the right name. **16b** added structured JSON logs with a request id, a
CloudWatch metric filter on 5xx and one alarm, recorded in **ADR-0032**.

Since then one Ops session, **ADR-0033**. 16b closed four times, each time
reported complete, and the exit checklist was never the problem — it lives in
four documents and three of them were read. Prose does not run, so the two ends
of a session became commands: `make session-open` refuses to start on a working
copy that is not what it claims to be and prints the phase from the cursor,
`make session-close` checks the record of the session and prints the
Consequences of any ADR it added. Running them found that `INDEX.md` had stopped
being chronological, which had already made the entry command report the wrong
session.

16b's central point is that its two halves are one decision: the metric filter
READS the log, so the shape of the log decides whether the alarm can exist at
all. `status` has to be a JSON number or the filter compares strings and matches
nothing forever; the exception path has to be logged or the most valuable 5xx is
invisible. Neither property can be seen by an HTTP client, which is why
`tests/unit/` exists — a fourth suite, in-process, holding the log's shape as a
contract.

The signal comes from the application's own log rather than the ALB's free
`HTTPCode_Target_5XX_Count`, because the line names the path and the request id,
so the alarm and the evidence are one artifact. What that choice cannot see is
written down: an ALB answering 503 with no healthy target raises nothing here.
And the alarm ships with no notification, because an SNS email subscription
needs a confirmation click and a topic beside a per-cycle environment would ask
for one every cycle — a notification channel has to outlive what it reports on,
the fifth arrival at the ADR-0027 rule.

What both halves have in common is worth carrying. From 16a: a test that skipped
itself on its first run reported the same colour as a pass; a deliberate
off-by-one passed all 50 contract tests because every pagination assertion was
about the newest rows while an off-by-one drops the oldest; and two tests that
passed on localhost timed out against the stage ALB, because latency is a path
and it had never been exercised. From 16b: `default_value = 0` made the metric
billable from the first ALB health check while ADR-0032 claimed it did not exist
until the first 5xx, and the alarm held ALARM for exactly sixty seconds while
notifying nobody. Both were found in one command's output and neither was
reachable by review — a document and a command disagreeing, with the command
right.

The cycle that closed the phase also paid the Phase 15b debt: `setup-terraform`
v4 and `configure-aws-credentials` v6 ran in all four dispatch-only workflows
for the first time and none of them failed.

**As of 2026-07-28.** Phase 13 (the empty-to-empty verification run) and Phase
14 (release resilience, ADR-0029) are CLOSED — see `docs/phase-gates.md`, which
remains the only file that claims to know where the project stands. Phase 15 was
then split: **15a is CLOSED at $0** — Dependabot over five manifests, gitleaks as
a gate in `ci.yml` over the full history, and the budget email moved from a
GitHub variable to an environment secret. **15b is CLOSED, also at $0**:
Checkov over `infra/` with four findings fixed and 46 skip decisions recorded
beside the checks they skip, Trivy over the image each commit builds, and every
third-party action pinned to a commit SHA (**ADR-0030**) with a check that keeps
them pinned. The `ci` workflow now runs five AWS-free checks.

Two things from 15b are worth carrying. The Trivy gate went red and then green
in CI on a REAL vulnerability: three HIGH findings in `starlette`, and
Dependabot's PR #5 — `fastapi 0.115.6 -> 0.140.13`, resolving `starlette 1.3.1`
— turned out to be exactly the fix, arrived at independently from the other
direction. And a gate on a shared dependency reddens every open pull request:
the moment `image-scan` was on `main`, the four other Dependabot PRs failed on
findings none of them introduced.

Two things from 15a are worth carrying rather than filing: the GitHub Actions
annotation channel was reporting two stale actions out of six, so four had aged
invisibly including the one that performs every OIDC authentication; and the
secret gate's break test came back GREEN on a planted AWS access key id, because
gitleaks 8.30 does not treat an access key id alone as a finding. The gate was
sound and the assumption was not.

Phase 0–8 = done as far as they go: the Phase 8 lifecycle half is CLOSED, the
feature half is not started. **Phase 9 is CLOSED (2026-07-26): 9.0
reconciliation on 07-25, 9.1 prod + promotion + HTTPS on 07-26. Phase 10 is
CLOSED (2026-07-26) — validated against AWS, not only locally. Phase 11.0
(publish the repository) was pulled forward and is DONE. Phase 11.1a — the
decisions and the scaffold for the public dashboard — is CLOSED (2026-07-26):
`fmt -check` clean and `tf-validate` green over seven discovered root levels,
with nothing applied to AWS. Phase 11.1b APPLIED the level on 2026-07-26: 16
added, 0 destroyed, first attempt, and there is now a FIFTH permanent state
level in AWS behind https://demo.uveapp.net — which returns 200 and stays up when
every environment is destroyed. 11.1b is CLOSED: `publish-site` ran green under
the narrow publish role, and the guard that stops the site sync from deleting the
published evidence was proven in both directions. **Phase 11.1c is CLOSED
(2026-07-26): the dashboard has content, and a full cycle ran underneath it with
no manual AWS operation — deploy-stage #21, promote-prod #4 behind a reviewer,
destroy prod #12 behind a reviewer, destroy stage #13. The environment panels
were WATCHED going no observation → up → unknown → destroyed. Every defect the
cycle found was in the browser half; nothing on the AWS side failed.**
**Phase 12 is CLOSED (2026-07-27), at $0 and without touching AWS: the
repository has a README for the first time in its history, an architecture
document, and a demo script; the two known-stale places are corrected; the
control-layer tooling is in git (ADR-0028); and `make docs-check` now checks the
six living documents against the repository in CI. No cycle was run — a
deliberate exception to the end-of-phase destroy invariant, recorded in
`docs/phase-gates.md` rather than left silent, because the phase changed no
HCL, no AWS-touching workflow and no application code. Phase 13, the
empty-to-empty verification run, is next.**

The full cycle now runs end-to-end through GitHub Actions with zero manual AWS
operations for BOTH environments:

```text
deploy stage → tests gate it → a human approves → the tested image is promoted
BY DIGEST to prod at https://app.demo.uveapp.net → both environments destroyed
```

That was the project's headline goal, and it is done. Phase 10 then made what
the cycle gates on mean something: an items slice with real negatives, suites
split into read-only and destructive by directory, and a database assertion
proving a browser action reached RDS — all of it now exercised against AWS, not
just against Compose. What the MVP still lacks is the public dashboard
(Phase 11.1).

Phase 9.0 made `infra/envs/prod` valid for the first time in seven weeks, moved
the container registry to a permanent state level (**ADR-0018**), and closed the
validation gap that let an invalid IaC directory sit in the repository unnoticed.
`make tf-validate` now discovers every root level and runs hermetically. Nothing
was applied to AWS in that session.

Stage infrastructure is FULLY DESTROYED in AWS — zero billable resources.
Nothing is billing except the near-zero state bucket. The OIDC provider + deploy
role from `infra/bootstrap-oidc` are still present (IAM, free) because a stage
teardown does not touch that state level.

### Phase 12 (2026-07-27) — the documents, and what running them found

The phase was planned as "rewrite the stale README". One command changed its
shape: `git log --all -- README.md` came back empty. There was no stale README;
Phase 8 had deliberately declined to commit a false one, so this was a blank
page rather than an edit.

Three things were decided rather than assumed. The architecture diagram is drawn
twice — here in Mermaid and in `site/index.html` — and the document says so, and
says which artifact wins: neither picture, but the directories under `infra/`. No
cycle was run, because the phase changed no HCL, no AWS-touching workflow and no
application code; the exception to the standing invariant is written into the
cursor rather than left silent. And ADR-0028 finally settled a question the
transfer buffer's own README had left open for one, moving `send.sh` into git
and fixing the bare-name lookup that had been delivering the stale primer copy.

What running things found, none of it by review: the Mermaid blocks were parsed
by mermaid's own parser and the parser was then made to fail twice on purpose;
`send.sh`'s new lookup passed its third case only through a `set -e` exemption
and was rewritten as an explicit `if`; and the new `make docs-check` caught a
false claim in `docs/phase-gates.md` that had been sitting in the cursor since
Phase 6 — the assert-seed script named by a path that exists only inside the
image — then caught the same mistake again in the paragraph written to describe
the catch. The gate was seen red six times before it shipped, once for its own
list of documents going missing.

The recorded prediction for this phase is that the first genuinely new reader
finds something true but unusable in the README — an instruction that assumes
context the writer had. `docs-check` cannot see that class of defect: every
command exists, and existing is not the same as being enough.

### Phase 11.1c validation (2026-07-26) — what a real cycle did to the page

One cycle, no manual AWS operation: `publish-site`, `deploy-stage #21`,
`promote-prod #4` paused for a reviewer, `destroy prod #12` paused for a
reviewer, `destroy stage #13`. The 11.1b plumbing ran for the first time and was
green in all four runs.

What the page showed, watched rather than reconstructed: stage
`no observation → up`, prod `no observation → up → unknown → destroyed`, each
step naming the run responsible. The `unknown` is the design working — the two
sources disagreeing on purpose while a destroy was in flight and nothing had
observed AWS since. Promotion by digest became legible instead of asserted: stage
on `:70bb5d5...` and prod on `@sha256:094e7838...`, side by side. `run-name`
proved itself in one screen, with #12 and #13 attributed to prod and stage while
every earlier destroy still reads `stage, prod`.

Three defects, all found by running it and all the same shape — the page saying
something it was not in a position to say. A panel with no status file claimed
"nothing has reported" while a deploy was sixteen minutes into reporting. The
step list called an absence a failed read while a promotion waited for its
reviewer, because GitHub returns a job with no steps until it starts. And refresh
was GitHub-only every three minutes, which from outside looks like a dead page;
the two sources now run at the speed each one costs, with GitHub paced by the
rate-limit headers it returns.

The recorded prediction was wrong for the fourth time in a row: the AWS side, where
failure was expected, did not fail once. Everything broke in the browser, in the
half no fixture could cover because it needs a real run to exist.

And one trap was caught in the act, inside a command written this session:
`grep -rn 'pull_request_target' .github/ || echo none`, run from the wrong
directory, printed `none`. grep exits 1 for "no matches" and 2 for "could not
look", and `||` cannot tell them apart — an error rendered as a clean result, in
the session that documents that exact failure mode twice. The corrected check
prints the exit code.

### Phase 11.1c session (2026-07-26) — the page, before it has ever seen a run

Full write-up: `docs/sessions/2026-07-26-phase-11-1c-dashboard-content.md`.

`site/index.html` stopped being a placeholder. One file, no build step, no
dependencies and no credential: environment panels fed by `status/<env>.json`
from this bucket, the current cycle's every STEP with state and duration from the
public Actions API, twelve runs of history labelled by environment, and the
architecture drawn as the split that actually matters — the five permanent levels
against the ones destroyed every cycle.

The design work was not the layout, it was deciding what the page is allowed to
say. ADR-0026's rule that a source may only assert what it observes had to be
scoped in both directions before it could be rendered. Too wide, and a
documentation commit turns both environment panels amber because `ci` happens to
be the newest run; too narrow, and a `destroy` run cannot be attributed at all,
because the anonymous API does not expose `workflow_dispatch` inputs. The first
is fixed by comparing each environment against the newest run that WRITES ITS
FILE. The second cost one line of YAML — `run-name: destroy ${{ inputs.environment }}` —
which is not cosmetic: it is what makes the run observable to the only source
entitled to describe runs. Runs from before it degrade to "unknown", visibly.

Everything degrades loudly rather than emptying, because an empty result is not a
clean result: a rate-limited API renders a named banner with the time of the last
successful read, a missing status file renders "no observation" and never
"destroyed", and a panel whose freshness cannot be checked labels itself
unverified instead of implying it is current.

None of this had run when it was written, and the states worth seeing are exactly
the ones a healthy cycle will not produce on demand. So the render logic was
driven through a stub DOM with six fixtures — `ci`-after-destroy, a deploy in
flight, a matching run id, missing files, a 403, and an unattributable destroy —
and each produced the intended badge and wording. That is a proxy for the real
thing, and it is the only way the failure paths get looked at at all.

### Phase 11.1b session (2026-07-26) — the level exists in AWS

Full write-up: `docs/sessions/2026-07-26-phase-11-1b-apply-and-publish.md`.

The apply was the whole billable content of the step and it was uneventful: 16
resources added, 0 destroyed, first attempt, roughly four minutes, most of it the
CloudFront distribution. Verification was done against the AWS CLI and `curl`
rather than against Terraform state, and returned **403 on all three names with a
verified certificate** — which is the correct answer while the bucket is empty,
and the reason the step was worth doing before any content existed: it separates
"the hosting works" from "the page is right".

Two things the session got for free, both cheaper than the checks that would
otherwise have been needed. The two data sources resolved at PLAN time, which
proves `infra/dns` and `infra/bootstrap-oidc` are applied without querying
either. And the untracked `.terraform.lock.hcl` in the new level turned out to be
short one hash, because `tf-validate` had written it without ever installing the
provider — a small, real gap that only a genuine `init` would have closed.

The plumbing written here obeys ADR-0026 by splitting one job across two roles:
the deploy role observes ECS/ALB/RDS, the narrow publish role writes the bucket
and invalidates. Neither is allowed to describe what the other saw. The status
file also became one object per environment, because destroying prod while stage
deploys is a normal cycle and S3 has no compare-and-set for a shared file.

`publish-site` then ran green in 18 seconds, first attempt, and the two things
worth asserting were read out of its log rather than assumed: the identity was
the publish role, and the 200 on the apex was asserted by the workflow rather
than eyeballed. The `--exclude` guard was proven in both directions with a canary
and a `--dryrun` — without the excludes the sync deletes every status file and
report, with them it deletes nothing.

The session also closed a tag divergence it had itself created: `Owner=uve` on
the new level against `Owner=UVE` everywhere else, inherited from the lowercase
value 11.1a put in the tfvars example. Re-applied, tags only, 0 destroyed. The
preflight document turned out to name a third value that nothing in the account
had ever carried.

What remains unrun is the status-file plumbing in the three lifecycle workflows.
Only a real cycle exercises it, and that is 11.1c.

### Phase 11.1a session (2026-07-26) — decisions, scaffold, and one direct question

Full write-up: `docs/sessions/2026-07-26-phase-11-1a-decisions-and-scaffold.md`.

The debt Phase 11.0 left was paid first: gitleaks over the full history, every
ref, 81 commits, nothing found — and then the same invocation was pointed at a
throwaway repository holding a fake key, so that the green result came from a
check demonstrably able to go red. `git rev-list --all --count` returned the same
81, which is what makes "the whole history" a measurement rather than a hope.

Two decisions. **ADR-0026** answers where the dashboard's status comes from, and
the answer is both sources, divided by what each can observe: GitHub Actions
knows where a run is and nothing about what exists in AWS; a file written by a
workflow knows what was there when it finished and cannot know a run is in
flight. Neither is allowed to speak for the other, and because each carries a
run id, each detects the other going stale. **ADR-0027** puts the dashboard in a
new permanent state level for a reason this project has now met three times —
after the registry (ADR-0018) and the hosted zone (ADR-0024) — and this is the
sharpest form of it: the exhibit cannot be destroyed by the thing it exhibits.

The scaffold for `infra/public-site` is written and nothing is applied: private
bucket, CloudFront with OAC, a second certificate in us-east-1 because CloudFront
takes no other region while the prod ALB takes only its own, and a publish role
narrow enough to be uninteresting if it leaked — this bucket, this distribution,
no branch subject at all.

The session also answered a question asked directly rather than found in the
code: can a stranger start a billable run now that the repository is public. The
answer is in `docs/security-posture.md`, with the re-checking command beside every
claim rather than the claim alone. Four independent locks; the interesting part
is the two things that are NOT covered by any of them — public Actions logs can
carry `TF_VAR_budget_email`, and the fork-PR approval setting is UI state, in the
same uncheckable category as prod's protection rules and the NS record in the
parent zone.

### Phase 10 closing session (2026-07-26) — the AWS validation cycle

Full write-up: `docs/sessions/2026-07-26-phase-10-aws-validation.md`.

One cycle through Actions, no manual AWS operation: deploy-stage green on the
first attempt, promote-prod paused for required reviewers then green, destroy
prod and destroy stage green. Prod was checked from outside the workflow that
declared itself green — `curl` from a different host confirmed the certificate,
the HTTP redirect, and `/api/items` returning the seeded row with a `description`
column, which is what proves prod ran the Phase 10 slice on a database migrated
to revision 0002 rather than an older image answering `/health`. Teardown
confirmed against the AWS CLI, not Terraform state.

The phase-gate note had predicted one failed run, because every genuinely new AWS
path in this project had cost exactly one. It was wrong this time, and is kept as
wrong rather than deleted: the reasoning stands as the default for the next path.

The session's real findings were not in AWS at all.

`aws sso login` needs `--use-device-code` on the headless devbox. That was
already documented — in one file — while eight others still printed the flagless
form, and those were the ones being copied from. A trap documented once is not a
trap removed while the wrong command stays copyable; this is the
`promote-prod.yml` "read-only" comment wearing different clothes.

A post-teardown check whose SSO token had expired printed an empty list for every
resource, which is indistinguishable from a clean account. It now starts with
`aws sts get-caller-identity` and assigns each result under `set -e`, so losing
credentials aborts instead of rendering green. The `teardown` skill also still
expected the ECR repository to disappear — false since ADR-0018 — and would have
made a correct teardown look failed; it now lists all four permanent levels.

And the operational hazard worth carrying into the demo script: prod appeared
dead in the browser for half an hour while serving 200s the whole time. The macOS
system resolver held a NEGATIVE cache entry for `app.demo.uveapp.net`, a name
that is dead most of the time by design (ADR-0017 D2a). `dig` resolved, `curl` on
the same machine did not, because only the second goes through the system
resolver. Verify prod with a request that bypasses it, and flush the cache before
showing anything to anyone.

### Phase 10 session (2026-07-26) — the thin application slice

Full write-up: `docs/sessions/2026-07-26-phase-10-thin-application-slice.md`.

The cycle worked; what it gated on did not mean much. One smoke test and a seed
assertion cannot tell a working application from one that returns 200 for
everything. Phase 10 adds the smallest surface worth gating on — items
create/list/delete with real negatives, a page that drives it, 19 HTTP contract
cases, a Playwright regression, and a database assertion made by a DIFFERENT
process than the browser that wrote the row.

Validated on the devbox against real PostgreSQL and green in CI on the first
attempt (`ci` 30217591361). Nothing had run against AWS at that point, so the
phase stayed open until the following session closed it. The migrate step is the one worth keeping: the
volume had survived earlier sessions, so alembic upgraded an EXISTING database
instead of building a schema from nothing — a path that could not exist before
this phase added a second revision.

Both new gates were also made to fail on purpose: the spec-coverage guard with a
stray spec, the UI-write assertion with a probe name nothing had created. A gate
seen only green is indistinguishable from one that cannot go red.

The finding is the familiar one. `promote-prod.yml` carried a step called
"Read-only smoke against prod" and ran `npx playwright test` — the whole
`testDir`. The comment was an intention the command could not honour; it was
true only because no destructive spec existed, and the first one would have made
prod destructive silently, with nothing turning red. Suites are now split by
DIRECTORY into Playwright projects, every caller names its projects explicitly,
and a guard fails when a spec belongs to no project (**ADR-0025**). The guard was
verified by breaking it on purpose, because an unexercised guard is not a guard.

Second-order but the same species: the ECS run-task loop existed in two copies,
and this phase needed to teach it environment overrides. That is precisely the
change that lands in one copy and not the other, so it moved to
`scripts/ecs-run-task.sh` and both workflows call it.

### Phase 9.1 closing session (2026-07-26) — prod, promotion, HTTPS

Full write-up: `docs/sessions/2026-07-26-phase-9-1-prod-promotion-https.md`.

HTTPS went onto a **delegated subdomain**, `demo.uveapp.net` (**ADR-0024**). The
authoritative zone for `uveapp.net` turned out to be in `org-management` — the
account ADR-0001 forbids this project to deploy into — which turns delegation
from the convenient answer into the only acceptable one. A new permanent level
`infra/dns` holds the zone and the wildcard certificate; the alias record stays
in `infra/envs/prod`, because it points at an ALB rebuilt every cycle. Seven
state levels now, not six.

Two defects worth remembering. `destroy.yml`'s "nothing billable remains" check
searched the whole account for the project prefix, so tearing down one
environment while the other was up would have failed a correct teardown — found
by reading, fixed, and then proven in the same session by destroying prod while
stage was live. And `promote-prod` failed its first plan on two IAM reads no
inspection would have revealed, `route53:ListTagsForResource` and
`acm:GetCertificate`, both issued by data sources the configuration never asks
to read tags or bodies from. The lesson generalises: budget one failed run for
every genuinely new path, because that is the only detector this class has.

An hour went to a hosted zone that looked authoritative and was not. The ground
truth for a delegation is what the TLD publishes, not what a console shows.

### Phase 9.1 session (2026-07-26) — the OIDC split, and why the repo went public

Full write-up: `docs/sessions/2026-07-26-phase-9-1-oidc-split.md`.

Two structural findings, both caught by reading rather than by an error.
`iam_github_oidc` created the identity provider and the deploy role together,
and AWS allows one provider per issuer URL per account — so the second role prod
needs could never have been a copied module block (**ADR-0021**). And prod's
trust policy, if copied from stage, would have carried
`ref:refs/heads/main`: a subject any workflow on the default branch satisfies,
which would have made the reviewers real in the GitHub UI and absent from IAM.

Then the gate turned out to be unavailable at all: required reviewers need a
public repository outside Enterprise, confirmed by the protection-rules block
simply not rendering. **Phase 11.0 was pulled forward and the repository is now
public** (**ADR-0022**), which also retired the read-only clone token of
ADR-0020 the same day it was adopted.

Publication was preceded by a full-history sweep: clean on credentials, and four
identifiers accepted as public with stated reasons rather than rewritten away
(**ADR-0023**). The deciding number: 39 commit hashes are referenced 103 times
across `docs/`, and `filter-repo` would have silently invalidated every one of
them. Buying privacy with the project's own documentation invariant was the
wrong trade.

The session also changed how chat sessions exchange state with the repository
(**ADR-0020**): clone in over a read-only token, deliver out as one `git am`
patch. Adopted mid-session and used for its own delivery. The token half expired
within hours, by its own terms, when the repository went public.

**The plan for everything after Phase 8 now lives in `docs/next-phases.md`**
(in git), shaped by **ADR-0017**. It supersedes the unordered wish-list in
`project-prompt.md` §14. Two tracks:

```text
MVP     9  prod + promotion + HTTPS      (9.0 reconcile scaffold, 9.1 build)
       10  thin application slice
       11  public dashboard (S3 + CloudFront)
       12  minimum viable documentation
       13  MVP verification gate (empty → empty in one run)
Polish 14  release resilience / rollback
       15  security gates (Trivy, Checkov, gitleaks, Dependabot)
       16  full test depth + observability
       17  prod data continuity (optional)
       18  remaining documentation
       19  guarded self-service launch + out-of-band watchdog
```

### Phase 9.0 session (2026-07-25) — reconcile prod, close the validation gate

Full write-up: `docs/sessions/2026-07-25-phase-9-0-reconcile-prod.md`. Highlights
that change how the rest of the project is built:

- **ADR-0018** closed the ECR question `next-phases.md` had left open. The
  "(simplest)" label on the shared-registry option was an assumption and wrong:
  a shared registry inside stage state is deleted by stage teardown, taking the
  image prod has promoted with it. The registry is now level 3 of six.
- The change **removed** two workarounds instead of adding any: the targeted
  `apply -target=module.ecr` and the `terraform output` lookup in
  `deploy-stage.yml` both existed only because the registry did not exist in an
  empty stage state (bug b71b846).
- **Four defects beyond the five documented ones**, all found by reading the code
  rather than the plan: `prod/outputs.tf` lacked the four outputs `run-task`
  consumes; `destroy.yml`'s prod choice died at OIDC authentication because
  `bootstrap-oidc` creates exactly one role; `destroy.yml` still exported dead
  `TF_VAR_github_*`; `state_bucket_name` was dead in STAGE as well as prod.
- **`terraform init -backend=false` does not skip the backend** in a directory
  initialized for real — it reuses the cached S3 config in `.terraform/`. The
  Makefile comment promising "no AWS creds needed" was false on the devbox and
  true in CI only because a fresh checkout has no `.terraform/`. Fixed with an
  isolated `TF_DATA_DIR`; the claim now has a test.
- **A mistake worth keeping:** the first version of the new validate target
  would have passed green if `find` returned nothing — an empty value passing
  silently, i.e. b71b846 again, written one commit after recording that lesson.
  Fixed in e1e577a. Knowing a failure pattern by name does not stop you writing it.

Repo (origin/main), most recent first:

```text
972c109  docs: close the Phase 9.0 session — cursor, summary, index, trap list
e1e577a  ci: tf-validate must fail when it discovers nothing
e05cc02  ci: validate every root level, hermetically
1987c1f  fix(prod): reconcile the Phase 4 scaffold against the post-C2 modules
ab22a58  feat(ecr): shared registry at a permanent state level (ADR-0018)
2027654  docs: discussion-log — six state levels, ECR leaves the per-cycle teardown
ffe060d  docs: primer — six state levels; the chat supplies the transfer path
0ce9326  docs: ADR-0018 shared ECR at a permanent state level
d56d820  docs: primer — the chat drives the session, devbox executes
1f50243  docs: move discussion-log into git (last artifact outside the source of truth)
bbe8bd0  docs: close the 2026-07-25 planning session — phase-gates Phase 9, summary, index
ee0a25e  docs: next-phases — Phase 9.0 reconcile the stale prod scaffold
f8f32e5  chore: commit the control layer (CLAUDE.md, skills, sessions) + ADR-0017 + next-phases
8912aa9  docs: phase-gates — Phase 7 done, Phase 8 lifecycle closed
f08f2f4  docs: ADR-0016 destroy the ALB before the network
6944229  chore(deploy): manual dispatch only, drop the push trigger
58ec209  fix(oidc): allow eks:ListClusters for the teardown verification step
b110b41  fix(destroy): unblock teardown via Actions
b71b846  fix(deploy): create ECR before build; fail loudly on empty repo URL
5735430  refactor(oidc): C2 — move OIDC provider+deploy role to infra/bootstrap-oidc
8d3ed9d  fix(destroy): retry terraform destroy (WRONG fix — REVERTED in C2/5735430)
181cabd  chore(ci): bump actions to Node 24
497a4b2  docs: mark Phase 7 done (destroy validation)
2c1efcc  fix(oidc): allow environment:<name> sub in deploy role trust policy
1675f53  docs: mark Phase 6 done (36ecfba) + carry-forward learnings
36ecfba  fix: in-image DB-assert script for run-task (build context is app/)
a309763  chore: commit bootstrap provider lock (aws 5.100.0, amd64+arm64)
2c4162b  fix: add depends_on=[module.alb] to ecs in stage
40eb757  feat: phase 5 github actions workflows (ci, deploy-stage, destroy)
0256dc8  feat: phase 4 terraform foundation
```

GitHub configured: 6 ENVIRONMENT variables under environment `stage`, no secrets
(OIDC). Environment `stage` created; `prod` environment not yet created.

SSO login on the headless devbox: use `aws sso login --profile demo-admin
--use-device-code`. Identity confirmed: Account 993912191738.

---

### Phase 8 session 4 (2026-07-25) — planning + two structural findings

Ran in **Cowork on the MacBook**, not Claude Code on the devbox. Files were
produced locally and moved across with `scp`. Nothing was deployed; no AWS
resource was touched.

**Goal:** decide what happens to the application and to the project as a whole
now that the lifecycle is closed, and produce a real plan before writing more
code.

#### Decisions — recorded as ADR-0017

- **D1** prod lives in the SAME AWS account as stage, separated by state key,
  name prefix, deploy role, GitHub Environment and VPC. A separate member
  account is the stronger AWS Organizations story but was rejected on schedule
  cost — the finish line was already months out.
- **D2** hybrid availability: the dashboard is always on, every workload
  environment is on demand. The dashboard is **S3 (private) + CloudFront + OAC
  in AWS, not GitHub Pages** — hosting the showcase of an AWS project outside
  AWS demonstrates nothing. This forces a permanent state level
  `infra/public-site/`.
- **D2a** prod keeps NO data between cycles. `skip_final_snapshot = true`,
  `backup_retention_period = 0` are indefensible on a real production database,
  so the honest interview framing is **"a production-shaped environment with a
  promotion gate"**, not "production". Volunteer that; do not get caught by it.
- **D3** public HTTPS on an owned domain. `<domain>` → dashboard,
  `app.<domain>` → prod ALB. **The CloudFront certificate must be issued in
  us-east-1**; the ALB certificate stays regional in us-west-2.
- **D4** external access is phased: view-only first (Phase 11), authorised
  self-service launch last (Phase 19), with mandatory guardrails.

Rejected and recorded: always-on prod (~$40–60/month against a $20 alarm, and it
would make the project's own cost-control claim false); prod on the Lightsail
devbox; GitHub Pages; a second member account for now.

#### Ordering changed mid-session

The session began with a documentation-first recommendation. Once the stated
priority became "fastest path to a shareable MVP", the order was rebuilt
prod-first: prod is the only genuinely missing half of the cycle and the
riskiest work, so it goes while the context is fresh. Documentation was cut to
README + architecture + demo-script (Phase 12) with the rest deferred to
Phase 18.

#### Finding 1 — the control layer had never been committed

`CLAUDE.md`, `.claude/skills/` (9 skills + registry), `docs/sessions/`,
`docs/skills-structure.md`, `docs/project-instructions-pointer.md` and
`docs/decisions/0000-template.md` existed **only** in a non-git folder on the
MacBook (`~/Projects/aws-devops-sdet-demo`), created 2026-06-06. The repo had
93 tracked files and none of them.

Consequence: Claude Code on the devbox had been starting with **no anchor file
and no skills for seven weeks**, while `CLAUDE.md` — the file asserting that
GitHub is the source of truth — sat outside the source of truth.

Found by accident. A verification command intended for the MacBook was pasted
into the devbox session; the resulting `find` dump of the home directory
exposed what the repo did and did not contain.

Fixed in `f8f32e5` (18 files, 93 → 111 tracked). The June `README.md` was
deliberately NOT committed: it claims "pre-devbox scaffold, app/infra built
later", which contradicts reality. It is rewritten in Phase 12.

#### Finding 2 — `infra/envs/prod` is a stale scaffold that contradicts two ADRs

It exists in git (6 files, Phase 4 mirror of stage, never applied,
`desired_count = 0`) and was never updated by the C2 refactor:

```text
- still contains module "iam_github_oidc" → the exact construct ADR-0015
  removed from stage because destroy deletes its own permissions mid-run
- passes db_secret_arn where the post-C2 module takes db_secret_arn_pattern
  → this directory cannot plan against the current modules AT ALL
- no depends_on = [module.alb] on ecs (2c4162b went to stage only)
  → the ADR-0016 ENI/IGW teardown race is built in from birth
- declares its own ECR repo (…-app-prod) → conflicts with promotion-by-digest;
  decide one shared ECR vs cross-repo image copy BEFORE promote-prod.yml
- destroy.yml offers "prod" in its dropdown with nothing behind it
```

The second bullet is the serious one: **an entire IaC directory has been failing
to validate for seven weeks and CI never said so**, because `terraform validate`
does not cover the whole tree.

Phase 9 was therefore redefined to start with **9.0 — reconciliation, not
construction**.

#### New invariants adopted (now in `docs/next-phases.md`)

```text
- a fix to a SHARED invariant is applied to EVERY environment directory in the
  same commit, not only to the one currently being exercised
- CI validates EVERY IaC directory; an unvalidated directory rots invisibly
- "GitHub is the source of truth" is a claim to VERIFY, not to assume
```

Both findings have the same shape as the infrastructure bugs this project
already documents: something looked finished, was never exercised on the path
that would expose it, and stayed broken until an accident surfaced it.

---

### Phase 8 session 3 (2026-07-25) — verification cycle DONE ✅

Goal: run the C2 verification cycle that session 2 left open. Result: closed, but
only after three further latent bugs were found and fixed. **C2 itself was sound —
no self-deletion of permissions occurred in any run this session.**

**Proof of completion:**
- `deploy-stage #18` green (14m23s) from a fully destroyed account.
- `destroy #7` green END-TO-END (8m21s), including the "no billable resources
  remain" verification step. First time destroy.yml ever completed on Actions.
- Live demo verified between the two: `/health` 200, `/api/db-check` =
  `{"status":"ok","db":"connected"}`, ECS running 1/1, task def revision 9.

**Bug 1 (b71b846) — empty ECR_URL on a from-scratch cycle.**
`deploy-stage.yml` resolved `ecr_repository_url` via `terraform output -raw`
against an EMPTY stage state (ECR is created by the stage apply, which had not
run yet). `terraform output` failed, but `echo "ecr_url=$(...)"` swallowed the
error, so the step went GREEN with an empty value. `docker build` then got the
tag `":<sha>"` → `invalid reference format`.
Why it never appeared before: earlier green runs (#10, #12) ran on top of a
stage already applied locally, so the repository existed.
Fix: a targeted `terraform apply -target=module.ecr` before the build (keeps ECR
under Terraform management), plus `set -euo pipefail` and an explicit empty-check.

**Bug 2 (b110b41) — two independent teardown failures. See ADR-0016.**
- `iam:ListInstanceProfilesForRole` was dropped when C2 narrowed
  `IamManageScoped` to the two ECS roles. The AWS provider calls it while
  deleting ANY IAM role, so both ECS role deletions failed with AccessDenied.
- **No dependency edge exists between `module.alb` and the IGW.** Terraform
  destroys them CONCURRENTLY; the ALB's ENIs still held mapped public IPs →
  `DependencyViolation` on `DetachInternetGateway` after ~20 min of retries.
  Fix: a targeted `terraform destroy -target=module.alb` before the full
  destroy. A targeted destroy also removes dependents, so `module.ecs` goes
  first and its task ENIs are released too.

**Bug 3 (58ec209) — the guard could not verify its own invariant.**
`destroy.yml` asserts "no EKS in v0" via `aws eks list-clusters`, but the deploy
role had no `eks:ListClusters`. The teardown had already succeeded; the run went
red on the assertion. Fix: a read-only `TeardownVerifyRead` statement.

**Also fixed (6944229): `deploy-stage.yml` had `on: push: branches: [main]`.**
Every push to main deployed ALB + RDS + ECS. Three of that session's deploys were
unintended side effects of documentation commits. Now `workflow_dispatch` only.

**IMPORTANT correction to the Phase 7 analysis.** The destroy #3 failure on
`ec2:DetachInternetGateway` was recorded as a consequence of the deploy role
self-deleting its permissions. Session 3 reproduced the identical failure with
the role's permissions fully intact — so that failure was, at least in part, the
IGW/ALB ordering race of Bug 2, not permission loss. ADR-0015 remains valid:
self-deletion was real, proven separately, and separately fixed.

**Method note that paid off:** the race is NONDETERMINISTIC. A local
`terraform destroy` of the same graph succeeded, with IGW and ALB both reporting
"Destruction complete after 27s". A bug that sometimes passes is why this sat
undiagnosed for two months. Read the concurrency in the log, not just the error.

**Session gotchas:**
- Recovery from the failed Actions destroy was again a LOCAL `terraform destroy`
  under demo-admin. Same pattern as Phase 6/7.
- No stuck `.tflock` this time — the role kept S3 access throughout, itself
  evidence C2 worked.
- After a full teardown, `stage/terraform.tfstate` shrinks to ~182 bytes rather
  than disappearing. That is the expected empty-state marker.

### Phase 8 session 2 (C2 refactor — OIDC to its own bootstrap state)

Goal: make `destroy.yml` run fully end-to-end via Actions OIDC by removing the
self-deletion-of-permissions trap. Root cause (proven in session 1):
`module.iam_github_oidc` lived inside `infra/envs/stage`, so `terraform destroy`
under the deploy role deleted the role's own inline policy + the OIDC provider
mid-run.

**Decision recorded as ADR-0015.** Supersedes the OIDC-placement part of ADR-0014.

**Done (commit 5735430) — VERIFIED against AWS in session 3:**
- **New level `infra/bootstrap-oidc/`** with its own remote state, S3 backend
  `key = bootstrap-oidc/terraform.tfstate`.
- **Stage cleaned:** removed `module "iam_github_oidc"`, its output, and the
  `github_owner/repo/branch` variables. (Session 3 also removed the matching dead
  `TF_VAR_github_*` env from deploy-stage.yml — Terraform had been ignoring them.)
  **NOTE: `infra/envs/prod` was NOT cleaned — see session 4, finding 2.**
- **Module `iam_github_oidc` changed (two security improvements):**
  1. `db_secret_arn` → `db_secret_arn_pattern` (wildcard). The OIDC level is
     applied BEFORE stage exists, and the DB secret carries a per-cycle random
     suffix, so `GetSecretValue` must be scoped to
     `arn:...:secret:<name_prefix>-db-credentials-*`. The ECS execution role
     still uses the EXACT secret ARN — unchanged.
  2. `IamManageScoped` resources narrowed from `role/<name_prefix>-*` to exactly
     the two ECS roles. The old wildcard ALSO matched the deploy role itself,
     giving it `iam:DeleteRolePolicy` over itself — the deeper cause of
     self-deletion. (Session 3 caveat: narrowing the RESOURCES was right, but the
     ACTION list was left incomplete — see Bug 2.)
- **Reverted retry hack 8d3ed9d**: back to a plain `terraform destroy`.

### Phase 8 session 1 (repeatable lifecycle via CI) — context that led to C2

- **Node 24 actions bump (181cabd).** checkout v4→v5, setup-node v4→v5,
  setup-python v5→v6. Residual "Node.js 20 deprecated" warning is informational.
- **Repeatability-check — CLOSED ✅.** Two fresh applies of stage after a full
  destroy, each "34 added, 0 changed, 0 destroyed", no name conflicts.
- **deploy-stage.yml via Actions OIDC — green at #10, #12**, but on top of an
  already-applied stage. The from-scratch path was only proven in session 3.
- **gotcha: stage has NO `demo_account_id` variable.** Local apply -var set is
  `owner`, `state_bucket_name`, `budget_email`, `app_image` only.

### Phase 6 result (DONE — first AWS stage deploy)

All checks PASSED against AWS: `/health` 200 (no DB), `/api/health` ok (no DB),
`/api/db-check` connected; run-task migrate / seed / db-assert exit 0;
Playwright smoke against the ALB URL passed. No NAT, no EKS.

Resource naming (identifiers change every cycle):

```text
VPC + 2 public subnets (10.0.0.0/24, 10.0.1.0/24) + 2 private-db subnets
ALB      aws-devops-sdet-demo-stage-alb
ECS      cluster ...-stage-cluster, service ...-stage-app
RDS      aws-devops-sdet-demo-stage-db...rds.amazonaws.com:5432
secret   aws-devops-sdet-demo-stage-db-credentials-<suffix>
role     arn:aws:iam::993912191738:role/aws-devops-sdet-demo-stage-github-deploy
ECR      993912191738.dkr.ecr.us-west-2.amazonaws.com/aws-devops-sdet-demo-app
```

### Phase 6 learnings / gotchas (IMPORTANT, carry forward)

- **Run long applies under SSH-disconnect protection.** RDS takes ~5-10 min. A
  dropped apply got SIGHUP mid-create, leaving a stuck S3 lockfile + orphaned
  resources. Use `nohup ... &` + `tail -f`, or tmux.
- **Recovery pattern for an interrupted apply:** read the lock id from the
  `.tflock` JSON in S3, `terraform force-unlock <id>`, `terraform import` each
  orphan, `plan` until `0 to destroy`, then re-apply.
- **app_image has no real default.** Local apply MUST pass
  `-var="app_image=<ECR_URL>:<sha>"`.
- **DB-assert build-context bug (fixed, 36ecfba).** The image is built from
  context `./app` and does NOT contain `tests/`. `app/scripts/assert_seed.py`
  ships via `COPY scripts ./scripts`. `tests/db/assert_seed.py` remains the local
  `make test-db` gate vs compose.
- **CloudWatch log stream format** is `app/app/<task-id>`, NOT `ecs/app/<task-id>`.
- **Image build note:** buildkit produces an OCI manifest list; ECS Fargate
  pulled it fine.

### Phase 7 result (DONE — destroy validation, 2026-06-08)

Stage fully destroyed; AWS CLI verification all empty. State bucket intentionally
REMAINS. The teardown was completed via LOCAL `terraform destroy`, NOT via
destroy.yml end-to-end (that was achieved on 2026-07-25 — session 3). The first
destroy.yml run surfaced two latent deploy-role bugs:

1. **Trust policy missing the environment sub.** destroy.yml runs as
   `workflow_dispatch` with `environment: stage`, so GitHub sends
   `sub=repo:UVE-QA/aws-devops-sdet-demo:environment:stage`. Fix (2c1efcc):
   `github_environments` var, both sub forms concatenated.
2. **Permissions policy absent in AWS (state/AWS drift)** from the interrupted
   Phase 6 apply.

**Phase 7 learnings (carry forward):**
- **A `-target` apply does NOT reconcile the rest of the config.** Read the
  destroy plan itself; don't panic on an intermediate targeted-plan.
- **"has been deleted" in a refresh ≠ resource never existed.** Confirm against
  AWS CLI first.
- **Latent OIDC-role bugs only surface on the FIRST real run of a given path.**
  Expect this every time a path runs for the first time.

---

## Project shape

- Portfolio/demo platform for DevOps / Cloud / QA-SDET interviews. The app stays
  minimal; the value is the cloud delivery construction, IaC, CI/CD, test
  automation, security model, and budget-safe lifecycle.
- Phase-gated execution. No jumping ahead; each phase ends with summary +
  validation + STOP + explicit confirmation.
- All prompts/instructions/skills in English. Chat discussion may be Russian.

## Infrastructure decisions

- **Account model:** dedicated AWS Organizations member account. Never deploy
  workload into the management account. Human access via IAM Identity Center
  (profile `demo-admin`); GitHub access via OIDC. No static keys.
- **Region:** us-west-2. **Tag:** Project = aws-devops-sdet-demo (+ Owner=UVE).
- **MVP architecture:** single app container (FastAPI static HTML + API) →
  Browser → ALB → ECS Fargate → RDS PostgreSQL.
- **Terraform state levels.** Three exist today; **six** at the end of the MVP
  track. Levels marked NOT BUILT are decided, not implemented:

```text
1. infra/bootstrap       S3 state bucket. LOCAL state, applied once. Permanent.
2. infra/bootstrap-oidc  OIDC provider + deploy roles. S3 state. Permanent.
3. infra/shared-ecr      container registry. S3 state. Permanent.
                         NOT BUILT — ADR-0018, Phase 9.0.
4. infra/public-site     dashboard S3+CloudFront. S3 state. Permanent.
                         NOT BUILT — Phase 11.
5. infra/envs/stage      workload. Destroyed every cycle.
6. infra/envs/prod       workload. Destroyed every cycle. Stale scaffold until
                         Phase 9.0 reconciles it.
```

  Only levels 5 and 6 are ever destroyed. Anything that must survive a teardown
  — including the artifact that PROVES the teardown works — belongs above them.
  The registry qualifies and nobody noticed until prod needed to run an image
  that stage's own teardown would delete (ADR-0018).
- **Two chicken-and-egg bootstraps, both first run LOCALLY (demo-admin):** the
  state bucket, then the OIDC provider + deploy role.
- **Deploy-role IAM scope:** S3 on the state bucket + ECR/ECS/RDS/logs/secrets/
  EC2/budgets via `*` + `IamManageScoped` on EXACTLY the two ECS roles +
  `GetSecretValue` on `<name_prefix>-db-credentials-*` + `PassRole` on the ECS
  roles + read-only `GetOpenIDConnectProvider` + read-only `TeardownVerifyRead`.
  It deliberately has NO rights over its own role → cannot self-delete.
  **Lesson: when narrowing an IAM statement, narrow the RESOURCES, but re-derive
  the ACTION list from what the provider actually calls.**
- **DB password:** `random_password` (length 32) → Secrets Manager; ECS reads it
  via the task `secrets` block, never plaintext env, never in repo.
- **No-NAT egress:** Fargate task in a public subnet with a public IP reaches
  ECR/Secrets/Logs over the IGW. The cost of this choice is the ENI/IGW teardown
  ordering problem (ADR-0016).
- **Health checks:** `/health` and `/api/health` must NOT touch the DB;
  `/api/db-check` is the only DB endpoint. Otherwise ECS cannot reach steady
  state before the migrate task runs — a deadlock.
- **DB driver:** psycopg2-binary. **Postgres 16** pinned (compose == RDS).
- **Provider lockfile** committed for linux_amd64 + linux_arm64.

## Repeatable lifecycle (deploy → demo → destroy → repeat)

- **Survives every cycle:** the state bucket, `infra/bootstrap-oidc`, (from
  Phase 9.0) `infra/shared-ecr`, and (from Phase 11) `infra/public-site`.
- **Destroyed every cycle:** ECS/ALB/RDS/logs/VPC. ECR leaves this list in
  Phase 9.0 — see ADR-0018.
- Start of a cycle (LOCAL, demo-admin): `aws sso login --use-device-code` →
  apply `infra/bootstrap` → apply `infra/bootstrap-oidc` → (from Phase 9.0)
  apply `infra/shared-ecr` → then `deploy-stage.yml` via the Actions UI. The
  permanent levels are applied once per ACCOUNT, not once per cycle; a normal
  cycle finds them already there.
- End of a cycle: `destroy.yml` via the Actions UI, confirm = `DESTROY`.
- Idempotency fixes: ECR `force_delete = true` (becomes `false` once the
  registry moves to a permanent level — its only purpose was per-cycle teardown,
  ADR-0018); Secrets Manager
  `recovery_window_in_days = 0`; RDS `skip_final_snapshot = true` +
  `backup_retention_period = 0`; CloudWatch log group Terraform-managed.
- Safety nets: Budgets module (free), monthly limit $20, alerts at 50% ACTUAL /
  100% FORECASTED; `destroy.yml` ends with a verification step that exits
  non-zero if anything billable remains.

## CI/CD

- Workflows: `ci.yml`, `deploy-stage.yml`, `destroy.yml`. OIDC only.
  `promote-prod.yml` is added in Phase 9.
- CI is deterministic and AWS-free.
- One-off tasks (migrate/seed/db-assert) reuse the SAME ECS task definition via
  `aws ecs run-task` command overrides (ADR-0007): `["alembic","upgrade","head"]`,
  `["python","scripts/seed.py"]`, `["python","scripts/assert_seed.py"]`
  (NOTE: `scripts/`, not `tests/db/`).
- run-task network: public subnets + ECS app SG + assignPublicIp=ENABLED.

### Workflow status (current)

- **ci.yml**: `local-ci` reuses the Makefile targets; `terraform-checks` runs
  `terraform fmt -check -recursive` + `make tf-validate`. **Known gap: validate
  does not cover every IaC directory — `infra/envs/prod` was never checked.
  Fixed in Phase 9.0.**
- **deploy-stage.yml**: `workflow_dispatch` ONLY. `environment: stage`.
  Order: OIDC → ECR login → init → targeted apply of `module.ecr` → resolve
  `ecr_repository_url` (fails loudly if empty) → build/push by SHA → apply with
  `TF_VAR_app_image` → run-task migrate/seed/db-assert → Playwright smoke →
  artifact. Green from scratch at #18.
- **destroy.yml**: `workflow_dispatch` (environment + confirm). Guard fails
  unless confirm == DESTROY. Order: OIDC → init → targeted destroy of
  `module.alb` → full destroy → verification. Green end-to-end at #7 (8m21s).
  **Its `prod` dropdown choice is a placeholder with nothing behind it.**

### GitHub repo config (carry forward)

- 6 ENVIRONMENT variables under environment `stage`, no secrets:
  `AWS_REGION`, `OIDC_ROLE_ARN`, `TF_STATE_BUCKET`, `TF_VAR_BUDGET_EMAIL`,
  `TF_VAR_DEMO_ACCOUNT_ID`, `TF_VAR_OWNER`.
- GOTCHA: the variable is `OIDC_ROLE_ARN`, NOT `GITHUB_OIDC_ROLE_ARN` — GitHub
  reserves the `GITHUB_` prefix.
- Env-scoped vars are visible only to jobs with `environment:` set.
- The deploy role trust allows both `ref:refs/heads/main` and
  `environment:<name>` subs (`github_environments`, default ["stage"]).
- `gh` CLI is NOT installed on the devbox — run workflows via the GitHub UI.
- A `prod` GitHub Environment with required reviewers is created in Phase 9.

## Open debts / next steps

- **Phase 9.1 (build out prod)** is the immediate next action: a SECOND deploy
  role in `infra/bootstrap-oidc` (`name_prefix` is a scalar today), a `prod`
  GitHub Environment with required reviewers, `promote-prod.yml` promoting by
  DIGEST, and HTTPS. See ADR-0017, ADR-0018 and `docs/next-phases.md`.
- **`infra/shared-ecr` has never been applied.** It is applied locally under
  `demo-admin` once per account, BEFORE the first `deploy-stage.yml` run of a
  cycle. The workflow fails fast with an explicit message if it is absent.
- **Documentation debt, now scheduled rather than floating.** Still missing:
  README.md, docs/architecture.md, docs/demo-script.md (Phase 12);
  docs/cost-control.md, docs/interview-talking-points.md,
  docs/lightsail-devbox.md (Phase 18). Present: phase-gates.md,
  preflight-inventory.md, next-phases.md, decisions/0001–0017, sessions/.
- **`architecture.md` must be written against the SIX-level state model**
  (ADR-0018), not the three-level model of ADR-0015 — otherwise it is stale on
  arrival. This has now been revised twice before being written, which is the
  argument for writing it in Phase 12 and not earlier.
- **Skills freshness:** `tf-workflow` and `teardown` should mention the
  multi-level bootstrap and the targeted apply/destroy passes. Likely stale.
- **project-prompt.md** should reflect the repo shape after C2 (§7 repo
  structure, §10 bootstrap ordering) and note that **§14 is superseded by
  docs/next-phases.md**.
- **Repository visibility: public at Phase 11, not before (decided 2026-07-25).**
  Phase 11's dashboard reads run history from the PUBLIC GitHub API, so the repo
  must be public by then; a portfolio repo nobody can open is a contradiction
  anyway. Prerequisite: gitleaks over the FULL history plus a conscious decision
  about the account id, the devbox IP and the SSO start URL. Deferred rather
  than rejected — see docs/next-phases.md 11.0.
- **Deferred idea: a session-start skill that clones the repo into the chat
  sandbox** and reads CLAUDE.md / phase-gates.md / next-phases.md /
  discussion-log.md itself. Verified feasible: the Cowork sandbox reaches
  github.com over HTTPS (SSH out is blocked). Blocked only by the repo being
  private, since asking for a PAT is against the project's own rules. Unblocks
  itself at Phase 11. Its appeal is that the clone lives in the ephemeral
  sandbox, so it is NOT a second working copy on a laptop.
- **RESOLVED (1f50243 + ADR-0019): this file lives in git at
  `docs/discussion-log.md` and nowhere else.** The Claude Project mirror was
  retired on 2026-07-25 after being measured five commits stale. Load state from
  git, or from the devbox when the sandbox cannot clone.

## Collaboration / context model

- One working copy, on the Lightsail devbox (`ubuntu@34.213.147.86`,
  `~/aws-devops-sdet-demo`); laptops connect via SSH. GitHub is the source of
  truth. Don't sync repos via Dropbox/iCloud or scp between machines.
- **`~/Projects/aws-devops-sdet-demo` on the MacBook** is NOT a working copy.
  Session 4 recorded that everything unique in it had been committed. That was
  wrong: `docs/project-prompt.md` lived there and in the Claude Project and
  NOWHERE ELSE until `96e110c`, and it was nearly deleted on the strength of the
  earlier claim. Only `README.md` is now uncommitted, deliberately — the June
  version contradicts reality and is rewritten in Phase 12.
  Verify with `git ls-files` before treating anything there as redundant.
- **`~/Projects/_claude-transfer` on the MacBook** is the buffer for files
  produced in chat that still need to reach the devbox. It should be empty most
  of the time; anything sitting there is uncommitted. Contains `send.sh` and
  `README-TRANSFER.md`.
- SSH alias configured on the MacBook: `ssh devbox`, `scp file devbox:/tmp/`
  (`~/.ssh/config`, with `ServerAliveInterval 60`).
- Context in layers to save tokens: ADRs (always, the "why"), `phase-gates.md`
  (where we are), session summaries on demand.
- `CLAUDE.md` is the always-read anchor/router; skills load on demand. **Both are
  in git as of f8f32e5.**
- **No manual context sync (ADR-0019).** The Claude Project holds a pointer and
  no state. `discussion-log.md` and `project-prompt.md` are tracked files; the
  Project copies were exact duplicates and were deleted. A phase gate ends in
  git — cursor, session summary, ADRs, commit, push — and nothing outside the
  repository needs touching for the state to be correct.
  The ritual failed structurally, not through carelessness: a manual step gets
  skipped exactly when a session was long, which is when the next session most
  needs accurate context.

## Skills design

- Skills = operations (verbs); phases = state (phase-gates + CLAUDE.md).
- 9 skills: meta (session-protocol, phase-gate, skill-maintenance), infra
  (local-dev, tf-workflow, deploy-stage, teardown), product (app-dev, test-dev).
- The `description` is the trigger mechanism: rich trigger phrases (EN+RU) + an
  explicit "Do NOT use for" boundary naming the neighbour skill.
- app-dev → test-dev: any contract change must sync tests before the task is done.
- New skills added via `skill-maintenance`. ~9 is the comfortable ceiling.

## Deliberately out of scope

Recorded with reasons in `docs/next-phases.md`: EKS/Helm/ArgoCD, React/Vite,
Grafana/Prometheus/Loki, WAF and CloudFront in front of the app, the dashboard on
the devbox, private ECS subnets + NAT, blue/green and autoscaling, a second
workload member account, a general nightly-teardown backstop. Being able to
explain why something was NOT built is itself an interview asset.

## Tooling decisions

- **Claude Code on the devbox**, via VS Code Remote-SSH or bare SSH. Bare SSH
  from Terminal.app proved sufficient for operations-heavy sessions and avoids
  UI contention. **Cowork on the MacBook** was used for session 4 (planning and
  document production) — a reasonable split: Cowork for thinking and writing,
  Claude Code on the devbox for anything that touches the repo or AWS.
- Devbox tool versions: Docker 29.6.2, Compose v5.3.1, AWS CLI 2.34.63,
  Terraform 1.15.8, Node 20.20.2, Python 3.12.3, Git 2.43.0, Make 4.3.
- **Shell gotchas that cost time:** long heredocs get mangled over browser SSH
  (write long docs in short flat chunks and verify each); pasted example commands
  containing `...` will be run literally; `exit` typed into a `tail -f` does
  nothing — use Ctrl+C; typing at a `>` continuation prompt appends to the
  command you are already building (this cost one `scp` into `/tmp/clear`).
- **Prefer a checked-in patch script over a long interactive heredoc** for
  surgical edits to long docs: it fails loudly, changes nothing on mismatch, and
  is reviewable before it runs.
- `gh run view --log` returns nothing for some runs; the API path
  `repos/:owner/:repo/actions/jobs/<id>/logs` worked every time.
- The devbox clock is UTC, the GitHub UI renders PDT (-7). State times in UTC
  or the deadline you quote will be wrong by seven hours.
