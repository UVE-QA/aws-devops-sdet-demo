---
name: skill-maintenance
description: >
  Use when adding a new skill, editing or fixing an existing skill, or when a
  skill is not triggering (or the wrong one triggers): "create a skill",
  "add a skill", "update the skill", "this skill isn't firing", "wrong skill
  triggered", "the skills overlap", "новый скилл", "поправь скилл",
  "скилл не срабатывает". Covers when to add vs merge skills, how to write a
  trigger-rich description with explicit boundaries, how to verify triggering
  with the skill-creator evals, and how to record the change (ADR + registry).
  Do NOT use for: running the operational work itself, only for changing the
  skills that describe that work.
---

# Skill Maintenance

Skills are how we keep process out of the token budget: a skill loads only
when its description matches the task. So the description is everything —
most failures are "right body, weak description", not bad instructions.

## When to add, edit, or merge

- **Add** when a repeatable operation has no home (e.g. a new prod-only step
  in Phase 8). Keep the total small; ~9 skills is the comfortable ceiling.
- **Edit the description** when a skill mis-fires or under-fires. Fix the
  description first, not the body.
- **Merge or re-split** when two skills overlap on triggers. Overlap is the
  main cause of the wrong skill firing.

## Procedure for any skill change

1. **List trigger phrases** the skill should fire on — realistic user
   sentences, English and Russian, including file/path names and synonyms.
2. **Check overlap** against existing descriptions. If two could match the
   same phrase, add an explicit "Do NOT use for: ... (see other-skill)"
   line to both.
3. **Write the description**: what it does + concrete triggers + boundaries.
   Be slightly pushy (Claude tends to under-trigger). Body stays a procedure
   (imperative steps, exact commands), not theory.
4. **Verify triggering** with the skill-creator description optimizer, which
   runs trigger evals and reports the trigger rate:
   ```bash
   # from a copy of the skill-creator skill
   python -m scripts.run_loop \
     --eval-set <trigger-eval.json> \
     --skill-path .claude/skills/<name> \
     --model <current-model-id> \
     --max-iterations 5 --verbose
   ```
   Build the eval set with 8-10 should-trigger and 8-10 tricky
   should-not-trigger queries (near-misses with the neighbor skills).
5. **Record the change**: if trigger semantics or responsibilities changed,
   write an ADR in `docs/decisions/`. Always update the registry
   `.claude/skills/README.md` (when used / when not / last changed).
6. **Commit + push** via `session-protocol`.

## Description quality checklist

- Concrete trigger words, both languages, plus path/file names.
- An explicit "Do NOT use for" boundary naming the neighbor skill.
- A one-line statement of what the skill actually does.
- No secrets or real ARNs — placeholders only.

## Versioning

Skills live in git; history is the version log. Don't put version numbers in
skill names. A semantic change to triggers is a normal commit plus an ADR.
