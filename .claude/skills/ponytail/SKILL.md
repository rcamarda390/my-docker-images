---
name: ponytail
description: Lazy-senior-dev discipline for code changes. Use when writing, editing, reviewing or planning code, config, Dockerfiles, workflows or scripts, to keep diffs small, reuse existing code, and verify non-trivial logic.
---

# Ponytail: lazy means efficient, not careless

The best code is the code that never needed to be written.

## Priority order when rules conflict

1. Correctness
2. Security and data safety
3. User request
4. Root cause over symptom
5. Existing project patterns
6. Small readable diff
7. Verification

Investigate wide. Change narrow.

## Before writing code

Read the task fully. Read the code it touches. Trace the real flow end to end.
Check relevant callers. Ask only when ambiguity changes behavior, scope,
compatibility, security or data safety. Otherwise state the safest assumption
and continue.

## Stop at the first rung that works

1. Does this need to be built at all?
2. Does this codebase already have it? Reuse the helper or pattern.
3. Does the standard library do it?
4. Does a native platform feature cover it?
5. Does an already installed dependency solve it?
6. Write the smallest clear code that works.
7. Add a new dependency only when required.

Do not rewrite an existing helper. Do not add a new tool when an existing one works.

## Fix root cause, not symptoms

Grep every caller before choosing where a fix belongs. Fix shared code once when
the invariant belongs there. Do not force a shared fix onto callers that need
different behavior.

## Keep scope tight

Touch only what the task requires. No extra features, unrelated cleanup,
drive-by formatting or refactors. Match existing project style. Mention unrelated
dead code instead of deleting it. Remove only code your change makes obsolete.
Deletion beats addition within scope.

## Keep code simple

No abstractions, flexibility or config that was not requested. No defensive
handling for states an enforced invariant already rules out.

Not lazy about: input validation at trust boundaries, error handling that
prevents data loss, security, accessibility, and calibration real systems need.

Mark intentional shortcuts with a `ponytail:` comment naming the ceiling and
the upgrade path, unless the limitation is already obvious.

## Verify by risk

Non-trivial logic leaves one runnable check behind: the smallest thing that
fails if the logic regresses. No new test framework unless one is in use.
Trivial one-line edits need no test. Security, authorization, deletion,
migration, persistence and data-integrity changes are never trivial.

## Surface tradeoffs

When real alternatives exist, name them briefly, state the tradeoff, recommend
one. Do not silently pick the riskier path. Push back on unnecessary work.

## Final check before stopping

- Correct problem solved, root cause addressed.
- Existing code reused where appropriate.
- Diff no larger than necessary; no unrelated code changed.
- No avoidable dependency added.
- Verification matches actual risk.
- User request fully satisfied.
