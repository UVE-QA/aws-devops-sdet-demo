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

The session clones the repository into its sandbox over HTTPS and reads state
from that clone. While the repository is private this needs a token, which is a
deliberate, bounded exception to "never ask for secrets" — see ADR-0020.

```text
Resource owner    UVE-QA
Repository access Only select repositories → aws-devops-sdet-demo
Permissions       Contents: Read-only        (nothing else)
Expiration        shortest that covers the phase
```

Read-only on one repository: it cannot push, cannot reach anything else, and
expires on its own. The session clones with it, rewrites `origin` to the
credential-free URL immediately, and never writes it to a file. **Revoke it by
hand when the phase closes** — do not leave it to expire, and do not reuse a
token from an earlier chat.

If no token is supplied, fall back to loading state FROM THE DEVBOX: ask for
`git -C ~/aws-devops-sdet-demo log --oneline -5`, then the files in section B
one at a time. Treat that as the degraded path, not the normal one — what it
loads is a hand-picked excerpt, and nothing checks that the excerpt is complete.

**Never reconstruct state from a copy that lives outside git (ADR-0019).** That
includes a clone left in the sandbox by an earlier chat: on 2026-07-26 one was
four commits behind `origin/main` and looked entirely authoritative. Compare the
hash before believing anything, every time.

Both the token and this section expire at Phase 11, when the repository goes
public and the clone needs no credential.

## B. Loading state — Claude Code on the devbox

`CLAUDE.md` is read automatically and sends you here. Then:

```text
1. git pull
2. docs/phase-gates.md      the cursor: current phase, last validated step,
                            what is allowed next
3. docs/next-phases.md      the plan: MVP track 9-13, polish track 14-19.
                            Supersedes project-prompt.md §14.
4. docs/decisions/          the "why". Newest first; 0015, 0016, 0017 shape
                            everything currently in flight
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
  keys, tokens, passwords are not. ONE exception, bounded and written down:
  the read-only clone token of section A (ADR-0020). Nothing else.
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
                                                session-primer.md  <- local
                                                  original; its appendix is what
                                                  you paste to start a new chat
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

**The chat knows where its files are; you do not. So the chat supplies the
path.** A chat session writes into an outputs folder whose path contains that
session's own identifiers, so it is different in every chat and can never be
written down here. Whenever the chat hands you a file — patch or otherwise — it
must emit a ready-to-run `[mac]` command with the full path already substituted.

File cards in the chat are for reading the file, not for delivering it. Assuming
a card lands anywhere by itself costs a round trip every time.

Known debt: `send.sh` and the buffer README exist ONLY on the MacBook. That is
control-layer tooling outside the source of truth — the same shape as the
2026-07-25 finding, when `CLAUDE.md` and the skills had never been committed.
They belong in the repository, with the local copies being copies.

Refresh the local primer whenever the repository one changes; a stale copy is
actively harmful, because it is the copy a new chat starts from:

```text
scp devbox:aws-devops-sdet-demo/docs/session-primer.md ~/Projects/_claude-transfer/
```

## Current shape of the project (structural, changes rarely)

```text
Browser → ALB → ECS Fargate → RDS PostgreSQL, one FastAPI container.
Region us-west-2, one dedicated AWS Organizations member account.
GitHub OIDC only; no static AWS keys anywhere.

Terraform state levels — only the last two are ever destroyed:
  infra/bootstrap        S3 state bucket, local state, permanent
  infra/bootstrap-oidc   OIDC provider + deploy roles, permanent
  infra/shared-ecr       container registry, permanent        (ADR-0018)
  infra/public-site      dashboard S3+CloudFront, permanent   (Phase 11)
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
- prod has no deploy role of its own yet, so destroy.yml offers stage only and
  prod desired_count is still 0. Phase 9.1.
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

First, load state. Clone https://github.com/UVE-QA/aws-devops-sdet-demo into
your sandbox over HTTPS using the read-only token I paste next, rewrite origin
to the credential-free URL straight away, and read, in this order:
  docs/session-primer.md
  docs/phase-gates.md          (the cursor — the only file that knows the phase)
  docs/next-phases.md
  docs/decisions/              (newest first)
  docs/discussion-log.md       (top "Current state" block only)

If I have not given you a token, ask for one (fine-grained, this repo only,
Contents: Read-only — ADR-0020) or fall back to loading state FROM THE DEVBOX:
`git -C ~/aws-devops-sdet-demo log --oneline -5`, then the files above one at a
time. Never rebuild state from a copy that lives outside git (ADR-0019) —
including a clone left in your sandbox by an earlier chat. Check the hash.

Then STOP and report: current phase, next allowed step, blockers. Propose what
this session should cover and wait for my confirmation.

Then run the session: discuss, decide, draft, and give me instructions.
- ONE command at a time, labelled [mac] or [devbox]. Wait for my real terminal
  output before the next. Never assume a step ran.
- Verify the previous step before starting the next.
- Author files inside your own clone, commit them there with real commit
  messages, and deliver the session as ONE patch:
  `git format-patch <base>..HEAD --stdout`. Give me a ready-to-run scp with
  your own outputs path substituted — I cannot guess where your sandbox put
  it — then the `git am` line. You never push; I apply and push after reading.
- Explicit confirmation before any billable AWS action. Never ask for secrets —
  the read-only clone token above is the one written-down exception.
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
