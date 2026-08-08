# AWS Architecture Icons — provenance and the position taken

The SVG files in this directory are unmodified members of the **AWS Architecture
Icons** asset package, release `Icon-package_07312026` (Q3 2026), downloaded from
<https://aws.amazon.com/architecture/icons/>, all taken from its `48` set so they
share one viewBox. They are renamed to the service key the page uses (`rds.svg`,
`elb.svg`, …) and nothing else about them is changed.

How many there are is deliberately not written here. It was — "these seventeen
SVG files" — and it went stale the first time one was added, which is the exact
defect Phase 20 exists to end, in the file explaining why the icons are safe to
use. `scripts/build-icon-sprite.py` prints the count from the directory it just
read, and that number is measured rather than remembered.

## What AWS actually says

Established in Phase 20a by reading AWS's own pages, because ADR-0039 required
this question be answered from the vendor's terms rather than guessed:

```text
aws.amazon.com/architecture/icons
  "We allow customers and partners to use these toolkits and assets to create
   architecture diagrams."
  "You can also put icons in materials like whitepapers, presentations, data
   sheets, and posters."
  No terms-of-use or licence document specific to the package is linked from
  the page. The words "website" and "web page" do not appear on it.

aws.amazon.com/trademark-guidelines
  No blanket permission to display AWS marks publicly outside the authorised
  cases (Powered by AWS, partner badges). Marks may not be altered, must have
  reasonable spacing, may not imply sponsorship or endorsement, and may not be
  shown larger than the publisher's own branding.

aws.amazon.com/terms  (the only legal document the icons page's footer links to)
  "may not be reproduced, duplicated, copied ... or otherwise exploited for any
   commercial purpose without express written consent"
```

None of the three names a public web page — neither permitting it nor excluding
it. ADR-0039 predicted exactly this ("neither named nor excluded") and required
that the finding be recorded rather than resolved by assumption.

## The position taken

A decision, in the absence of a "no" — **not** a permission granted by AWS, and
this file exists so that distinction survives longer than the conversation that
made it.

```text
use            architecture diagrams of this project's own infrastructure, on a
               non-commercial portfolio and teaching page
unmodified     no recolouring, reproportioning or cropping. scripts/build-icon-
               sprite.py namespaces internal element ids and touches nothing else
not AWS        a test suite, a human approval and a teardown are not AWS
               services and carry project glyphs, never an AWS mark
no endorsement the page claims no affiliation with, or endorsement by, AWS
```

The honest caveat, recorded rather than argued away: the page also serves as a
portfolio in a job search, and a lawyer need not agree that this is
"non-commercial".

If AWS's terms are ever clarified against this reading, the remedy is one commit —
the icons live in this one directory and are referenced through a single sprite
builder.

Amazon Web Services, AWS and the AWS marks are trademarks of Amazon.com, Inc. or
its affiliates.
