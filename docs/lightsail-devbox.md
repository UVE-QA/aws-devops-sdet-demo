# The Lightsail devbox

The persistent development machine for this project. It is **not** the AWS
deployment target — ECS Fargate, the ALB and RDS are (`docs/architecture.md`).
The devbox exists so that every command in this project's history has a single,
consistent home: one git clone, one Docker daemon, one set of CLI versions.

## What it is

From `docs/preflight-inventory.md`, Phase 1 (kept current here; that file is the
Phase 0 record and does not get edited after the fact):

```text
Instance name    devops-sdet-devbox
OS               Ubuntu 24.04 LTS
Size             2 GB RAM / 2 vCPU / 60 GB  (~$12/month, a Lightsail fixed
                                            price - not part of the per-cycle
                                            AWS cost in docs/cost-control.md)
AZ               us-west-2a
Static IP        34.213.147.86
Private IP       172.26.4.52
Firewall         SSH/22 only
```

Toolchain installed and version-verified (Phase 1 criteria):

```text
Docker 29.5.3            Docker Compose v5.1.4
AWS CLI 2.34.63           Terraform 1.15.5
Node.js 20.20.2           Python 3.12.3
Git 2.43.0                Make 4.3
GitHub CLI 2.45.0         dnsutils (dig)
```

## What runs where

```text
Laptop / any computer
  |  SSH / browser SSH (VS Code Remote-SSH deferred - see below)
  v
Lightsail Ubuntu devbox
  |-- git clone of aws-devops-sdet-demo (the ONE working copy, git lives here)
  |-- Docker + Docker Compose (postgres:16 not exposed, app on :8000)
  |-- Playwright
  |-- Terraform CLI, AWS CLI
  |-- Claude Code, if a chat session hands off heavy file editing
```

Local development means the Docker Compose stack running ON the devbox, not on
the laptop. The laptop is a terminal into it.

## Access

Browser SSH through the Lightsail console is the current method — VS Code
Remote-SSH was the original plan and is still deferred
(`docs/preflight-inventory.md`, "still outstanding, non-blocking").

To reach the app running in Compose from a laptop browser, tunnel it over SSH
rather than opening the port on the devbox's firewall:

```bash
ssh -L 8000:localhost:8000 ubuntu@34.213.147.86
```

then open `http://localhost:8000` locally. The Lightsail firewall stays
SSH-only by design (`docs/session-primer.md` §8 of the original project
instructions) — Postgres (5432) and the dev app port are never exposed
publicly, only reachable through the tunnel.

## Two logins that need a non-default flag, and why

```text
aws sso login --profile demo-admin --use-device-code
```
The default SSO flow opens a callback on `127.0.0.1`. On a headless box that
loopback is the DEVBOX's own, unreachable from the browser that completes the
login on the laptop. `--use-device-code` prints a code and a URL instead of
trying to open a local browser. This has to be run from inside the step that
needs it — a chat session driving the devbox cannot see whether a previously
issued token is still alive, so it is never assumed.

```text
gh auth login --git-protocol https --web
```
Without `--git-protocol https`, `gh auth login` prompts to upload an SSH key.
git already pushes over SSH with its own key; `gh` only needs API access, so
forcing HTTPS here avoids a second, redundant key negotiation.

## Claude Code on the devbox

`CLAUDE.md`, read automatically at the start of a Claude Code session there,
points to `docs/session-primer.md` and then to `make session-open`
(ADR-0033) — it refuses to start on a working copy that is not what it claims
to be (wrong branch, dirty tree, an unpushed previous session) and prints the
current phase from `docs/phase-gates.md` rather than from memory. A chat
session hands off to Claude Code on the devbox specifically for heavy,
multi-file edits; anything that needs judgment or planning first happens in
the chat, which then issues one command at a time, each labelled `[mac]` or
`[devbox]`.

## Known operational notes

```text
- make tf-validate used to leave ~700MB per Terraform root level in /tmp on
  every run. Fixed 2026-07-26; if a disk-full error appears again on the
  devbox, check /tmp/tmp.* first before anything else.
- the devbox has needed tools installed AFTER a related CI gate shipped,
  twice: gitleaks (Phase 15a) and Checkov (Phase 15b) were both absent
  locally days after their CI jobs went green - a reminder that "the gate
  passes in CI" and "this machine can reproduce it" are different claims.
- git identity on the devbox: UVE-QA / papers.usher.3m@icloud.com. The
  repository clone lives at /home/ubuntu/aws-devops-sdet-demo.
```

## Its role in the architecture, stated once

The devbox is a fixed-cost, always-on development host — the one thing in this
project that is deliberately NOT torn down between cycles, because losing the
working copy or the toolchain between sessions would cost more in
re-setup than the ~$12/month it costs to leave running. Everything it builds
and tests locally is what `deploy-stage` later reproduces on ECS Fargate; the
devbox never serves the application to anyone but the person tunnelled into it.
