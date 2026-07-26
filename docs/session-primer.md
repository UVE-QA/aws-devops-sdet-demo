# Session Primer

Read this first in any new session. It is a **pointer**, not a summary — it says
what to read, in what order, who does what, and what has burned us before. It
deliberately holds almost no state, so it does not go stale.

The cursor lives in `docs/phase-gates.md`. Nothing else claims to know the
current phase — including this file.

---

## How a session works

**Every session starts in a new chat.** The chat is the entry point and the
driver: it loads the current state, reports where the project is, then runs the
session — discussion, decisions, and step-by-step instructions. Execution
happens on the devbox.

```text
chat      DRIVES the session. Loads state, reports it, discusses, decides,
          authors documents, and issues commands one at a time, each labelled
          [mac] or [devbox]. It does not commit directly.
devbox    EXECUTES. Commands run there; files land there; git lives there.
you       the bridge between the two.
patch     delivery in ONE file: the session's own commits, exported as an
          mbox and applied with `git am`. send.sh remains for one-offs.
```

Optionally the chat can hand a task to a **Claude Code session on the devbox**
when the work is heavy file editing — that session reads `CLAUDE.md`, lands
here, and writes directly. Use it when a task touches many files; use the chat
for everything that needs thinking, planning, or judgement first.

What must never happen: the chat inventing state instead of loading it, or a
document reaching the repo without going through git.

## A. Loading state — chat session

**The repository is public.** Clone it into the session sandbox over HTTPS, with
no credential of any kind, and read state from that clone:

```text
git clone https://github.com/UVE-QA/aws-devops-sdet-demo
```

The read-only token this section described for a few hours on 2026-07-26 is
gone. ADR-0020 wrote its own expiry condition — "superseded when the repository
goes public" — and that condition was met the same day, by ADR-0022. Do not ask
for a token; there is nothing for one to unlock.

**Never reconstruct state from a copy that lives outside git (ADR-0019).** That
includes a clone left in the sandbox by an earlier chat: on 2026-07-26 one was
four commits behind `origin/main` and looked entirely authoritative — right
remote, clean tree, plausible HEAD. Compare the hash against `origin/main`
before believing anything, every time. Cloning fresh costs seconds.

## B. Loading state — Claude Code on the devbox

`CLAUDE.md` is read automatically and sends you here. Then:

```text
1. git pull
2. docs/phase-gates.md      the cursor: current phase, last validated step,
                            what is allowed next
3. docs/next-phases.md      the plan: MVP track 9-13, polish track 14-19.
                            Supersedes project-prompt.md §14.
4. docs/decisions/          the "why". Newest first. 0020-0023 are the ones
                            in flight; 0015 and 0016 still shape the state
                            levels and the teardown order
5. docs/discussion-log.md   the narrative. Read the top "Current state" block;
                            go deeper only for history
6. docs/sessions/INDEX.md   only when you need a specific past session
```

Then STOP and state the phase, the next allowed step, and any blocker before
touching anything.

## C. Closing a session

```text
- run the relevant validation
- update docs/phase-gates.md if the phase status changed
- write a summary in docs/sessions/ and add a row to INDEX.md
- record new structural decisions as ADRs
- commit and push; work is only shared once pushed
- leave the transfer buffer empty
```

---

## Working agreements

```text
- Phase gates are real. End of a phase: summary → validation → STOP →
  explicit confirmation. Do not advance without it.
- ONE command at a time. Not one block of three — one. Wait for real terminal
  output before the next. Never assume a step ran.
- Verify the previous step before starting the next one.
- Label every command [mac] or [devbox]. The wrong host has already cost a
  wasted round trip.
- Explicit confirmation before ANY billable action. Review the plan first.
- Never ask for secrets. Account ids, ARNs, regions, repo names are fine;
  keys, tokens, passwords are not. No exceptions: the clone needs no
  credential now.
- Give one correct method, not options A/B.
- Prefer a checked-in patch script over a long interactive heredoc when editing
  long documents: it fails loudly and changes nothing on mismatch.
```

## Language

```text
English   everything that lands in the repository or is pasted into a session:
          docs, ADRs, skills, code, commit messages, startup prompts.
Russian   live discussion in chat only.
```

## Session naming

Auto-generated chat titles are derived from content and cannot be relied on.
Rename the chat manually right after the first reply.

```text
Phase <N>[.<sub>] — <topic>     phase work
Ops — <topic>                   maintenance outside the phases

Phase 9.0 — reconcile prod scaffold
Phase 11.0 — publish repository
Phase 12 — README, architecture, demo script
Ops — devbox maintenance
```

