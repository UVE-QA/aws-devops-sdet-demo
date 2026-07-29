# 2026-07-28 — Phase 15a: Dependabot, the secret gate, and the budget email

Chat-driven session. Nothing was applied to AWS; nothing in it was billable.
State was loaded by cloning `origin/main` fresh. A clone from an earlier chat was
sitting in the sandbox again — discarded unread, per ADR-0019 — and the fresh
clone's HEAD was compared against `origin/main` before anything was believed.

Phase 15 was split. **15a is this session: Dependabot, gitleaks, and the
secrets-hygiene item Phase 14 left open.** Trivy and Checkov are 15b, separated
deliberately: both produce real findings, and every finding is a fix-or-allowlist
decision. Mixing them with two deterministic gates would have hidden the
deterministic ones inside a triage session.

## What was done

### Dependabot, and what it exposed on its first run

`.github/dependabot.yml`, five ecosystems — `github-actions`, `pip` in `app/`,
`tests/api/` and `tests/db/`, `npm` in `tests/playwright/`. Grouped per
ecosystem, weekly. Version updates only; Dependabot **alerts** are a repository
UI setting, in the same uncheckable category as prod's protection rules.

The prediction was that it would raise the two Node 20 deprecations read by hand
in Phase 14. It did — and four more:

```text
actions/upload-artifact                v4 → v7   known, annotated
hashicorp/setup-terraform              v3 → v4   known, annotated
actions/checkout                       v5 → v7   silent
actions/setup-python                   v6 → v7   silent
actions/setup-node                     v5 → v7   silent
aws-actions/configure-aws-credentials  v4 → v6   silent
```

**The annotation channel was showing two of six.** Annotations report a runtime
deprecation, not staleness, so everything that aged quietly stayed invisible —
including the action that performs every OIDC authentication in this project,
two majors behind. Reading the annotations in Phase 14 felt like clearing the
debt; it cleared a third of it.

Five PRs opened immediately rather than on the configured Monday: the first run
after the file lands walks every manifest.

**PR #3 is deliberately NOT merged.** It touches five workflows and `ci` runs
exactly one of them — a green check on that PR would say "ci.yml survived" and
nothing at all about `deploy-stage`, `promote-prod`, `destroy` and
`publish-site`, which are dispatch-only. Merging it would change the OIDC
authentication path of four billable workflows and defer the verdict to the next
cycle, mid-demo. It is held until a cycle can exercise it on stage, where a
regression is cheap. Splitting it in `dependabot.yml` is not an option:
grouping is per dependency, and `actions/checkout` is in both halves.

### The secret gate, and the break test that did not break it

`make secret-scan` runs gitleaks over the full history, every ref
(`--log-opts="--all"`), redacted, and `ci.yml` installs a pinned,
checksum-verified 8.30.1 and calls that same target. One definition, two hosts.

`gitleaks/gitleaks-action` was deliberately not used: it requires a
`GITLEAKS_LICENSE` for organization-owned repositories, and installing by
version with a verified checksum is the practice this phase is meant to show.

Two refusals sit in front of the scan, both aimed at the failure mode this
project keeps meeting — an empty result that reads as a clean one:

```text
gitleaks not on PATH   a scanner that never ran finds no leaks
shallow clone          actions/checkout defaults to depth 1, and one commit is
                       clean on a history full of keys
```

Both fired for real. The missing-scanner refusal fired on the devbox, where
**gitleaks turned out not to be installed at all** — the tool that paid the
Phase 11.0 debt on 2026-07-26 was gone two days later, which is the argument for
a gate rather than a memory, made by accident. The shallow refusal fired against
a `--depth 1` clone. And a full clone with the scanner present did NOT refuse: a
check that only ever refuses is as useless as one that never does.

Then the break test, and it is the finding of the session:

```text
planted AKIA...  (an access key id alone), committed → make secret-scan GREEN
```

The gate was not broken. The chain was fine — 120 commits scanned, the planted
commit among them — so the fault was in the assumption, not the wiring. Three
probes located it:

```text
gitleaks stdin  <the same key>                        no leaks
gitleaks dir    break-test.txt                        no leaks
gitleaks stdin  --enable-rule aws-access-token        rule EXISTS, no leaks
gitleaks stdin  <the sidekiq secret from the README>  FOUND, exit 1
```

The last probe is what made the difference between "the scanner is broken" and
"the rule does not match": the scanner detects, exits 1, and its configuration is
intact. **In gitleaks 8.30 an AWS access key ID on its own is not a finding.**
Adding a secret access key beside it produced a finding — under
`generic-api-key`, on entropy, not under `aws-access-token`.

That retires an instruction this project wrote down on 2026-07-26:

```text
11.1a: "assert on the AWS rule specifically rather than on 'something was found'"
```

It cannot be done in 8.30. The AWS-specific rule does not fire on the identifier,
and the pair is caught by the generic entropy rule. The behaviour is defensible —
an access key ID is not a credential, and the half that actually costs money is
caught — but it has to be written down, because "gitleaks catches AKIA" is what
everyone assumes.

Re-run with the pair, through a real commit and `make`:

```text
RuleID generic-api-key, File break-test.txt, Secret REDACTED, exit 1
```

Red, and redacted — the gate does not publish, in the log of a public
repository, the secret it has just found. The branch was never pushed and was
deleted.

### The budget email

`TF_VAR_budget_email` was a GitHub *variable*, so it was not masked and appeared
in the step environment dump of every stage and prod run of a public repository.
Found in Phase 14 while reading an unrelated log, recorded as a follow-up, fixed
here: an environment **secret** in both `stage` and `prod`, referenced by
`deploy-stage`, `promote-prod` and `destroy`.

`deploy-stage.yml` carried a header comment asserting the opposite — "AWS values
come from repo Variables (vars.*), not Secrets". Corrected in the same commit.
A comment that contradicts the file under it is worse than no comment.

If the secret is ever missing, `terraform plan` fails with "No value for required
variable" before anything is created. Loud, and at the right moment.

## What was observed, and how

```text
make secret-scan (devbox)  8.30.1, 119 commits across every ref, no leaks.
                           81 were scanned on 2026-07-26; the 38 since had
                           never been scanned by anything.
ci #80 on main             green. secret-scan job: checksum OK, "119 commits
                           across every ref" from make and "119 commits
                           scanned." from gitleaks — two independent counts,
                           read from the job-level API, not from
                           `gh run view --log`
gitleaks-report artifact   159 bytes, an empty finding list
break test                 green on a planted AKIA id (the finding), red on the
                           pair, RuleID generic-api-key, secret REDACTED
dependabot                 5 PRs, one per ecosystem; PR #3 carries 6 action
                           updates, 4 of them silent until now
```

## Follow-ups

```text
PR #3             merge immediately before the next full cycle, so deploy-stage
                  exercises the new configure-aws-credentials on stage. Do not
                  merge it and then not run a cycle.
PR #1 #2 #4 #5    pip/npm bumps. These ARE exercised by ci (build, api suite,
                  playwright), so their green check means something. pytest
                  8.3.4 → 9.1.1 is a major and should be read, not just merged.
15b               Trivy and Checkov, plus the question 15a raised and did not
                  answer: whether actions should be pinned by SHA rather than by
                  tag. Dependabot can maintain SHA pins.
dashboard badge   unchanged from Phase 13 and 14: the green state carries no
                  observation age.
one account       unchanged.
```

## Cost

$0. No AWS API call was made in this session, and no billable resource existed
at any point.
