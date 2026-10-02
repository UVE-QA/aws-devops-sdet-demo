# ADR-0104: Who looked

## Status
Accepted (2026-10-02). Adds a logs bucket and access logging to the permanent
level `infra/public-site` (**ADR-0027**); changes nothing the page shows.

## Context

The owner: *как можно организовать проверку просмотра сайта кем-либо - если
кто-то просто заходил и не нажал кнопку; простой лог без заморочек, но чтобы
было понятно, сколько уникальных юзеров и примерно откуда.* A press of the
button leaves a record in the control table and in the run history; a visit
left none. Three ways were weighed with the owner: CloudFront's built-in
viewer reports (nothing to build, but requests and not visitors, and an open
page polls once a minute); CloudFront's access logs and a script; a
third-party analytics script on the page (uniques and countries at once, but
visitors' data to a third party and the page's first runtime dependency).
The owner chose the second, and the first way to read it.

## Decision

**D1. CloudFront's standard access logs, in a bucket of their own.** Private,
SSE-S3, public access blocked, every object expired after 90 days, no cookies.
ACLs stay enabled on this bucket alone, because standard logging writes through
them; Checkov's two findings about that are skipped inline with the reason, and
its third - aborting failed uploads - was taken.

**D2. Read on the devbox, on request.** `make visitors` (`DAYS=7` by default)
syncs the logs into a local cache and prints visitors per day, page views, the
edge that answered, the referring site and the device. A page view is a GET of
the page itself, not a status poll; a visitor is an address with a browser; the
place is CloudFront's edge, near the visitor and not the visitor, and with
PriceClass_100 a visitor from outside North America, Europe and Israel appears
at the nearest of those. Crawlers and this repository's own headless checks are
left out. Nothing the script prints holds an address.

**D3. Not on the page.** A small number on a public exhibit works against it,
and the logs hold addresses; the counts stay with the owner. A weekly summary
by mail - a scheduled Lambda and an SNS topic - is the next step if asking
proves inconvenient.

## Consequences

- Logs arrive with CloudFront's delay, up to an hour or so; the first report
  can only count what came after the apply on 2026-10-02.
- The plan showed the publish role's policy and the site bucket's policy as
  changing, because their documents name the distribution and Terraform defers
  reading them while the distribution changes. They were read from AWS before
  and after the apply and are identical; Terraform's own count was one change.
- The bucket is permanent and costs cents. The data in it is personal - IP
  addresses - and is kept 90 days and read by nothing but the script.