## Verification habits that keep paying off

```text
- "It looked finished" is the recurring failure mode here, not "it broke".
  Every serious bug so far was something never exercised on the path that
  would expose it.
- A claim about state is not state. Check git, check AWS, check the file —
  do not trust a document, including this one.
- After a teardown, confirm against the AWS CLI, not against Terraform state.
- A fix to a shared invariant goes to EVERY environment directory in the same
  commit, not only the one being exercised.
```

## Delivering files from a chat to the repo

**The normal path is one patch per session, not one command per file.**

The chat session works inside its own clone of `origin/main`, commits there with
real commit messages, and exports the whole session as a single mbox file:

```text
git format-patch <base>..HEAD --stdout > phase-N.patch
```

You move that one file and apply it:

```text
[mac]     scp "<the chat's own outputs path>/phase-N.patch" devbox:/tmp/
[devbox]  cd ~/aws-devops-sdet-demo && git pull && git am /tmp/phase-N.patch
[devbox]  <validation> && git push
```

`git am` refuses to apply onto a diverged or dirty working copy and changes
nothing when it refuses. That is the property the "prefer a patch script over a
heredoc" rule was already asking for, applied to delivery itself: if the chat's
assumption about the base commit is wrong, you find out before anything moves.

Nothing about this lets the chat commit to `main`. It authors commits; you apply
and push them, after reading them.

### The layout

```text
mac      ~/Projects/_claude-transfer/          tooling, permanent:
                                                send.sh
                                                README.md
                                                (no copy of this file — see below)
         ~/Projects/_claude-transfer/outbox/   PAYLOAD ONLY.
                                                empty = everything is committed
devbox   ~/aws-devops-sdet-demo/               the ONE working copy
github   UVE-QA/aws-devops-sdet-demo           source of truth
ssh      ssh devbox / scp file devbox:/tmp/
```

### The one-off path

For a single file outside a session's patch, `send.sh` still works:

```text
./send.sh <file> <repo/path> ["commit message"]
    a bare filename is looked up in outbox/
    without a message: delivers and shows git status, you commit after review
    with a message:    delivers, commits, pushes
```

**The destination is always `outbox/`.** One fixed directory, never "wherever it
went this time". The split between tooling and `outbox/` makes one rule
checkable: **anything in `outbox/` has not been committed yet**, and that is now
a fact you can see at a glance. It was unverifiable while permanent tooling and
in-flight files shared a flat folder — the folder was never empty, so nothing
could be read from its contents.

### Paths

**The chat should mount the buffer and write into it directly.** Ask it to
request access to `~/Projects/_claude-transfer` at the start of the session;
after that it writes straight into `outbox/` and the path is fixed and known to
both sides.

Without that mount, a chat session writes into an outputs folder whose path
carries that session's own identifiers — different in every chat, impossible to
write down here. In that case the chat must emit a ready-to-run `[mac]` command
with the full path already substituted, because you cannot guess it.

File cards in the chat are for reading the file, not for delivering it. Assuming
a card lands anywhere by itself costs a round trip every time.

Known debt: `send.sh` and the buffer README exist ONLY on the MacBook. That is
control-layer tooling outside the source of truth — the same shape as the
2026-07-25 finding, when `CLAUDE.md` and the skills had never been committed.
They belong in the repository, with the local copies being copies.

### There is no local copy of this file

There used to be one on the MacBook, and it called itself the "local original"
while another section of this same file told you to refresh it whenever the
repository version changed. Both could not be true. In a project whose first
rule is that git is the source of truth, the repository version wins.

It existed because a private repository could not be read by a chat session, so
the paste-in starter had to live somewhere reachable. Publishing the repository
(ADR-0022) removed that job: the session clones this file itself, and the
starter in the appendix is one click away on GitHub, always current.

The copy was deleted rather than kept in sync. On 2026-07-26 alone it went stale
three times in a single session — because it is read at the start of a session
and edited at the end, which makes staleness structural rather than careless. A
sync ritual would have postponed that, not fixed it. Deleting the second copy
fixes it.

**Do not recreate it.** If you find yourself wanting a local copy, the thing you
actually want is `git pull` on the devbox.

## Current shape of the project (structural, changes rarely)

