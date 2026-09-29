# Gnosis 0.14.1-v12 Xray remediation

Evidence: user-supplied Xray screenshot, reviewed 2026-09-14. All nine rows
are HIGH (CVSS 7.0–7.9); the dashboard groups Critical and High together.
Every row reports `N/A` for Fix Version. No image digest or layer path was
provided. These are Debian base-image packages, not Python dependencies.

## Finding ledger

| CVE | Installed component/version | CVSS | Change / disposition |
| --- | --- | --- | --- |
| CVE-2026-54369 | libacl1 2.3.2-2+b1 | 7.1 | Rebuild ACL 2.4.0-1 on Trixie; retain library and exercise coreutils/tar callers. |
| CVE-2026-5435 | libc-bin 2.41-12+deb13u4+rcamarda1 | 7.3 | Existing upstream backport retained in the coherent libc6/libc-bin rebuild. Scanner recognition remains unconfirmed. |
| CVE-2025-69720 | ncurses-bin 6.5+20250216-2 | 7.8 | Rebuild ncurses 6.6+20260608-2; upgrade installed sibling libraries and terminfo together. |
| CVE-2026-85091 | zlib1g 1:1.3.dfsg+really1.3.1-1+b1 | 7.4 | Unresolved: no confirmed Debian fix. Retain Python's required zlib library. |
| CVE-2026-78410 | liblastlog2-2 2.41.5-0+deb13u1 | 7.8 | Rebuild util-linux 2.41.6 with Trixie packaging; upgrade all installed siblings. |
| CVE-2026-76642 | util-linux 2.41.5-0+deb13u1 | 7.8 | Same util-linux 2.41.6 rebuild. |
| CVE-2026-78409 | libuuid1 2.41.5-0+deb13u1 | 7.0 | Same rebuild. Upstream's affected range is >=2.42; this row is a candidate applicability mismatch, not confirmed scanner clearance. |
| CVE-2026-78408 | liblastlog2-2 2.41.5-0+deb13u1 | 7.9 | Same util-linux 2.41.6 rebuild. |
| CVE-2026-54371 | libattr1 1:2.5.2-3 | 7.1 | Rebuild attr 1:2.6.0-1 on Trixie; retain the library. Advisory describes CLI tools, but upgrade the source family. |

## Primary sources and limitations

