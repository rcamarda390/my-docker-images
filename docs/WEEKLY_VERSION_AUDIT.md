# Weekly Docker and tool version audit

## Schedule

- Frequency: Weekly, Monday at 7:00 AM America/New_York (Eastern; DST-aware).
- Execution: ChatGPT cloud scheduled task, separately configured; this document does not create or activate it.
- Mode: Read-only; **do not** edit image versions, create PRs, merge PRs, run builds, or publish images.
- Repository: https://github.com/rcamarda390/my-docker-images (default branch).
- References: [PROJECT_URLS.md](PROJECT_URLS.md), image manifests, Dockerfiles, lockfiles, workflows and release notes.

## Audit inventory

| Image | Check |
| --- | --- |
| agentmemory-server / agentmemory-mcp | AgentMemory upstream release, lockfile and iii compatibility |
| ai-cli-runner | Claude Code CLI **and** Cline CLI independently, comparing package versions and locks |
| bifrost-mcp | Bifrost transports release stream, commit pin and downstream patches |
| gnosis-mcp | Nicholas Glazer GitHub releases/tags are the only upstream; image version must equal the latest GitHub release (ignore unreleased `main` commits) |
| headroom-mcp | Headroom release, commit pin and security patches |
| slim-archify | Archify stable release, commit pin and runtime Node compatibility |
| slim-docker-codeburn | CodeBurn upstream, Marketplace VSIX version and remediated payload |
| sooperset-mcp-atlassian | Sooperset MCP Atlassian release, not official Atlassian Rovo MCP |
| zeus-dev-image | Component-level inventory from Dockerfile, not a single composite version |

Include any newly added image named above even if its path changes. Report missing images as unverified rather than silently dropping them.

## Weekly report contract

For each component, provide: image/component, current pinned version, latest applicable **stable** upstream version, release date, upstream release URL, status (**current / update available / blocked / unverified**), notable security fixes, breaking changes, local-patch or dependency implications, and recommendation (**update / hold / no change / investigate**). Do not invent version comparisons when the source is unavailable. Separate release availability from build safety and from Xray scan clearance.

Flag active and existing candidate PRs to avoid duplicated work. Link relevant GitHub Actions and PRs if known. Provide a short executive summary first, prioritize actionable/security changes, and note prior audit changes when available. Use source GitHub tags/releases, npm stable dist-tags and VS Code Marketplace releases as appropriate. Check manifests/lockfiles first; never rely on Docker tags alone.

## Interaction with existing automation

- Existing `.github/workflows/check-upstream-versions.yml` runs Monday 08:00 UTC and can create manifest-only candidate PRs for five selected images.
- Existing `.github/workflows/check-ai-cli-versions.yml` runs Monday 09:00 UTC and can create CLI version-bump PRs.
- These jobs may overlap with the audit and are **not** safe build/test evidence. The audit must observe, not duplicate, their mutations.
- To prevent false alerts, use the latest main-branch pins and note pending PR versions separately.

## Limitations and decision gate

ChatGPT Tasks scheduling is independent from this Markdown document. Activating it requires a separate task creation. This plan tracks versions but cannot certify federal/FIPS suitability, supply-chain provenance or remediation of vulnerability scanner findings. Upgrades require manual review, build, runtime smoke checks, compatibility checks and Artifactory Xray validation before merging/publishing.

## Maintainer

Prepared by OpenAI GPT-6 assistant, 2026-10-14. Documentation-only change.
