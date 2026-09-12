# ADR-0094: The plan is on the page, and cannot outlive the plan

## Status
Accepted (Phase 40, 2026-09-13). Adds an editorial band to `Details` beside
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

**D1. A band in `Details`: *What comes next*.** Five items in the order they
will be done, each with a title, what it is and why it is there. The heading
says what the band is: planned, none of it in `infra/`, the map draws none of
it. Drawn as a numbered list rather than as cards, because cards on this page
are for things that exist.

**D2. Editorial data, generated onto the page, and refused two ways.** The
items live in `assets/topology-groups.json` beside `outside` and
`request_path`, the other two things the map cannot derive from `infra/`.
`scripts/generate-topology.py` carries them into `topology.json` and refuses:

- a title that `docs/next-phases.md` does not contain - the plan document is
  where the decision lives and the page is its summary, so the summary cannot
  say something the plan does not (ADR-0085's shape: one fact, two copies, one
  check);
- an id that names a display group or a node the map already draws - an item
  that was built and never taken off the list.

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