```text
Browser → ALB → ECS Fargate → RDS PostgreSQL, one FastAPI container.
Region us-west-2, one dedicated AWS Organizations member account.
GitHub OIDC only; no static AWS keys anywhere.

Terraform state levels — only the last two are ever destroyed:
  infra/bootstrap        S3 state bucket, local state, permanent
  infra/bootstrap-oidc   OIDC provider + deploy roles, permanent
  infra/shared-ecr       container registry, permanent        (ADR-0018)
  infra/public-site      dashboard S3+CloudFront, permanent   (Phase 11.1,
                         not built yet; 11.0 publish-the-repo is DONE)
  infra/envs/stage       workload, destroyed every cycle
  infra/envs/prod        workload, destroyed every cycle      (Phase 9)
```

Anything that must survive a teardown — including the artifact that PROVES the
teardown works — belongs above the env levels. The container registry was the
second thing to qualify and the first one nobody noticed: it only becomes
obvious once prod runs an image that stage's teardown would delete (ADR-0018).

## Known traps (verify against phase-gates.md; these get fixed and go stale)

```text
- infra/shared-ecr has never been applied. Apply it locally under demo-admin
  once per account, BEFORE the first deploy-stage run of a cycle; the workflow
  fails fast with an explicit message if the repository is absent.
- prod's deploy role EXISTS IN CODE but has never been applied. The next local
  apply of infra/bootstrap-oidc under demo-admin must plan as 1 role + 1 role
  policy added, 0 destroyed (ADR-0021 moved blocks). Anything else means a
  moved block is wrong — do not apply through it.
- destroy.yml still offers stage only, and prod desired_count is still 0.
- prod's approval gate has BOTH halves as of 2026-07-26: trust_branch_ref =
  false in IAM, and the prod environment's 2 protection rules in GitHub (required
  reviewers, main-only, admin bypass off). The GitHub half is UI state that git
  cannot assert — if a promotion ever runs without pausing, check it first.
- the GitHub variable TF_VAR_DEMO_ACCOUNT_ID is NOT a Terraform variable.
  Only destroy.yml uses it, to build the deploy role ARN. Fixing the name means
  renaming it in the GitHub UI.
- prod keeps no data between cycles, and app.<domain> is a dead link most of
  the time (ADR-0017 D2a). Say so; do not get caught by it.
```

---

## Appendix — paste-in starter for a new chat session

This is the entry point. Paste it as the first message of a new chat, then
rename the chat per the naming convention above.

```text
AWS project session. You are the driver for this session.

First, load state. The repository is PUBLIC — clone
https://github.com/UVE-QA/aws-devops-sdet-demo into your sandbox over HTTPS,
no credential needed, and read, in this order:
  docs/session-primer.md
  docs/phase-gates.md          (the cursor — the only file that knows the phase)
  docs/next-phases.md
  docs/decisions/              (newest first)
  docs/discussion-log.md       (top "Current state" block only)

Never rebuild state from a copy that lives outside git (ADR-0019) — including a
clone left in your sandbox by an earlier chat. Check the hash against
origin/main before believing anything. Also ask me for access to
~/Projects/_claude-transfer so you can write deliverables straight into
outbox/.

Then STOP and report: current phase, next allowed step, blockers. Propose what
this session should cover and wait for my confirmation.

Then run the session: discuss, decide, draft, and give me instructions.
- ONE command at a time, labelled [mac] or [devbox]. Wait for my real terminal
  output before the next. Never assume a step ran.
- Verify the previous step before starting the next.
- Author files inside your own clone, commit them there with real commit
  messages, and deliver the session as ONE patch:
  `git format-patch <base>..HEAD --stdout`, written into
  ~/Projects/_claude-transfer/outbox/ — ask for access to that folder at the
  start and the path stops being something either of us has to look up. Then
  give me the ready-to-run scp and `git am` lines. If you cannot get access to
  the folder, substitute your own sandbox path, because I cannot guess it.
  You never push; I apply and push after reading.
- Explicit confirmation before any billable AWS action. Never ask for secrets.
- English for anything that lands in the repo or is pasted into a session;
  Russian is fine for discussion.

At the end, close the session properly: validation, phase-gates update, a
summary in docs/sessions/ with a row in INDEX.md, ADRs for new structural
decisions, commit and push, and an empty transfer buffer.
```

## Appendix — starter for a Claude Code session on the devbox

Use when the work is heavy file editing and the chat hands it over.

```text
New session. Read docs/session-primer.md, then docs/phase-gates.md,
docs/next-phases.md, and the newest ADRs.

Then STOP: state the current phase, the next allowed step, and any blockers.
Change nothing until I confirm.
```
