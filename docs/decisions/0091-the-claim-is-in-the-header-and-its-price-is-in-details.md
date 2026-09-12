# ADR-0091: The claim is in the header, and what it costs is in Details

## Status
Accepted (Phase 40, 2026-09-12). Finishes what **ADR-0084** started and
**ADR-0082 D3** made necessary. Narrows **ADR-0085**: the fact now has two copies
rather than three, and the check that compares them is unchanged in kind.

## Context

ADR-0082 D3 moved the whole identity bar into `Details`, and named the cost: the
page stopped saying what it was above the fold. ADR-0084 bought one clause back —
`deploy → test → promote → destroy on AWS, reporting on itself`, a shortened
paraphrase sitting beside the name — and left the sentence it was a paraphrase of
in a paragraph three clicks away.

Two statements of one fact, one of them abridged. The owner, looking at the
identity bar in `Details`:

> эту строчку с текстом до "There is" перенести на самый верх в шапку для всех
> страниц

## Decision

**D1. The header carries the sentence itself, whole, on every part.**
*A deploy → test → promote → destroy pipeline on AWS, reporting on itself.* Not a
paraphrase of it — the paraphrase existed only because the row could not fit the
sentence, and the row is two rows now (ADR-0089 D6).

**D2. `Details` keeps what the claim COSTS to be true.** *There is no manual AWS
operation anywhere in that sentence, teardown included, and every state it leaves
is read back out of AWS afterwards rather than taken from the run that claimed
it…* — which is the half that was never going to fit above the fold, and the half
a reader wants only after the first has interested them.

`that sentence` is not a dangling reference: the header is on every part, four
lines above this paragraph wherever it is read. That is what makes the split
possible at all.

**D3. The chain has two copies, and the gate compares both.** README's opening
and the header clause. `check-claim-chain.py` loses the third source and nothing
else: it still refuses when a copy cannot be found, still refuses when a copy has
no chain in it, and still fails when they disagree. Removing a copy removes a way
for them to drift; it does not make the remaining two agree by themselves.

**D4. The ways out go with it.** `repository →`, `N decision records →`,
`Actions →` move to the right end of the same header line, opposite the name. They
were in the identity bar, which lives in `Details` — so the source of a page whose
whole argument is *go and check for yourself* was three clicks away from four of
the five parts. What this is at one end of the line, where to verify it at the
other, and the count of decision records still comes from `topology.json` rather
than from the markup.

**D5. And the badge.** `dashboard live` sits beside the name. It is the one
claim the page makes about ITSELF — that it is up while everything it reports on
is gone — and it was readable on one part in five.

## Consequences

- One fewer place to forget. ADR-0085's finding — a copy that dropped `approve`
  within an hour of being written — was about copies, and there are fewer now.
- The page states its claim above the fold on all five parts, which is what a
  stranger arriving from a CV link gets in the first second.
- `Details` opens mid-argument by design. Read on its own it is a paragraph about
  a sentence that is on the screen; read from the top of the page it is the
  second half of one thought.
- `Details` keeps the name and the paragraph. It is a smaller card than it was,
  and nothing that was on it is gone from the page.
- The header row now carries a full sentence at 1280px and below without
  wrapping, because the name has a line of its own since ADR-0089 D6. If it ever
  does wrap, the clause is the part that should give ground — and the way to make
  it do that is not `flex: 1 1 auto`, which ADR-0089 records the hard way.
