# Session Primer

**This file is the whole entry point. Attaching it to a new chat starts the
session — there is nothing else to paste.**

It is a **pointer**, not a summary: it says what to read, in what order, who
does what, and what has burned us before. It deliberately holds almost no state,
so it does not go stale. The cursor lives in `docs/phase-gates.md`; nothing else
claims to know the current phase, including this file.

## If you are the chat reading this, start here

```text
1. You are the DRIVER for this session.
2. Load state NOW, per section A below. Do not ask permission first.
3. Then STOP. Report: current phase, next allowed step, blockers. Propose what
   this session should cover, and wait for confirmation before doing anything.
4. Then run the session per the working agreements below: one command at a time,
   labelled [mac] or [devbox]; verify each step before the next; explicit
   confirmation before any billable AWS action; never ask for secrets.
5. Ask for access to ~/Projects/_claude-transfer early, so deliverables can be
   written straight into outbox/.
6. Close the session per section C. Nothing is done until it is pushed.
```

Discussion may be in Russian. Anything that lands in the repository — docs,
ADRs, code, commit messages — is in English.

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
- if this file changed, refresh the local copy (see "The local copy of this file")
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
- ONE copyable block per message, and the host label goes OUTSIDE it. A block
  whose first line is `[devbox] make local-up` has to be edited before it can
  be run, and a second block in the same message gets run by accident. Both
  happened on 2026-07-26, the second one because a discarded command was left
  in the reply.
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
Phase 13 — MVP verification gate
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
- A gate that has only ever been seen GREEN is indistinguishable from a gate
  that cannot fail. Break each new one on purpose, once, and keep the output.
  Eleven have been confirmed this way: the tf-validate discovery check, the
  Playwright spec-coverage guard, the UI-write assertion, `make docs-check` (six
  ways, including its own document list going missing), the Mermaid parse check
  (on a malformed diagram AND on a file containing no diagram at all), the prod
  rollback itself (fired by promoting a knowingly broken image, and the re-run
  smoke proved it restored something that works), and its no-target refusal
  (seen live on an empty pointer, and on the devbox against a digest that had
  genuinely just been deleted, with the same check answering `present` for a
  live one in the same command), the secret gate (red on a planted key pair,
  with the secret REDACTED in the log, and both of its refusals fired for real),
  `make iac-scan` (a security group opening port 22, plus all three refusals -
  scanner missing, config missing, zero checks evaluated), `make image-scan`
  (all four verdict branches on fixtures, THEN red and green in CI on a real
  starlette CVE rather than a planted one) and `make action-pins` (a tag instead
  of a SHA, a pin with its version comment removed, and the workflows directory
  moved away). Only the rollback cost more than a minute.
- A BREAK TEST THAT FAILS TO BREAK is testing your assumption about the tool,
  not the tool. On 2026-07-28 a planted AWS access key id was committed and the
  secret gate scanned it GREEN. The wiring was blameless — 120 commits scanned,
  the planted one among them; gitleaks 8.30 simply does not treat an `AKIA…`
  identifier as a finding, and the pair is caught by the entropy rule rather than
  the AWS one. Two probes separated "the scanner is broken" from "the rule does
  not match" in under a minute: the tool's OWN documented example secret, which
  fired, and `--enable-rule <id>`, which proved the rule existed. When a gate
  stays green on a planted failure, first prove the tool can fail at all.
- A BREAK TEST MEASURED THROUGH A PIPE MEASURES THE PIPE. On 2026-07-28 the
  first Checkov break test printed three red findings and then an exit status of
  zero, which read exactly like 15a's gate that would not break. The gate was
  fine: `$?` taken after a pipe into `grep` is grep's status, not the target's.
  One re-measurement with the output redirected to a file settled it in seconds. The reading was indistinguishable
  from a real defect, which is the point - an instrument has to be trusted
  before its verdict means anything, and that includes the shell.
- ONE DEFINITION, TWO HOSTS PROTECTS THE TARGET, NOT THE TOOL UNDER IT. On
  2026-07-28 `docker compose config --images app` filtered by service on the
  devbox and ignored the filter on the GitHub runner, handing the image scan
  `postgres:16`. The Makefile recipe was byte-identical on both machines. When a
  target asks a tool to DISCOVER something, the answer is a version-dependent
  fact, not a definition - prefer a literal that both sides can be checked
  against.
