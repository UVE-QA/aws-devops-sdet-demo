# ADR-0102: The name and the statement

## Status
Accepted (2026-09-15, after Phase 47). Amends **ADR-0082 D3** and
**ADR-0091** only in what the identity line says; keeps every name in AWS
exactly where **ADR-0018**, **ADR-0029** and **ADR-0035** put it.

## Context

The plan of 2026-09-12 is done (ADR-0101 D7), and the owner looked at the
name:

> so what you thinking about rename project to something like
> aws-platform-demo to avoid pointed to sdet or devops

`aws-devops-sdet-demo` names two roles. What the repository shows by now -
three services on two runtimes, a manifest the pipeline, the estate and
the page derive from, an observed teardown, the gates - is platform work,
and a recruiter reading the name reads a narrower thing than the page. The
owner also asked for the path to be said on the page: *since project
started it growth from small sdet/devops demo petproject to real cloud
platform blueprint* - and, on the draft, *dont point to exact dates, just
in general*.

Two constraints shape what changes and what does not. Links to the
repository are being sent to recruiters and reviewers continuously, so a
rename cannot wait for a quiet moment and cannot break an old link. And the
first name is an identifier in three permanent state levels - the state
bucket `aws-devops-sdet-demo-tfstate-…`, the ECR repositories, the OIDC
roles - and in the `Project` tag the sweep and the watchdog select on, and
the `name_prefix` of every environment: 39 Terraform files.

## Decision

**D1. The page and the repository are `aws-platform-demo`; the AWS names
keep the first one.** `aws`, because everything here is AWS-specific and a
wider word would promise what is not there; `platform`, because that is
what the shape became; `demo`, because it is a demonstration and says so.
The names in AWS are not renamed: a prefix in permanent levels is an
identifier, and recreating three permanent levels, moving state and images
and reteaching the sweep for a word nobody outside sees is the rename that
is not worth its risk to a demo in strangers' hands. The precedent is
`app`, the api's compose service and target group (ADR-0101): declared as
history rather than renamed.

**D2. The statement says the path, without dates.** One paragraph in
`Details`, above the claim about the teardown, and its first sentence in
the README: *started as a one-container DevOps/SDET demo under the name
`aws-devops-sdet-demo` … now three services on two runtimes, declared once
in a manifest … the shape of a platform, at demo scale. The AWS names
underneath keep the first name.* No dates, on the owner's word - a
statement with a date in it has to be maintained, and this one has to stay
true on its own. *The shape of a platform, at demo scale* rather than *a
real cloud platform blueprint*: the page states and does not grade itself,
and the scale is said honestly. *Started as … under the name* is true
before and after the repository is renamed, which is why the page can be
renamed hours before the repository is.

**D3. In two steps, because the links are live.** First the page, the
README and this record - nothing that talks to GitHub by name changes, so
the button and the run history keep working against the repository as it
is. Then, at the owner's hand in GitHub's settings, the repository -
GitHub redirects the old name for the browser and for `git clone`, and the
old name cannot be taken by anyone but the owner's organisation - and in
the same hour the page's `REPO` constant, the button's repository, the
links, the fixtures and the documents, proven by one launch from the
button. A stranger with the old link lands on the renamed repository and
reads the first sentence of the README.

## Consequences

- The name on the page and the name in AWS differ, deliberately, and the
  page says why in one sentence. Anyone reading `aws-devops-sdet-demo-…` in
  a resource name has the explanation four lines under the `Details`
  heading.
- The first step (page, README, this ADR) is on `next` and merged on the
  owner's word; the second step is recorded here when it is done, with the
  launch that proved it.
- `docs/` keeps the first name wherever it is quoted from a log, a tag or
  a resource - those are records of what was, not statements of what is.