- [Debian ACL tracker](https://security-tracker.debian.org/tracker/CVE-2026-54369): fixed in 2.4.0-1; Trixie has no DSA. New ABI can conflict with existing callers, so final-image tests exercise tar and cp.
- [Debian attr tracker](https://security-tracker.debian.org/tracker/CVE-2026-54371): fixed in 1:2.6.0-1; Trixie has no DSA. Use the complete release, not a partial walk-tree backport.
- [Debian ncurses tracker](https://security-tracker.debian.org/tracker/CVE-2025-69720): fixed from 6.6+20251231-1. The selected 6.6+20260608-2 exceeds that floor. Compilation and packaging must be verified in our Docker environment.
- [util-linux 2.41.6 release notes](https://github.com/util-linux/util-linux/blob/v2.41.6/Documentation/releases/v2.41.6-ReleaseNotes): stable-branch security fixes for 76642, 78410 and 78408.
- [Upstream 78409 advisory](https://github.com/util-linux/util-linux/security/advisories/GHSA-8f2p-47x3-43mv): affected >=2.42; lists 2.41.6 and 2.42.3 as patched releases.
- [Debian glibc tracker](https://security-tracker.debian.org/tracker/CVE-2026-5435): stock Trixie remains affected. Existing checked-in patch identifies upstream 2.41 commit 0e8c56b386d72ba2ddf15784423f2e894c63a241. A custom package revision alone does not prove Xray recognizes the backport.
- [Debian zlib tracker](https://security-tracker.debian.org/tracker/CVE-2026-85091) lists all suites as unfixed. Its description names upstream 1.3.1.2–1.3.2 while the package table also flags Trixie's 1.3.1. [Upstream issue 1310](https://github.com/madler/zlib/issues/1310) remains open. Do not infer a fixed version, purge zlib, or suppress this finding. This discrepancy needs upstream resolution or source-level applicability proof.

## Build and verification

`prepare-native-sources.sh` downloads checksum-pinned original and Debian
packaging archives. It uses Trixie's util-linux packaging because sid requires
newer build tooling; the real upstream source advances to 2.41.6. Only two
already-upstreamed Debian patches are dropped, after reverse-application
checks prove both are present. Every other Debian patch is applied normally.
The script updates changelogs with honest `+rcamarda1` rebuild versions.

The Docker build installs build dependencies exclusively from Trixie and
runs normal package tests except ACL's suite. ACL 2.4.0's
`test/root/permissions.run` assumes Bash-only `shopt` behavior and access to
a block device; both fail under Docker's `/bin/sh` and device sandbox before
package installation. ACL is therefore built with `DEB_BUILD_OPTIONS=nocheck`
only. Runtime installation selects only packages already installed in the base
image.
Sibling packages from the same source are upgraded together; no package is
purged by this change. Both Python stages explicitly use the Trixie variant.

Final-image verification checks source-package version floors for every
installed sibling, Python UUID/zlib/gzip, native library loading, ACL-aware
tar/cp operations and infocmp. Existing Bash/curses/readline, SQLite FTS5,
sqlite-vec, dependency floors, and Gnosis import checks remain in place.

Local validation completed: all eight archive checksums, both reverse-patch
checks, all retained Debian source patches, generated changelog versions,
shell syntax for all 12 Dockerfile RUN instructions, and Python compilation.
The version guard correctly rejects the workspace's older util-linux 2.39.3;
this is a negative control, not a successful image runtime test. Docker/Podman/Buildah are
unavailable in this workspace. Full package compilation, image build, offline
smoke test and Trivy/Xray rescan are **pending**. Do not treat this as a clean
image or merge based only on source preparation. The blocking scan is retained.

## Relationship to prior work

PR #277 is still open. This branch includes its existing commits unchanged so
the v12 glibc, PyJWT, PCRE2/gzip, and highest-published-revision fixes are not
lost. The new work changes only the Gnosis image directory. No new revision
bump, publishing workflow, scan suppression, merge or publication is included.

Rollback: revert the new Gnosis native-package commit; preserve #277's fixes.
No database format or persistent volume migration is introduced.

Agent: Codex. Model: not exposed by this runtime.

## Repeated ncurses packaging failure (2026-09-14)

Run [34868335565](https://github.com/rcamarda390/fib_docker/actions/runs/34868335565/job/104057761602)
checked out ac30308502e0e33a99ad4d337a0a0924e7f6e840 and built
6.6+20251231-1+rcamarda1. It reproduced the missing rxvt-unicode and
rxvt-unicode-256color files from the preceding 6.6+20260608 build.
The earlier claim that the downgrade solved a Trixie toolchain incompatibility
was not supported. It is withdrawn.

The log shows Debian compiling with --disable-setuid-environ and invoking
its staged tic with only TERMINFO to choose the destination. The build runs
as real root. [ncurses documents](https://invisible-island.net/ncurses/man/ncurses.3x.html#h2-ENVIRONMENT)
that privileged execution can ignore TERMINFO.
The [tic -o option](https://invisible-island.net/ncurses/man/tic.1m.html)
explicitly selects the output database.

The preparation script now adapts that exact Debian tic invocation to pass
-o "$(CURDIR)/debian/tmp/usr/share/terminfo". Pre/post match-count assertions
fail if the expected recipe changes. No manifest entries are deleted and
no ncurses security flags or test gates are disabled. The ineffective
downgrade is undone, restoring the original checksum-pinned 6.6+20260608-2
sources and consistency with the unchanged runtime security version floor.

The final-image test now requires nonempty xterm and both rxvt-unicode files
and decodes them with infocmp -A against the explicit package directory.
This extends the existing runnable image-build verification.

Validation this follow-up: compared the logged command with the replacement,
checked source/runtime version alignment, and read back committed files.
No shell/Docker execution or fresh workflow-dispatch tool is exposed in this
session. Source patch application, complete compilation, runtime tests and
scan remain pending a NEW run of the existing Gnosis workflow on this branch.
Rerunning the old failed job would rebuild its old commit.

Agent: Codex. Model: GPT-5.