- COMMIT BEFORE BREAKING THINGS ON PURPOSE. Restoring a file with `git checkout`
  after a deliberate break discards whatever was uncommitted in it. On
  2026-07-28 a completed pinning edit to `ci.yml` vanished that way, silently,
  and was only noticed because the next check disagreed.
- A GATE ON A SHARED DEPENDENCY REDDENS EVERY OPEN PULL REQUEST. The moment the
  image scan reached `main`, four Dependabot PRs failed on findings none of them
  introduced, and none of the four carried a readable signal about its own
  contents until the fix landed. Land the fix first, or expect to explain four
  red checks that mean nothing.
- A guarantee stated in a comment is not a guarantee. `promote-prod.yml` said
  "read-only smoke against prod" and ran the whole test directory; it was true
  only while no destructive test existed. When a document and a command
  disagree, the command wins — go read the command.
- An EMPTY result is not a clean result. A post-teardown check whose SSO token
  had expired printed `ecs :`, `rds :`, `alb :` and six more empty lines, which
  is exactly what success looks like. Put `aws sts get-caller-identity` first and
  assign each result to a variable under `set -e`, so losing credentials aborts
  instead of rendering green. The same shape from a different tool on
  2026-07-28: `gh run view --log-failed` printed NOTHING for a run with two
  failed steps, and `--log` printed nothing either — indistinguishable from a
  run with no failures. The job-level API returned 2202 lines immediately. A
  tool answering "nothing" is not evidence that there is nothing.
- THE LIVING DOCUMENTS ARE NOW MACHINE-CHECKED, and this file is one of them.
  `make docs-check` verifies that every `make` target, repository path, HTTP
  route and workflow filename named in README.md, docs/architecture.md,
  docs/demo-script.md, docs/phase-gates.md, docs/transfer-buffer.md and THIS
  FILE actually exists, and it runs in `ci.yml`. So a document that invents a
  path now reddens CI rather than misleading a reader six weeks later. Two
  consequences for a chat session: run it before delivering a patch that touches
  any of the six, and write container-internal paths in absolute form
  (`/app/scripts/...`), because a repo-shaped path is checked as one.
- Documenting a trap once does not remove it. `--use-device-code` was written
  down in one file while eight others still printed the flagless command, and the
  eight were the ones being copied from. A fix goes to every copyable
  occurrence, in the same commit, exactly like a shared invariant.
- Absence of evidence in the session is not absence in the repository. On
  2026-07-28 a chat asserted docs/demo-script.md did not exist, on the strength
  of its name appearing in a "required documents" list, and wrote a replacement.
  The file existed, ran to 209 lines, and was better; `git am` refused with
  "already exists in index". A requirements list is evidence that someone wanted
  the thing, never that it is there. The same chat said no command had ever been
  run from the Mac, because none appeared in its own context; one had, that
  morning. Run `ls`, `git log -- <path>`, `grep` before saying something is
  missing. This is the negative half of "a claim about state is not state", and
  it is the half that feels like knowledge rather than like trusting a document.
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

### Expect several patches per session, not one

A session writes its closing documents BEFORE its validation runs, because that
is the order the work happens in: the patch has to reach the devbox before
anything can be run there. On 2026-07-26 the closing commit said "nothing has
run against PostgreSQL" — true when written, false twenty minutes later.

So the minimum shape is one patch with the work and the documents that can be
written in advance, then a second, small one recording what the validation
actually showed. Do not try to collapse them by holding the first patch back.

**Two is the floor, not the expectation.** Phase 11.1c took FOUR, and the reason
generalises: the moment an artifact is exercised by a live cycle, each thing the
cycle reveals has to land BEFORE the next run, or that run cannot show whether
the fix worked. Three of that session's four patches existed because a real run
said something no fixture had said, and each was delivered between workflow runs,
in minutes.

So the number of patches is not a measure of tidiness — it is how many times
reality got a word in. Deliver whenever it does. A session that ships one patch
because that felt neater has usually decided not to look.

### The layout

