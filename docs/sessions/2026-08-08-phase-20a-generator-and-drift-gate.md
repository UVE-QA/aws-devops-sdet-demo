# 2026-08-08 — Phase 20a: the generator, and the gate that holds it to infra/

The layout pilot earlier today decided what `topology.json` must carry and left
the file a hand-built fixture. This session replaced the fixture with
`scripts/generate-topology.py`, added `make site-data-check` to `ci.yml`, and
broke the gate five ways on purpose. Then, on review, added the band the map was
missing — the Lightsail devbox and GitHub Actions, neither of which is in
`infra/` — and put the front page's prose under a cut, GENERATED from the same
file rather than kept as prose. `site/index.html` was deliberately not touched;
that is the last piece of 20a.

Nothing was applied to AWS. No AWS API was called. **$0.**

## The generator refused on its first run, and was right

Before a single break test was planted, against unmodified `infra/`:

```text
site-data: REFUSED
infra/dns/main.tf: resource aws_route53_record.validation uses `for_each`.
One block would be counted as one resource and it is not.
```

Nine resource blocks carry `count` or `for_each`. The fixture had counted each
of them as one, so its headline number — "116 resources in `infra/`" — was not
the number of things AWS creates and never had been. The honest repair is not a
better guess but a change of unit: **every count now says resource BLOCKS**, the
nine are acknowledged one by one in the editorial file with the reason each
repeats, and the gate is red on a tenth that appears without an entry. The page
says the same thing in the same breath as the number:

```text
Blocks, not objects: 9 of them carry count or for_each and stand for a number
that depends on variables.
```

The nine split three ways: four `for_each` over certificate validation domains
and over the apex and www names, two `count 0 or 1` — an HTTPS listener with no
certificate and a budget a variable turns off — and three `count = 2`, the public
subnets, the private-DB subnets and the route-table associations, which the
fixture had drawn as one each.

## The check that measured its own regex, again

The first version of the repetition check reported five, and two were wrong:

```text
unacknowledged repetition: infra/modules/alb::aws_security_group.alb
unacknowledged repetition: infra/modules/alb::aws_lb_listener.http
```

Neither repeats. Both contain `for_each` four spaces in, inside a
`dynamic "ingress"` block, and the check was anchored on indentation rather than
on nesting. This is **Phase 19g's finding arriving again, in a different file,
in a session that had read it that morning** — there the adoption map read the
same ALB security group as indexed for exactly the same reason. A regex over
indentation is a claim about formatting; the question is about depth. Replaced
with a brace walk, after which the three real ones in `modules/network` survived
and the two false positives went away.

Worth stating plainly, because the pattern is now three sessions old: reading a
documented trap does not make you avoid it. Measuring does.

## What is derived, and what is deliberately not

```text
derived    the state levels, the modules each instantiates, every resource
           block and which level owns it, spec files per suite, workflows,
           ADRs, every count on the page
editorial  assets/topology-groups.json - which display group each resource
           block belongs to, and how groups fold into phases. It says so in
           its first field, and holds no number
absent     duration, cost, identifier, test result. A cycle says those; the
           repository does not know them, and writing them here is the defect
           the phase exists to remove. 20b and 20c fill them
```

So the map now renders entirely unobserved, and says so in three places rather
than showing plausible numbers. That is a visible regression in the exhibit and
the right one: the fixture's figures were placeholders that read as measurements.

## The gate

`make site-data-check`, in `ci.yml` beside `docs-check`. It is a **coverage**
gate, not a depiction one — it cannot tell whether the picture is a good
picture. Five ways to make it red, all exercised, every exit code written to a
file rather than read off a pipe, and the tree committed before anything was
broken. Full output in `docs/sessions/2026-08-08-phase-20a-break-tests.log`.

```text
1  a resource block added to a module and assigned to nothing
2  the generated file deleted
3  a count edited by hand in the committed file - the 2026-08-08 defect,
   planted: "adrs": 40 changed to 27, which is the number docs/demo-script.md
   was carrying that morning
4  an assigned resource deleted from a module - a stale assignment
5  a node removed from a phase while its module is still instantiated
```

Baseline green before, green after. The two the plan asked for are 1 and 2; the
other three exist because each names a way the map could go quietly wrong that
neither of those two would catch.

A sixth path is green and recorded rather than red: a group that means
**deliberately not shown**. There is one, and its member is
`aws_default_security_group`, which creates nothing — the network module's own
comment says AWS makes that group with the VPC and cannot delete it, and
Terraform adopts it to empty its rules. Drawing it beside resources that ARE
created would be a claim about creation the code contradicts. The gate skips
hidden groups when it asks "is this drawn?", and break test 5 is what proves
that skip is not blanket.

## The map printed `undefineds`, and only a screenshot said so

The node's CSS class defaulted a missing `state` to `absent`; the node's BODY
branched on the raw field. Every node in a generated file — none of which
carries a state until 20b — took the absent class and the measured body, and
rendered `undefineds` where the seconds go. One default now serves both.

