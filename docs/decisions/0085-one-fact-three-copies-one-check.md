# ADR-0085: One fact, three copies, one check

## Status
Accepted (Phase 39, 2026-09-10). Closes what **ADR-0084**'s Consequences named
and did not fix.

## Context

ADR-0084 put a clause of the claim beside the name on the parts row, and wrote
down what that made true:

> This is the third statement of the same fact on one page: the row's clause, the
> paragraph in `Details`, and the README's opening that both come from. They agree
> today because two of them were copied from the third. **Nothing checks that they
> still agree**, and a fourth copy would be one too many.

That is this repository's `docker compose config --images` shape, which it has
paid for twice: one definition, two hosts, agreeing right up until the moment
they do not.

**The check found a disagreement on its first run, an hour old.** The row clause
had been shortened to save a word and had dropped `approve`:

    README.md opening            deploy -> test -> approve -> promote -> destroy
    the claim paragraph          deploy -> test -> approve -> promote -> destroy
    the clause beside the name   deploy -> test ->            promote -> destroy

`approve` is the only step in that chain that involves a person, the page draws
it as a phase of its own — *a human, in the prod environment* — and the row named
four verbs where the map below draws five.

## Decision

**D1. The verb chain is compared, not the sentence.** The three are not meant to
be identical and never were: the README's opening runs on into *and then deletes
almost all of itself*, the paragraph into *there is no manual AWS operation
anywhere in that sentence*, and the row carries one clause because a row is one
line. What they must share is `deploy → test → approve → promote → destroy` —
the shape of the pipeline, and the thing the map draws as phases.

**D2. A copy with no chain is refused, not ignored.** With one of the three
silent, a checker that compared only what it found would report agreement between
the other two. That is the empty result that looks clean, which this repository
keeps finding in its own instruments.

**D3. A copy the check cannot find is refused too.** The gate locates the two
page copies by `<p class="claim">` and `<span class="ident-what">`. Rename either
and the gate would have nothing to read; it says so instead of passing.

**D4. Arrows are normalised before comparison, never the words.** `->` in
Markdown, `&rarr;` in the template, `→` once unescaped — three spellings of one
character, and comparing them raw would fail for a reason that is not about the
claim.

## Consequences

`scripts/break-claim-chain.sh`, six variants, all behaving as written:

    [A] control                                       agree
    [B] the README gains a step the page lacks        caught
    [C] the row loses a step                          caught  ← the real defect
    [D] a copy loses its chain entirely               refused, not ignored
    [E] the markup the gate reads is renamed          refused, not dropped
    [F] control again                                 agree

**The row is one line to 1440 now, not 1366.** Restoring `approve` costs about
80px, so the wrap threshold moved. The page caps itself at 1512 and the owner's
screen is 1512, so the line holds where it is read; below 1440 it wraps to two,
which is 52px and not a defect.

**A fourth copy is now cheap to add and would be checked.** `project-prompt.md`
and several ADRs state the chain in prose. They are not in the gate, because a
gate over every sentence that mentions the pipeline would be a gate over English
rather than over a fact. The three that carry it as a CHAIN — an arrow list a
reader parses as a sequence — are the ones that can drift silently.