```text
mac      ~/Projects/_claude-transfer/          permanent, and every file here
                                              is a COPY of one in the repo:
                                                send.sh            scripts/send.sh
                                                README.md          docs/transfer-buffer.md
                                                session-primer.md  docs/session-primer.md
                                                  <- THIS is the file you attach
                                                  to a new chat; keep it in sync
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
    a bare name is looked up in outbox/ FIRST, and the resolved path is printed
    without a message: delivers and shows git status, you commit after review
    with a message:    delivers, commits, pushes
```

**The bare-name lookup used to shadow exactly the file it mattered most for**, and
the fix is now in git (**ADR-0028**, Phase 12). The old code read
`[ ! -f "$LOCAL" ] && [ -f "outbox/$LOCAL" ]`, so the CURRENT DIRECTORY won: a
bare `session-primer.md` resolved to the stale attach-copy in the buffer root,
never to the fresh one in `outbox/`. That is the one filename that exists in both
places, by design, and it is this file. On 2026-07-26 it delivered the old primer,
the diff was empty, `git commit` found nothing to commit and `set -e` ended the
script before the word "pushed" — a delivery that looked almost like a success.

`scripts/send.sh` now **refuses** when a bare name matches in both places, and
names the explicit form to use:

```text
./send.sh outbox/session-primer.md docs/session-primer.md "docs(primer): ..."
```

Refusing rather than silently preferring `outbox/` is deliberate: preferring is
still a silent choice, and silence was the defect. The refusal was exercised
before it shipped, alongside both unambiguous cases.

**The chat can write into `outbox/` but cannot delete from it.** Removing a
patch once it is committed is yours to do. A chat that leaves one behind should
say so when it closes, rather than leaving the invariant below quietly broken.

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

Paid off in Phase 12 (**ADR-0028**): `send.sh` and the buffer README used to
exist ONLY on the MacBook — control-layer tooling outside the source of truth,
the same shape as the 2026-07-25 finding, when `CLAUDE.md` and the skills had
never been committed. They now live at `scripts/send.sh` and
`docs/transfer-buffer.md`, and the MacBook copies are copies. Refresh them after
a push that touches either, exactly as for this file.

### The local copy of this file

`~/Projects/_claude-transfer/session-primer.md` is a **copy**, not the original.
An earlier version of this section called it the "local original" while another
section told you to refresh it from the repository — both could not be true. In
a project whose first rule is that git is the source of truth, the repository
version wins, and this file is the one that gets edited and pushed.

The copy stays because **it is what you attach to a new chat**, and because it
is where this file is drafted between sessions. Refresh it whenever the
repository version changes:

```text
scp devbox:aws-devops-sdet-demo/docs/session-primer.md ~/Projects/_claude-transfer/
```

That refresh is the weak point. On 2026-07-26 the copy went stale three times in
a single session — not through carelessness, but structurally: this file is read
at the start of a session and edited at the end. **A push that touches this file
is not finished until the copy is refreshed in the same breath**, and a session
that edits it should say so in its closing summary.

A previous attempt to solve this by deleting the copy, and another by adding a
script that fetched the appendix from the public repository, both failed the
same way: they replaced one file with two things to know about. One file that
starts a session is the design. Keep it that way.

## Current shape of the project (structural, changes rarely)

Since Phase 12 the repository explains itself, so a session does not have to
reconstruct the design from `infra/`: `README.md` (what it is, how to run it),
`docs/architecture.md` (the levels, the request path, the trade-offs) and
`docs/demo-script.md` (the ten-minute walkthrough). They are descriptions, not
plans — `docs/phase-gates.md` remains the only file that claims to know where
the project stands.


```text
Browser → ALB → ECS Fargate → RDS PostgreSQL, one FastAPI container.
Region us-west-2, one dedicated AWS Organizations member account.
GitHub OIDC only; no static AWS keys anywhere.
prod is public at https://app.demo.uveapp.net while it is up.

Terraform state levels — only the last two are ever destroyed:
  infra/bootstrap        S3 state bucket, local state, permanent
  infra/bootstrap-oidc   OIDC provider + deploy roles, permanent
  infra/shared-ecr       container registry, permanent        (ADR-0018)
  infra/dns              hosted zone + ACM certificate, permanent  (ADR-0024)
  infra/public-site      dashboard S3+CloudFront, permanent   (ADR-0027,
                         APPLIED 2026-07-26; https://demo.uveapp.net)
  infra/envs/stage       workload, destroyed every cycle
  infra/envs/prod        workload, destroyed every cycle
```

