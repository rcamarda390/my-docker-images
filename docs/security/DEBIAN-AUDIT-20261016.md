# Debian tracker and pin audit — 2026-10-16

Scope: current main, 37 saved Trixie CVE/source-package entries, Headroom, Gnosis and AgentMemory build recipes. Research only; no image changes, builds or clearance claims. Open PR #77 concerns Bifrost's Go dependency and does not overlap this audit.

## Results

The repository checker and a fresh official tracker JSON snapshot both report all 37 Trixie entries open with no fixed Trixie version. This does not mean all are unpatched in our images: downstream fixes and applicability evidence remain separate.

| Source | CVEs | Finding |
| --- | ---: | --- |
| glibc | 21 | Trixie 2.41-12+deb13u4 matches all three source pins. Sid 2.43-7 resolves many recent CVEs, but not seven legacy entries. Existing backports remain necessary pending hunk and regression verification of any replacement. |
| gcc-14 | 2 | Sid 14.4.0-3 fixes both CVE-2026-95619 and CVE-2026-102010; Trixie 14.2.0-19 remains open. Older notes saying no fix in any suite are superseded. PBDS templates require consumer provenance/recompilation, not simply replacing runtime shared libraries. |
| ncurses | 2 | Sid fixes exist. AgentMemory already rebuilds 6.6+20260608-2, newer than both fixed versions. Other images use guarded removal. |
| acl / attr | 3 | Sid ACL 2.4.0-1 and attr 1:2.6.0-1 fix these; AgentMemory already rebuilds those sources. Trixie tracker says point-release update is intended, not individual backports. |
| zlib | 2 | 1.3.2 resolves CVE-2026-27171 but needs commit df84af25dc1942490e1d1c899a07619152a46148 for CVE-2026-85091. All three recipes carry that checksum-pinned patch. Upstream latest release is still 1.3.2. |
| dash | 2 | Trixie and Sid both 0.5.12-12, unfixed. Recipes rebuild with libc fnmatch and assert linkage. No newer official package to adopt. |
| coreutils | 4 | Trixie 9.7-3 and Sid 9.10-1 remain open in tracker. AgentMemory carries uniq/sort backports; Headroom/Gnosis use guarded removal. No official replacement demonstrated. |
| bzip2 | 1 | No Debian fix; upstream fix concerns bzip2recover. Preserve Python bz2 requirements and CLI absence evidence; library association alone is not proof of vulnerable runtime code. |

## Pin audit and plan critique

- No apt-mark hold, snapshot repository, or apt preference lock was found in the three reviewed image directories. Their runtime recipes run apt-get update and upgrade.
- Exact glibc/dash source pins and AgentMemory coreutils pin currently match available Trixie sources. No missed newer Trixie fix was established for these saved CVEs.
- Runtime upgrade is followed by explicit installation of custom glibc/dash packages. Exact-version assertions in Headroom/Gnosis and custom package versions make this a future maintenance hazard. A later Debian update can be rejected, require downgrade handling, or remain below a locally versioned carry. Do not solve this by blindly deleting pins or changing assertions to >=: a numerically newer version need not contain our extra patches.
- Source-package versions pinned to moving Debian mirrors may eventually disappear. A missing-source build failure is reproducibility drift, not evidence the service needs a new vulnerability patch.
- AgentMemory uses node:26-slim without an explicit suite suffix while native builders explicitly use Trixie. Future tag suite drift could mix ABI/package families. Recommend checking Debian VERSION_CODENAME at build time or using a verified matching suite tag when implementing the next image change; current runtime artifact suite was not inspected here.
- Gnosis already uses minimum-version floors for OpenSSL, PCRE2 and gzip, allowing newer compatible Debian revisions. Retain this pattern where there are no downstream carries.
- Newer is not automatically safer: upgrading zlib into the 1.3.2 line also introduces the nonblocking gzwrite defect unless its post-release patch is retained. Current recipes retain it.
- Do not import Sid glibc or GCC runtime packages into Trixie just to change scanner matches. Rebuild compatible source when justified and verify real consuming artifacts.

Recommended implementation order: (1) finish PBDS consumer provenance work; (2) add a narrow stale-source/carry review check that flags newer Trixie source candidates without applying them; (3) when an official candidate appears, compare all carried hunks, run existing regressions, then advance pins and rebuild only affected images. No rebuild is justified solely by this tracker refresh.

## Limits and sources

The existing checker reports only the configured suite, so it misses Sid replacement leads unless explicitly reviewed. The ledger now retains both Trixie and Sid tracker results for this review. No previous tracker snapshot was available to establish when a Sid fix first appeared. Some linked Debian BTS pages could not be retrieved; tracker notes and source references were available. This is not a complete inspection of every upstream bug discussion or final published binary.

- https://security-tracker.debian.org/tracker/data/json
- https://security-tracker.debian.org/tracker/source-package/glibc
- https://security-tracker.debian.org/tracker/source-package/gcc-14
- https://security-tracker.debian.org/tracker/source-package/ncurses
- https://security-tracker.debian.org/tracker/source-package/acl
- https://security-tracker.debian.org/tracker/source-package/attr
- https://security-tracker.debian.org/tracker/source-package/coreutils
- https://security-tracker.debian.org/tracker/source-package/dash
- https://security-tracker.debian.org/tracker/CVE-2026-102010
- https://security-tracker.debian.org/tracker/CVE-2026-85091
- https://security-tracker.debian.org/tracker/CVE-2026-42250
- https://github.com/madler/zlib/releases

Verification: ran tools/check-debian-security.py successfully; independently fetched tracker JSON and matched all 37 Trixie rows and Sid statuses; inspected Dockerfiles, manifests, native source preparation, runtime regressions, shared policy/methodology and image workflows. Scan statuses unchanged. Uploaded build-airgap-tarball.txt describes unrelated npm/GitHub binary packaging and was not applied to Debian remediation.

Agent: ChatGPT Work Codex /root. Model identifier unavailable.
