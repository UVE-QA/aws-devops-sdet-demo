# page-tense fixtures

One JSON file per sentence the page is not allowed to get wrong about WHEN its
figures are true. Each file is a description and a list of calls into the
`PAGE TENSE` block lifted out of `site/index.html` by
`scripts/check-page-tense.mjs`.

```text
{
  "description": "why this case exists, in the words the finding was written in",
  "checks": [ { "fn": "...", "args": [ ... ], "expect": ... } ]
}
```

The inputs are hand-written, small, and NOT slices of a real observation: the
functions under test take three fields between them, and a fixture carrying the
other four hundred would date this directory rather than the code.

Three of these cases exist because a live cycle on 2026-08-09 (Phase 20h) was
watched saying the opposite. The rest are the controls around them - the states
that must NOT change, without which a fix that greys the whole map would pass.