Test suites are split by DIRECTORY and bound to Playwright projects (ADR-0025).
Where a spec lives decides where it runs:

```text
tests/api/                          HTTP contract, DESTRUCTIVE, stage + local
tests/playwright/tests/smoke/       read-only — the only suite prod runs
tests/playwright/tests/regression/  DESTRUCTIVE — stage + local only
```

Anything that must survive a teardown — including the artifact that PROVES the
teardown works — belongs above the env levels. The container registry was the
second thing to qualify and the first one nobody noticed: it only becomes
obvious once prod runs an image that stage's teardown would delete (ADR-0018).

## Known traps (verify against phase-gates.md; these get fixed and go stale)

```text
- Every permanent level is applied. A cycle now starts straight at
  deploy-stage; the local applies are only needed on a fresh account, in the
  order listed in docs/preflight-inventory.md.
- prod's approval gate has BOTH halves: trust_branch_ref = false in IAM, and the
  prod environment's 2 protection rules in GitHub (required reviewers, main-only,
  admin bypass off). The GitHub half is UI state that git cannot assert — if a
  promotion ever runs without pausing, check it first.
- the NS record delegating demo.uveapp.net lives BY HAND in the parent zone, in
  org-management. Untracked by git, same category as the protection rules. If
  prod's name stops resolving, check it before anything else. And beware: a
  second, non-authoritative hosted zone for uveapp.net exists in an unrelated
  account and looks entirely real. Ground truth is the TLD:
  dig +noall +authority NS uveapp.net @a.gtld-servers.net
- the GitHub variable TF_VAR_DEMO_ACCOUNT_ID is NOT a Terraform variable.
  Only destroy.yml uses it, to build the deploy role ARN. Fixing the name means
  renaming it in the GitHub UI. TF_STATE_BUCKET, on stage, is used by nothing.
- prod keeps no data between cycles, and app.demo.uveapp.net is a dead name most
  of the time (ADR-0017 D2a). Say so; do not get caught by it.
- BECAUSE that name is usually dead, clients negative-cache it. On 2026-07-26
  prod looked dead in the browser for half an hour while serving 200s throughout:
  the macOS system resolver held an NXDOMAIN for it. `dig` resolved and `curl` on
  the same machine did not, because only `curl` goes through the system resolver.
  Verify prod from a host that has not been asking for the name, and flush before
  a demo: `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`.
  Three separate client-side symptoms all accused the application, which was
  never involved. Since 2026-07-26 the apex demo.uveapp.net and www are ALWAYS
  up (the dashboard, CloudFront), so the two kinds of name now behave
  differently: only app. is expected to be dead between cycles.
- `aws sso login` on the devbox needs `--use-device-code`. The default flow opens
  a callback on 127.0.0.1 that nothing there can reach. Put the login in the step
  itself; a chat session cannot see whether the token is still alive.
- a genuinely new path costs one failed run. Both IAM gaps in this project were
  reads a data source makes and the configuration never mentions; no amount of
  policy review finds them. Budget for it instead of being surprised — but note
  the record: this prediction has now been WRONG five times running. Every one of
  those sessions failed somewhere else instead, usually in the half nobody
  modelled (the browser, a document, a shell assumption). Then on 2026-07-28 it
  was right: SSM refuses any parameter name beginning with "aws", this project
  is called aws-devops-sdet-demo, and the first apply of the release pointer
  died with an AccessDeniedException that reads exactly like a missing IAM
  grant. Five wrong, then one right. Keep the budget, and stop treating either
  outcome as the pattern — the point of the budget is that you cannot tell in
  advance which half it will be.
```

---

## Appendix — starter for a Claude Code session on the devbox

Use when the work is heavy file editing and the chat hands it over.

```text
New session. Read docs/session-primer.md, then docs/phase-gates.md,
docs/next-phases.md, and the newest ADRs.

Then STOP: state the current phase, the next allowed step, and any blockers.
Change nothing until I confirm.
```
