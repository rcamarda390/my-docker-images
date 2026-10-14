# Shared security memory

Read this and `findings.json` before remediation or a version audit. Ledger
starts with all 67 component rows / 36 CVEs supplied for AgentMemory on
2026-10-14. It is not an exhaustive import of older reports. Add older/new
reports when reviewed; dated image notes remain the patch evidence.

## Agent process

1. Record every supplied finding. Group duplicate binary packages under their
   CVE/source package; retain reported score/CWE and supplied fix version.
   Record the scanned tag, digest and installed version. Missing means null.
2. Read existing image SECURITY notes, patches, Dockerfile and tests. Trace
   final-stage components, including vendored/static copies. Look up the
   shared component treatment before inventing another patch.
3. Check Debian suite status, linked bug, upstream fix commit and release.
   Prefer an official compatible fix; otherwise reuse a proven source patch.
   Record exact commit/checksum/version and each image's evidence separately.
4. Check every sibling image. Apply a fix only to proven affected code; a
   Debian package finding does not establish Alpine/Wolfi/UBI applicability.
   Removal needs that image's dependency/source/ELF checks and runtime tests.
5. Build through existing caller workflows. Verify actual final libraries,
   smoke/runtime checks and scan output. Record PR/run/tag/digest evidence.
6. Keep `scan_status: pending` until a post-build scan of that exact digest
   clears the finding. A downstream fix or applicability result stays distinct
   from scanner clearance. Never remove records when closed; keep history.
7. On remediation and upstream-version audits, recheck every pending entry,
   including downstream-patched and disputed issues. Update last_reviewed,
   official fix versions and remaining work. Retire a carry only after the
   replacement covers all hunks and existing regressions pass.

No scheduled job or automatic unreviewed patching is introduced.

## Sources for fixes and open issues

- [Debian Security Tracker](https://security-tracker.debian.org/tracker/)
- [Machine-readable tracker](https://security-tracker.debian.org/tracker/data/json)
- [Debian bugs](https://bugs.debian.org/) and [package tracking](https://tracker.debian.org/)
- [Debian sources](https://sources.debian.org/) and [snapshot](https://snapshot.debian.org/)
- [Debian security advisories](https://www.debian.org/security/)
- [glibc bugs](https://sourceware.org/bugzilla/) and [source](https://sourceware.org/git/?p=glibc.git)
- [GCC bugs](https://gcc.gnu.org/bugzilla/) and [source](https://github.com/gcc-mirror/gcc)
- [zlib issues](https://github.com/madler/zlib/issues)
- [coreutils bugs](https://debbugs.gnu.org/cgi/pkgreport.cgi?package=coreutils)
- Upstream project references: `../PROJECT_URLS.md`.

Check source-package pages for glibc, gcc-14, ncurses, zlib, acl, attr,
coreutils and dash. `no-dsa` means no scheduled Debian security advisory,
not fixed or harmless. Sid fixed packages are leads, not permission to mix
Sid libraries into Trixie. A compiled-template defect requires consumer work.

## Read-only check

Fetch one tracker snapshot and print suite status/fixed version for every
pending entry. This does not change the ledger, decide applicability or patch.
Missing records print UNKNOWN, never fixed. Network/JSON errors fail the command.

```bash
python tools/check-debian-security.py
```

For disconnected review, supply a previously downloaded tracker JSON:

```bash
python tools/check-debian-security.py --tracker-json /tmp/debian-security.json
```

## Cross-image review: 2026-10-14

| Runtime | Review result |
| --- | --- |
| AgentMemory | Existing glibc, ncurses, ACL, attr, coreutils, dash and zlib treatments preserved. No new source fix justified by repeated rows. |
| Headroom | Same glibc/dash carries; guarded removal of ncurses/ACL/attr/coreutils. Missing post-1.3.2 zlib patch identified and added. |
| Gnosis | Same glibc/dash carries; guarded removal of unused packages. zlib post-release patch already present. |
| Bifrost, ebay, socket proxy, Atlassian | Alpine runtime; Debian identity does not transfer. Native/vendored advisory applicability remains to be established from exact artifacts. |
| Zeus | UBI runtime; same CVE requires Red Hat/component review, not Debian version comparison. |
| LiteLLM, AI CLI runner | Wolfi runtime; review its package/vendor provenance separately. |
| Slim payload images | Scratch payloads; Debian builder packages do not automatically enter final images. Embedded native/static components still require artifact inspection. |

This is source-recipe review, not an inventory or clean-scan claim for every
published digest. Unverified cross-distro artifacts remain pending review.

## Open work

- Legacy glibc CVEs and coreutils CVE-2017-18018: no universal usable fix
  established; keep visible and recheck tracker/upstream.
- CVE-2026-102010: determine complete PBDS consumer provenance; rebuild any
  affected precompiled consumer. Sid gcc-14 14.4.0-3 alone cannot fix it.
- Applicability-only rows: retain tests/absence/architecture evidence, obtain
  scanner review; do not relabel them as package fixes.
- Every supplied row: scanned AgentMemory tag/digest/install versions missing;
  fresh Xray scan needed before clearance.

Agent: ChatGPT Work Codex /root. Model: GPT-6.
