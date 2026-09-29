# Agent Review Reply — fib_docker Build Methodology Handoff

**Date:** 2026-08-01
**Reviewer:** Copilot Code Agent
**Subject:** Review of "fib_docker Build Methodology Handoff" instruction document
**Requesting:** Gap resolution answers + updated plan as `docs/build-methodology-plan-v2.md`

---

## Summary

The handoff document's intent is correct and the direction is sound. After inspecting the live
repository tree, all five active workflow files, and all Dockerfiles, the following findings
and critiques require resolution before implementation can proceed cleanly.

---

## Findings — Actual Repository State

The handoff document describes the repo as if workflows live at the root and `.github/workflows/`
is mostly empty. **This is incorrect.** The actual state is:

| File | Location | Status |
|------|----------|--------|
| `build-agentmemory.yml` | `.github/workflows/` | Active — push-triggered, Docker Hub only |
| `build-iii-engine.yml` | `.github/workflows/` | Active — push-triggered, Docker Hub only |
| `build-agentmemory-mcp-all.yml` | `.github/workflows/` | Active — `workflow_dispatch` combo trigger, Docker Hub only |
| `build-gnosis-mcp.yml` | `.github/workflows/` | Active — `workflow_dispatch`, uses `-airgap` tag suffix, Docker Hub only |
| `dockerhub.yml` | `.github/workflows/` | Active — builds root `Dockerfile`, pushes `fib_docker:build-<N>` and `:latest` |
| `build-agentmemory-mcp-all.yml` | repo root | Legacy copy — not active |
| `build-gnosis-mcp.yml` | repo root | Legacy copy — not active |
| `build-iii-engine.yml` | repo root | Legacy copy — not active |

The active system **already lives under `.github/workflows/`**.
The root-level files are draft/legacy copies and can be removed without risk.

Additionally, the tag format for `agentmemory` and `iii-engine` **already matches** the target
(`<version>-v<N>`). The primary tagging offenders are:
- `build-gnosis-mcp.yml` — uses `-airgap-v2`, `-latest-airgap`
- `dockerhub.yml` — uses `build-<run_number>`

---

## Critique — Errors in the Handoff Document

### 1. Root-level files described as "the active system"

> *"Root-level workflow files are legacy or misplaced and should not remain the active system."*

This is backwards. The root-level files are already the legacy copies. The active system
is already under `.github/workflows/`. The handoff document should not imply otherwise,
as it risks the implementer auditing and rewriting the wrong files.

### 2. `dockerhub.yml` is not mentioned

The `dockerhub.yml` workflow is active, uses a `build-<N>` tag suffix, and is one of
the acceptance criteria violations. It is entirely absent from the handoff document.
This must be explicitly addressed.

### 3. Tag format problem is overstated for agentmemory and iii-engine

Both images already produce `<version>-v<N>` tags in the active workflows. The tag
migration work is limited to `gnosis-mcp` and `dockerhub.yml`.

---

## Gaps Requiring Decisions Before Implementation

The following are open design questions. The implementer cannot safely proceed without
answers. Please provide a resolution for each.

---

### Gap 1 — Revision increment ownership

**Current behavior:** The workflow auto-reads the current revision from `ARG` lines in the
Dockerfile, increments it, writes it back, and commits to the repo via `git push`.

**Proposed behavior:** Revision is read from `images/<name>/image.yaml`. But the document
does not say who or what increments it.

**Options:**
- A) Human manually edits `image.yaml` before triggering a build (simpler, but regression in automation).
- B) The reusable workflow still auto-increments and commits `image.yaml` back to the repo (matches current behavior, more complex in the reusable workflow).
- C) Remove auto-increment; revision is always explicitly set by the operator at dispatch time (clearest, but requires operator discipline).

**Please choose one.**

---

### Gap 2 — `image.yaml` schema — image-specific build args

The proposed schema is:

```yaml
name: agentmemory
upstream_version: 0.9.28
revision: 3
```

This schema cannot express gnosis-mcp's required build args:
- `EMBED_MODEL` (HuggingFace path, defaults to `MongoDB/mdbr-leaf-ir`)
- `EXTRAS` (pip extras group, defaults to `embeddings`)
- `PYTHON_VERSION` (defaults to `3.13`)

**Proposed addition:**

```yaml
name: gnosis-mcp
upstream_version: 0.13.3
revision: 9
build_args:
  EMBED_MODEL: "MongoDB/mdbr-leaf-ir"
  EXTRAS: "embeddings"
  PYTHON_VERSION: "3.13"
```

**Question:** Should the schema support a `build_args` map for image-specific Dockerfile
`ARG` values? Or should gnosis-mcp be treated as a special case outside the reusable workflow?

---

### Gap 3 — gnosis-mcp air-gap tag semantics

The gnosis-mcp Dockerfile pre-bundles a 300+ MB ONNX model at build time. The `-airgap`
suffix in the current tag is not naming drift — it is a meaningful distinction that tells
consumers this variant ships without requiring network access to HuggingFace at runtime.

Removing `-airgap` silently breaks any downstream consumer relying on that suffix to
select the correct image variant.

**Options:**
- A) Keep a variant tag or descriptor (e.g. `gnosis-mcp:0.13.3-v9-airgap` or a separate
  image name `gnosis-mcp-airgap`). This preserves consumer contracts.
- B) Rename the image to `gnosis-mcp` with no suffix, and document that all published
  builds are the air-gap variant. Update the `image.title` label accordingly.
- C) Both variants will eventually exist; defer this question and build only the air-gap
  variant for now using option B's naming, with a note to revisit when a non-air-gap
  variant is created.

