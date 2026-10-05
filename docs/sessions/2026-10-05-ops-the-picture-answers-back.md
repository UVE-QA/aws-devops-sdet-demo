# Ops — the picture answers back

**2026-10-05**, on `next`, then `main`.

The owner asked whether the application's picture is static. It was: one
generated SVG and a list of ten steps that did not know about each other. Four
ways to make it answer were offered - steps tied to arrows, one request
followed through, a card per box, live queue depths - and the owner chose the
first three.

The generator now marks what belongs to what: each box sits in a group named by
its key, each arrow carries its id, each numbered marker is a button, and the
data beside the picture says which arrows and boxes a step lights and what each
card holds. The cards are read from the same sources as the picture - the
manifest, the event contracts, the models (or the migration where there is no
model) - and link to the line on GitHub that defines the thing. The page's
script only lights and opens; it knows no geometry. Keyboard and reduced
motion included.

Checked in a browser on both themes and at 390 px: two layout faults found and
fixed (the card's rows fought the Details list styles; the caption split into
columns on a phone). Gates 33/33 on the devbox once a stale local web image was
rebuilt. Pushed to `next` on the owner's yes; the first CI run lost two jobs to
a GitHub Actions incident and passed on the rerun. Merged on *да, вливай*;
publish-site green, the live page identical to the build, clicked through.

Then the owner: a picture behind a cut in Details is one strangers may never
reach. The header got a link to it - *How the application works* - drawn as the
one thing in its row to press, on every part; it opens Details with the cut
open and the picture at the top, and an address ending in `#app-flow-cut` does
the same, for a link from a CV.
