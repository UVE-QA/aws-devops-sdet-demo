# ADR-0030: Third-party actions are pinned by commit SHA, and a check keeps them that way

## Status
Accepted (Phase 15b). Extends the supply-chain work of Phase 15a (Dependabot
over five manifests, gitleaks as a gate). Supersedes PR #3, which proposed the
same six version bumps as mutable tags.

## Context

Every workflow in this repository starts with third-party code:

```text
8  actions/checkout
7  aws-actions/configure-aws-credentials
6  actions/upload-artifact
4  hashicorp/setup-terraform
3  actions/setup-python
3  actions/setup-node
1  aws-actions/amazon-ecr-login
```

All of them were referenced by major-version tag — `actions/checkout@v5`. A tag
is a mutable pointer: the owner, or anyone who compromises the owner's account,
can move it to a different commit without any repository that consumes it
changing a byte.

That is a generic risk everywhere. Here it lands on the exact claim this project
is built to demonstrate. `deploy-stage`, `promote-prod`, `destroy` and
`publish-site` run with `id-token: write` and assume an IAM role in the demo
account over OIDC. The security story is "no static AWS credentials anywhere" —
and it is true. But OIDC does not authenticate *code*; it authenticates a
workflow's identity and hands the resulting credentials to whatever is running
in the job. `aws-actions/configure-aws-credentials` is the step that performs
that exchange, in every AWS workflow, and it was floating on `@v4`.

Phase 15a already showed how invisible this layer is. The Actions annotation
channel reported two stale actions; Dependabot's first run found six. Four had
aged silently, including the credentials action, two majors behind.

Pinning and staleness are **orthogonal**, and conflating them is the usual
mistake:

```text
Dependabot   solves staleness. A pinned action still gets updated, because
             Dependabot maintains SHA pins and rewrites the version comment
             beside them.
SHA pinning  solves mutability. It says nothing about how old the pin is,
             which is exactly why the version comment is mandatory.
```

Neither substitutes for the other. Together they cost nothing extra: 15a
already proved the bot works in this repository.

## Decision

### 1. Every third-party action is referenced by commit SHA

```yaml
uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
```

32 references across five workflows. Local actions (`./...`) are exempt: they
live in this repository and move with it.

### 2. The version comment is required, not decorative

A 40-character hex string is unreadable by design. Without the comment nobody
can tell whether a pin is one release old or three years old, and the pin
becomes a different kind of invisible than the tag it replaced. Dependabot
writes and maintains this comment.

### 3. A check enforces it — `make action-pins`, in `ci.yml`

Pinning is a one-time edit; staying pinned is not. The first person to add a
step will copy the idiom from documentation, which is written with tags. The
check runs on every push and pull request, and refuses when it finds no `uses:`
lines at all, because a checker that silently scans nothing passes everything.

### 4. The SHAs were resolved from git, not from a web page

```bash
git ls-remote https://github.com/actions/checkout refs/tags/v7.0.1^{}
```

The `^{}` peels the annotated tag to the commit it points at, which is what
`uses:` must name. This is a verifiable operation against the repository itself
rather than a value copied out of a rendered page, and the command is printed
by `check-action-pins.py` when it fails, so the next person does not have to
rediscover it.

### 5. PR #3 is closed as superseded, not merged

Dependabot proposed the same six bumps as tags. Pinning directly to the SHAs of
those same versions produces the identical upgrade in one commit, so merging
first and pinning second would be two changes to review instead of one.

## Consequences

**A pinned action cannot be updated by accident, and that includes by us.**
Every update is now a commit that names both the old and the new SHA. This is
the intended cost.

**Four of the five workflows are not exercised by `ci`.** `deploy-stage`,
`promote-prod`, `destroy` and `publish-site` are dispatch-only, so the version
half of this change — `setup-terraform` v3 to v4, `configure-aws-credentials`
v4 to v6 — is only proven by the next full cycle. The pin half is inert by
construction: a SHA and its tag are the same bytes. If the next cycle breaks,
the version bump is the suspect, not the pinning.

**The Node.js 20 deprecation annotations should disappear.** They named
`actions/upload-artifact@v4` and `hashicorp/setup-terraform@v3`, both of which
this change moves past.

## Alternatives considered

**Merge PR #3 as tags and pin later.** Two reviews for one outcome, and it
leaves the mutable-tag window open across a full cycle for no benefit.

**Pin only the AWS-credential action.** It is the sharpest edge, but
`actions/checkout` runs first in every job and can modify the workspace before
any other step sees it. A partial pin invites the question "why this one" at
every future review, and answering it once in a check is cheaper.

**Use a third-party pinning tool.** One more thing to install, trust and keep
current, to maintain a property a twelve-line script can assert.