**Please choose one.** If B or C, confirm that the gnosis-mcp Dockerfile `LABEL` should
be updated to remove the `airgap` marker or replace it with a clearer label.

---

### Gap 4 — `workflow_call` permissions declaration

When using `workflow_call`, the reusable workflow's effective permissions are bounded by
the calling workflow's declared permissions. If the calling workflow does not declare
`packages: write`, the GHCR push step in the reusable workflow will fail with a 403.

**Question:** Should calling workflows be required to declare `packages: write` themselves,
or should the reusable workflow use a `secrets: inherit` + `permissions: write-all` pattern
to avoid the caller having to know about this?

**Recommended resolution:** Calling workflows declare:
```yaml
permissions:
  contents: write
  packages: write
```
The reusable workflow does the same, making both explicit. Confirm or override.

---

### Gap 5 — `vars.DOCKERHUB_USERNAME` vs `secrets.DOCKERHUB_USERNAME`

All current workflows use `secrets.DOCKERHUB_USERNAME`. The handoff document says
"use `vars.DOCKERHUB_USERNAME` if available" — which implies a conditional fallback that
would require runtime branching logic.

A username is not a secret. It should live in `vars.*`.

**Recommended resolution:** Migrate `DOCKERHUB_USERNAME` to a repository variable
(`vars.DOCKERHUB_USERNAME`) and update all references. Remove the "if available" hedge.

**Question:** Confirm this is correct, and confirm that the `vars.DOCKERHUB_USERNAME`
repository variable will be set before workflows run.

---

### Gap 6 — Combo workflow vs. individual per-image workflows

There are currently two overlapping trigger paths:
- `build-agentmemory.yml` + `build-iii-engine.yml` handle push-triggered builds individually
- `build-agentmemory-mcp-all.yml` handles manual dispatch for both images together

Under the new model with a reusable `build-image.yml`:

**Options:**
- A) Keep individual per-image caller workflows (one per image), delete the combo workflow.
  Push triggers live in each individual caller.
- B) Keep the combo workflow as the single caller for agentmemory and iii-engine, remove
  the individual push-triggered workflows. Use `workflow_dispatch` only, no push triggers.
- C) Keep both patterns — individual workflows for push triggers, combo for manual batch dispatch.

**Please choose one.** Option A is the simplest and most aligned with the stated goal.

---

### Gap 7 — `latest` tag policy

Current behavior:
- `agentmemory` → pushes `latest` ✓
- `iii-engine` → does **not** push `latest`
- `gnosis-mcp` → pushes `latest-airgap` (non-standard)
- `fib_docker` (dockerhub.yml) → pushes `latest`

**Question:** Should every image push a `latest` tag on successful build? Or only images
that are explicitly designated as "stable"? The reusable workflow needs a clear policy.

**Recommended resolution:** Push `latest` to both registries on every successful build
of the default branch. Opt-out can be added later per image via `image.yaml`.

---

### Gap 8 — Smoke test hook interface

Each image has a different smoke test invocation:
- `iii-engine`: `docker run ... iii-engine --version`
- `agentmemory`: `docker run ... node -e "console.log('agentmemory image OK')"`
- `gnosis-mcp`: `docker run ... gnosis-mcp check`

**Question:** How should the reusable workflow support per-image smoke tests?

**Options:**
- A) The reusable workflow accepts a `smoke_test_cmd` string input; calling workflows pass
  the command. The reusable workflow runs `docker run --rm <image> ${{ inputs.smoke_test_cmd }}`.
- B) Smoke tests stay in individual per-image caller workflows, run after `workflow_call` returns.
- C) Skip the smoke test hook in the reusable workflow; move all smoke tests to a separate
  dedicated workflow.

---

### Gap 9 — `dockerhub.yml` fate

This workflow:
- Builds the **root** `Dockerfile` (not any MCP image)
- Pushes `rcamarda390/fib_docker:build-<N>` and `:latest`
- Has no GHCR publish
- Is triggered on every push to `main`

It is the only active workflow still using a `-build-*` tag. The handoff document does not
address it.

**Options:**
- A) Retire `dockerhub.yml` entirely — the root `Dockerfile` has no clear MCP purpose.
- B) Migrate it to the reusable workflow with image name `fib-docker` and standardized tags.
- C) Leave it as-is outside the new standardized system, documenting it as unrelated to MCP images.

**Please advise.** If A, confirm the root `Dockerfile` can be removed or archived.

---

## Action Requested

1. **Answer each of the nine gaps above** with a chosen option or explicit direction.
2. **Produce an updated plan** at `docs/build-methodology-plan-v2.md` that:
   - Corrects the current-state description (active workflows are already under `.github/workflows/`)
   - Incorporates your answers to each gap
   - Updates the `image.yaml` schema to include `build_args`
   - Lists the `dockerhub.yml` explicitly with a disposition
   - Specifies the `workflow_call` permissions pattern
   - States the `latest` tag policy
   - Describes the smoke test hook interface chosen
   - Has a revised, sequential execution order reflecting the above
   - Has a revised acceptance criteria list that is testable and unambiguous

The updated plan should be self-contained and ready to hand to an implementer without
requiring them to read this review document.

---

## Reference — Current Verified Image Versions

| Image | Upstream version | Current image revision |
|-------|-----------------|----------------------|
| `agentmemory` | `0.9.28` | `v4` |
| `iii-engine` | `0.22.0` | `v9` |
| `gnosis-mcp` | `0.13.3` | `v9` (airgap) |

These values should seed the initial `image.yaml` files.
