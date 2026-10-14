---
name: remediate-xray
description: Remediate and persist Xray or Trivy Docker-image findings in rcamarda390/my-docker-images. Use when the user provides security findings, requests shared-component patch reuse across images, asks to recheck open vulnerabilities for fixes, or supplies a post-build scan for reconciliation.
---

# Remediate Xray Docker findings

## Load the current repository process

Use the configured GitHub plugin for
https://github.com/rcamarda390/my-docker-images.
Read the current default branch and relevant open PRs before changes.
If the shared security process is still in an open PR, read and extend that
branch rather than creating overlapping remediation work. Initially it is
PR #62; verify its current state instead of assuming it remains open.

Read these repository files before acting:

- `docs/AGENT_INSTRUCTIONS.md`: authoritative repository policy.
- `docs/security/README.md`: authoritative intake, sibling-review and recheck process.
- `docs/security/findings.json`: persistent finding and patch memory.
- Target Dockerfile, image.yaml, startup scripts, dated SECURITY notes,
  patches, tests and image-specific/shared build workflows.

Keep policy and detailed process in those files. Do not create a second ledger
or copy historical package versions into this skill. If the security files are
absent from main, find their open PR. If no source exists, report the blocker.

## Execute the requested operation

For a new report, follow the shared process end to end:

1. Capture every row and report identity. Preserve original CVSS vector,
   score, CWE, component and supplied fix version when provided. Add report
   observations for later scans instead of overwriting the original intake.
   Leave missing installed versions, tags and digests null; continue useful
   source research without claiming artifact identity or clearance.
2. Reconcile each CVE/source package with existing records and dated evidence.
   Separate an already-carried source fix from what the scanned image contains.
3. Verify current Debian/upstream fixes and open issues through the process
   references. Reuse compatible patches, checksums and regressions. Prefer
   removing proven-unused components, otherwise patch or replace as justified.
   Preserve required libraries and normal service behavior.
4. Inspect every sibling final runtime and vendored/static copy for that CVE.
   Record proven affected, already patched, removed, not applicable or
   unknown separately. Reuse a fix only after source/ABI compatibility proof.
5. Make the smallest reproducible build change and update the shared ledger,
   report history, per-image evidence and unresolved work in the same PR.
   Preserve existing workflow/tag rules. Reuse an overlapping open PR.
6. Run meaningful checks and existing image CI. Inspect failures and fix their
   root cause. Record exact commit, run, tag and digest when available.
   Do not merge/publish unless the user has authorized it in the session.
7. Report PR, validation/build state, actual remediations and remaining issues
   briefly. Claim Xray clearance only from a post-build scan of the exact digest.

For an open-fix audit, run `tools/check-debian-security.py` from the
repository root. Review tracker, linked bugs and upstream releases for every
pending entry, including downstream-fixed records. Record the review date,
new official fix versions and replacement candidates. Keep existing carries
until the replacement covers their hunks and regressions pass.

For a post-build scan, match its immutable tag/digest and compare against the
previous observation. Mark cleared rows only for that artifact. Record
remaining/moved rows and reopen regressions. Keep historical records.

## User input

Accept pasted tables, screenshots or reports plus an image name.
Ask only when missing information changes the safe implementation.
A missing digest prevents clearance, not intake/research.
Use Headroom's `images/headroom-mcp/` and AgentMemory's
`images/agentmemory-server/`; preserve manifest image names.
