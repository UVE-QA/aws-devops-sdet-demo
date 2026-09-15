# ADR-0094: The plan is on the page, and cannot outlive the plan

## Status
Accepted (Phase 40, 2026-09-13). **D1 and D2 closed 2026-09-15 (Phase 47,
ADR-0101 D7)**: the plan's last item was done and the owner's word on the
empty band was *убрать блок совсем* - the band, its data and its refusals
left the page; D3, the plan itself, stands in `docs/next-phases.md` as
history, every item marked done. Adds an editorial band to `Details` beside
**ADR-0047**'s *outside the cycle*, under **ADR-0085**'s rule for editorial
text with two copies. Records, as a decision, the plan the owner set on
2026-09-12; the plan itself is in `docs/next-phases.md`.

## Context

The owner, after two conversations - one about a Kubernetes runtime, one about
where the application goes from here:

> добавь новый блок в детали с планируемыми изменениями

The page has always answered *what is this* and *what is it doing*. A reader who
has followed it that far asks *and then what*, and until now the honest answer
was silence, because the plan lived in a document the page never showed. Two
kinds of reader want it: the recruiter, who is reading the page as a claim about
its author, and the author in three months, who will want the order he chose
and the reason for it.

The risk with a plan on a page is the one this repository was built against:
prose that outlives its premise. A roadmap item that gets built and never
taken off the list is the same defect as *seven state levels* was on
2026-08-08 - precision that reads as truth after it has stopped being it.

## Decision

**D1. A band in `Details`: *What comes next*.** The additional services the
plan brings - `web`, `api`, the queue, the worker, the lab cluster, the worker's
own schema - drawn as greyed tiles in the board's own vocabulary, each naming
the step it arrives in. Written first as a numbered list of the five steps,
on the argument that cards are for things that exist; the owner chose the
tiles - *набор значков доп сервисов, пока обесцвеченных* - and he is right
about what the vocabulary means: `absent` is already what this page draws for
a noun a cycle has not reached, and a planned service is exactly that. The
heading says what the band is: planned, none of it in `infra/`, the map draws
none of it. The five steps stay in the data as the tiles' order and their
reasons, and are what the plan document is checked against.

**D2. Editorial data, generated onto the page, and refused two ways.** The
items live in `assets/topology-groups.json` beside `outside` and
`request_path`, the other two things the map cannot derive from `infra/`.
`scripts/generate-topology.py` carries them into `topology.json` and refuses:

- a title that `docs/next-phases.md` does not contain - the plan document is
  where the decision lives and the page is its summary, so the summary cannot
  say something the plan does not (ADR-0085's shape: one fact, two copies, one
  check);
- an id that names a display group or a node the map already draws - an item
  that was built and never taken off the list;
- a tile whose step is not an item of the plan, or a plan with items and no
  tiles.

`sqs` and `eks` are Architecture Icons from the same release the other
eighteen came from (`Icon-package_07312026`, the `48` set, unmodified), taken
with the owner's word on the download. They carried a project glyph for one
commit.

**D3. The plan itself, in `docs/next-phases.md`,** in the order the owner
chose after the reasons were argued:

1. split the container into `web` and `api`, a release becoming a set of
   digests;
2. a queue and a worker, with a dead-letter queue;
3. the same digests on EKS - Terraform for the cluster and the platform, Helm
   for the application, a lab environment beside stage and prod, the same
   button - and only after 1 or 2, because on one container it shows what ECS
   already shows;
4. each service owns its data, with contract tests between them;
5. a services manifest, so the machinery becomes a blueprint.

The out-of-scope list is reconciled in the same commit: EKS moves from *out*
to *item 3, reversed by the owner with the cost accepted*; Argo CD and Flux stay
out, with the reason.

## Consequences

- The page makes a promise now, and the generator holds it to the plan
  document. Building an item means editing three places - the code, the plan,
  the list - and forgetting the third is a red `site-data-check`, not a stale
  page.
- The band is the first thing in `Details` about the future. Everything above
  it is about the present or the past, and the heading keeps that line
  visible: *planned, in this order; none of it is in `infra/` yet*.
- `ci.yml` now runs on `next` as well as `main` (ADR-0093's branch, one commit
  earlier than this one): the work is on `next`, and the gates have to run
  where the work is. Nothing in `ci.yml` publishes or touches AWS, so a branch
  run costs a runner and nothing else; `publish-site.yml` stays on `main`.
- **Closed 2026-09-15.** The band could not outlive the plan, and it did
  not: with item 6 done the generator would have refused an empty plan as
  an invented one, and the owner chose removal over a band that says
  *done*. What remains of this decision is the rule it proved - a page
  statement about the future is editorial data with a check against the
  document that owns it - and the plan document, which is where a reader
  asking *and then what?* is sent now.
