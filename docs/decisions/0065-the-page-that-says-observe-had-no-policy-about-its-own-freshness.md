# ADR-0065: The page that says "observed" had no policy about its own freshness

## Status
Accepted (Phase 31, 2026-09-05). Extends **ADR-0044**, which made one missing
line in `scripts/publish-site.sh` a checked fact rather than a remembered one.
This is the second such line in the same command, found the same way — by
watching what the published page actually did.

## Context

`scripts/publish-status.sh` writes the documents a CYCLE produces — the
environment status files, the timelines, the folded results — and has always set
`cache-control: no-cache, max-age=0` on them. `scripts/publish-site.sh` writes
the page itself and set no cache metadata at all.

So the live bucket held two classes of object:

```text
/status/stage.json      cache-control: no-cache, max-age=0   the cycle's documents
/                       (none)                               the page
/data/topology.json     (none)                               the page's own data
```

An object with no `Cache-Control` is not uncached. It is HEURISTICALLY cached:
a browser is free to guess a freshness lifetime, and the common guess is a
fraction of the document's age. The page published on 2026-08-12 was 24 days old
on the day this was found, which buys a returning visitor's browser roughly two
days of serving a copy that a new publish has already replaced.

The CloudFront invalidation at the end of the same script does not touch that.
It empties the edge; it says nothing to a cache that already holds a copy.

**Observed rather than reasoned about.** On 2026-09-05, minutes after a publish
whose invalidation had completed, a browser tab rendered the previous page —
old header, `64 decision records` — while `curl` against the same URL in the
same minute returned the new one. A hard reload fixed it, which is exactly the
signature of heuristic freshness and not of a stale edge.

The finding is not the two days. It is which document had no policy: the page
whose entire argument is that state should be observed rather than assumed was
the one making no claim about whether what you were reading was current.

## Decision

### D1 — the sync sets `no-cache`, on the page and on its data together

`--cache-control "no-cache"` on the `aws s3 sync` in `scripts/publish-site.sh`.

`no-cache` does not mean "do not store". It means revalidate before use, and S3
already sends an ETag, so the cost is a conditional request answered with 304 —
the same policy the cycle's own documents have carried since they existed.

It covers `index.html` and `data/` together and not `index.html` alone. The page
renders its counts out of `data/topology.json`; a page that revalidates beside a
data file that does not is two documents free to disagree about one page, which
is a quieter defect than the stale page and harder to see.

Nothing needs a migration step. In CI the checkout is fresh, so every local file
is newer than its S3 object and the sync re-uploads all of them with the new
metadata on the next publish.

### D2 — a change to the publish script publishes

`publish-site.yml` fired on `site/**` and on itself, and not on
`scripts/publish-site.sh` — the file that decides what is uploaded and with what
metadata. A change to it sat unpublished until something else happened to touch
`site/`.

That is the same shape as the missing `--exclude` line ADR-0044 exists for: a
publish path that does not fire on a change to the publish path. The path filter
gains the script.

## Consequences

- Every visitor's browser now makes one conditional request for the page and for
  each file under `data/` per load. Four 304s against a page that already fetches
  the GitHub API and five bucket documents on a timer; it does not move the
  anonymous budget, which is spent on `api.github.com` and not here.
- `--cache-control` applies to what the sync UPLOADS. The reasoning above says
  why that is enough in CI and not in general: a publish run from a machine whose
  `site/` is older than the bucket would skip files and leave them bare. Nothing
  checks this, and no gate is added for it here — `publish-prefixes-check` reads
  prefixes, not metadata. Named rather than assumed away.
- The stale copies already in visitors' browsers are not reachable by this or by
  any other change. They expire on their own schedule.
- Two documents in this repository now assert the page's freshness policy: this
  ADR and the comment in the script. The comment says why, and there is still no
  check that says whether — unlike the prefixes, which have one.