Nothing in the JSON was wrong. No check in this repository would have said
anything, and the four-viewport render is the only reason it was seen at the
same time as the change that caused it. Two smaller things came out of the same
screenshot: an unobserved node now says what it is MADE of, which the repository
does know — "6 resource blocks — no observation yet" — and the paragraph
explaining that bar length is approximate and the seconds beside it exact is
hidden while there are neither.

Rendered through Playwright with real viewports at 1440 / 1180 / 834 / 390, not
a raw headless `--window-size`, for the reason the pilot recorded this morning.
`scrollWidth == clientWidth` at all four; 26 phase nodes across 8 phases plus 6
permanent cards, 32 in all; 4 serpentine rows at 1440 and 1180, 7 at 834, 8 at 390.

## Delivered

```text
scripts/generate-topology.py       the generator and the gate, one file, --check
assets/topology-groups.json        the editorial half: grouping, phases, the
                                   nine acknowledged repetitions
site/data/topology.json            now GENERATED; the header says so
Makefile                           site-data, site-data-check
.github/workflows/ci.yml           the gate, in terraform-checks
assets/map-pilot.template.html     the state default, the made-of line, the
                                   hidden bar-length note
site/map-pilot.html                rebuilt by make site-pilot
docs/sessions/…-break-tests.log    five planted refusals and the one that
                                   fired for real, exit codes from a file
```

One thing fixed in passing: the `site-pilot` comment in the Makefile named
`site/map-pilot.template.html`, a path that does not exist — the template is in
`assets/`. `make docs-check` reads documents, not the Makefile, which is why it
had survived.

## Asked for in review: the band, and the text under a cut

Two things a visitor could not see, raised after the first patch and built as a
second one.

**The devbox and GitHub were nowhere on the map.** Neither is in `infra/`, which
is exactly why neither had appeared: the map is generated from `infra/`. They are
not a phase of the cycle either — nothing creates or destroys them — so they got
a band ABOVE it, `outside`, with two cards and a caption. The GitHub card makes a
claim about the trust path, so the claim is tied to a resource: `backed_by` names
`aws_iam_openid_connect_provider.github`, and the generator is red if that
resource is not declared. A card that says "GitHub reaches this account through
OIDC" now stops being printable the moment the provider is deleted.

`Lightsail` is the awkward one and is left visibly so. It IS an AWS service, but
its official icon is not among the seventeen this page inlines, and inventing a
mark or recolouring another would break the single rule
`assets/aws-icons/NOTICE.md` makes. It carries a project glyph until the icon can
be taken from AWS's package on the devbox — recorded as open in
`docs/next-phases.md`.

**The prose is generated, not hidden.** The front page's hand-written "What
happens, in the order it happens" is the text this asked to keep. Keeping it as
prose would have preserved the class of defect the whole phase exists to end —
its "five permanent state levels" is where this started. So the cut renders from
`topology.json` (ADR-0039 D1), and the generator now emits `members`: the exact
Terraform address of every resource behind every node. The map folds 116 blocks
into 26 marks because 26 fit on a screen; the cut is where the other 90 are named
one by one. Only judgements stay hand-written — "the exhibit cannot be destroyed
by the thing it exhibits" is not a fact about state — along with the links.

## Three measurements, and one of them dates a defect to before this session

```text
phone, cut OPEN   a terraform address is one unbroken token, and `dt` and `dd`
                  carried them. 103px wider than a 390 viewport. With the cut
                  SHUT the page fitted and said nothing - the first wrap fix
                  covered `dd` only, and the second measurement found `dt`
scrollbar         opening the cut made the page taller, the scrollbar appeared,
                  the viewport narrowed - and the map had been laid out against
                  the wider one. `scrollbar-gutter: stable`, plus a re-render on
                  toggle. The layout must not depend on how much text below it
                  happens to be expanded
.node .head       up to 22px WIDER THAN ITS OWN NODE, at every width, with the
                  cut shut, and on the pre-patch build measured by stashing this
                  one. Not introduced here
```

That third one is the finding worth carrying. The layout pilot recorded
`scrollWidth == clientWidth` at all four widths and it was true — of the
DOCUMENT. Nothing spills past the page edge; the head content spills into the
node's own padding and the gap beside it, which is invisible in a screenshot and
invisible to the measure that was taken. A green measurement of the wrong
quantity is the same shape as the empty result that looks clean.

Deliberately NOT fixed here. `.node .head` is layout, and this project decides
layout by looking at it rather than by reasoning about it — that is what 20a's
first half was for. It goes to the session that next has the map on a screen.

Document width now fits at 1440 / 1180 / 834 / 390 with the cut both shut and
open, measured in both states rather than one.

## Not done, and not claimed

Folding the map into `site/index.html` in place of the hand-written "What
happens, in the order it happens" section, and the prose rendering generated
from the same JSON (ADR-0039 D1). Agreed at the start of the session: the
smaller surface, and one publish rather than two. 20a stays open on that half.
