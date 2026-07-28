# The transfer buffer

`~/Projects/_claude-transfer` on the MacBook is the staging area between a chat
session and the repository. **It is not a working copy of
`aws-devops-sdet-demo`.** The only working copy is on the devbox
(`ubuntu@34.213.147.86:~/aws-devops-sdet-demo`); GitHub is the source of truth.

## Layout

```text
send.sh              a COPY of scripts/send.sh from this repository
README.md            a COPY of this file
session-primer.md    a COPY of docs/session-primer.md — drafted here between
                     sessions, pushed to the repo, refreshed after every push
outbox/              payload only — files a chat produced that are not yet in git
```

Everything permanent in that folder is a copy of something in this repository
(**ADR-0028**). Refresh after any push that touched one:

```text
scp devbox:aws-devops-sdet-demo/docs/session-primer.md   ~/Projects/_claude-transfer/
scp devbox:aws-devops-sdet-demo/scripts/send.sh          ~/Projects/_claude-transfer/
scp devbox:aws-devops-sdet-demo/docs/transfer-buffer.md  ~/Projects/_claude-transfer/README.md
```

The primer's refresh is the one that actually gets forgotten — it went stale
three times in a single session on 2026-07-26, structurally rather than
carelessly: the primer is read at the start of a session and edited at the end.
A session that edits it says so in its closing summary.

## Starting a new chat

Attach `session-primer.md` to a new chat. That is the whole procedure — the file
tells the chat what it is, what to load, and when to stop. Nothing is pasted
alongside it.

## Why the split

One rule, and it is checkable at a glance: **`outbox/` empty means everything a
chat produced has been committed.** While permanent tooling and in-flight files
shared one flat folder, the folder was never empty and the rule could not be
read from its contents.

A chat can write into `outbox/` but cannot delete from it. Removing a patch once
it is pushed is the human's job; a chat that leaves one behind should say so when
it closes rather than leaving the invariant quietly broken.

## The normal path — one patch per session

```text
1. ask the chat to request access to ~/Projects/_claude-transfer at the start.
   It then writes its patch straight into outbox/ and neither side has to look
   up a path.
2. scp ~/Projects/_claude-transfer/outbox/<name>.patch devbox:/tmp/
3. ssh devbox 'cd ~/aws-devops-sdet-demo && git pull --ff-only \
     && git am /tmp/<name>.patch && make tf-validate && git push'
4. delete the patch from outbox/ once it is pushed
```

`git am` refuses to apply onto a diverged or dirty tree and changes nothing when
it refuses, so a wrong assumption about the base commit surfaces before anything
moves.

**Expect several patches per session, not one.** A session writes its closing
documents before its validation runs, because the patch has to reach the devbox
before anything can run there. Phase 11.1c took four, and each existed because a
real run said something no fixture had said. The number of patches is not a
measure of tidiness — it is how many times reality got a word in.

## The one-off path

For a single file outside a session's patch:

```text
./send.sh <file> <path/in/repo> ["commit message"]
    a BARE name is looked up in outbox/ first, and the resolved path is printed
    no message -> delivered, not committed; review and commit on the devbox
    message    -> delivered, committed, pushed
```

If a bare name matches in **both** the buffer root and `outbox/`, the script
refuses and asks for an explicit path. That case is not hypothetical:
`session-primer.md` exists in both by design, and the previous
current-directory-first lookup delivered the stale copy silently — the diff came
out empty, there was nothing to commit, and the script ended before printing
"pushed" (**ADR-0028**).

## Note on ~/Projects/aws-devops-sdet-demo

A stale stub from 2026-06-06: not a git repository, holding old copies of
`discussion-log.md` and `project-prompt.md` plus a single early ADR.

A session in 2026-07-25 recorded that everything unique in it had been
committed. **That was wrong by exactly one file**, `docs/project-prompt.md`,
which existed nowhere else and was nearly deleted on the strength of the claim
(see ADR-0019). It was committed in `96e110c`.

Verify with `git ls-files` before treating anything there as redundant, and do
not read it for project state.
