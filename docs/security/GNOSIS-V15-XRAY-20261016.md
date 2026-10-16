# Gnosis v15 Xray reconciliation — 2026-10-16

## Intake and comparison

The user supplied 28 component rows / 26 CVEs for Gnosis 0.17.5-v15 in this conversation. All CVE/component pairs match the saved October 14 Gnosis intake. There are no new or absent pairs. Preserve the original intake and this new observation separately, including the user's exact CVSS strings, CWE values, and blank fix/installed versions.

The scanned digest is unknown. The successful v15 publication log records manifest sha256:9b738800e09206c0ccc4d0fc0de819dfa679c84429111b5d42944f6300276c06 from source commit 76a31211735e068b57f914f44b5274afc20eb8ff:
https://github.com/rcamarda390/my-docker-images/actions/runs/38784810311

This publication digest must not be substituted for the missing scan digest. All 28 rows remain reported; no Xray clearance is claimed.

| Source disposition | Component rows | Distinct CVEs |
| --- | ---: | ---: |
| Carried source corrections or regex mitigation | 16 | 16 |
| Existing applicability evidence, not a package-version fix | 5 | 4 |
| Unresolved/no usable fix established | 7 | 6 |

## Per-CVE disposition

| CVE | Reported components | Current evidence / next action |
| --- | --- | --- |
| CVE-2019-1010022 | libc6 | No verified safe universal source fix established; keep visible. A glibc 2.43 upgrade does not resolve this legacy entry. |
| CVE-2019-1010023 | libc6 | No verified safe universal source fix established; keep visible. A glibc 2.43 upgrade does not resolve this legacy entry. |
| CVE-2026-95619 | libgcc-s1, libstdc++6 | AMD64 posix_memalign path and actual aligned-new regression support non-applicability; no scanner clearance. |
| CVE-2026-19499 | libc6 | Existing checksum-pinned glibc backport retained in v15; official Trixie package remains open. Reuse source/runtime evidence before changing the carry. |
| CVE-2018-20796 | libc6 | 64-frame recursion mitigation carried and final C-locale regression passed in v15. Keep tradeoff and pending scan status. |
| CVE-2019-9192 | libc6 | 64-frame recursion mitigation carried and final C-locale regression passed in v15. Keep tradeoff and pending scan status. |
| CVE-2026-5435 | libc6 | Existing checksum-pinned glibc backport retained in v15; official Trixie package remains open. Reuse source/runtime evidence before changing the carry. |
| CVE-2026-102010 | libstdc++6, libgcc-s1 | Header/template issue; no affected ONNX consumer established. See PBDS-CONSUMERS-20261016.md. Shared-library substitution cannot repair precompiled templates. |
| CVE-2026-6238 | libc6 | Existing checksum-pinned glibc backport retained in v15; official Trixie package remains open. Reuse source/runtime evidence before changing the carry. |
| CVE-2026-85670 | tokenizers | Patched 0.23.1+rcamarda1 wheel; malformed merges and real offline embedding pass. Latest 0.23.3 still has the defective writes; retain patch. |
| CVE-2026-86805 | libc6 | Existing checksum-pinned glibc backport retained in v15; official Trixie package remains open. Reuse source/runtime evidence before changing the carry. |
| CVE-2026-80489 | libc6 | Existing checksum-pinned glibc backport retained in v15; official Trixie package remains open. Reuse source/runtime evidence before changing the carry. |
| CVE-2026-77117 | libc6 | Existing checksum-pinned glibc backport retained in v15; official Trixie package remains open. Reuse source/runtime evidence before changing the carry. |
| CVE-2026-19542 | libc6 | Existing checksum-pinned glibc backport retained in v15; official Trixie package remains open. Reuse source/runtime evidence before changing the carry. |
| CVE-2026-102473 | dash | Dash rebuilt with libc fnmatch; symbol assertion plus bounded malicious/ordinary matching checks pass. |
| CVE-2026-8674 | libc6 | Existing checksum-pinned glibc backport retained in v15; official Trixie package remains open. Reuse source/runtime evidence before changing the carry. |
| CVE-2019-1010025 | libc6 | No verified safe universal source fix established; keep visible. A glibc 2.43 upgrade does not resolve this legacy entry. |
| CVE-2019-1010024 | libc6 | No verified safe universal source fix established; keep visible. A glibc 2.43 upgrade does not resolve this legacy entry. |
| CVE-2026-18374 | libc6 | Existing checksum-pinned glibc backport retained in v15; official Trixie package remains open. Reuse source/runtime evidence before changing the carry. |
| CVE-2026-89092 | libc6 | nscd service is absent; retain absence assertion, no blanket libc fix claim. |
| CVE-2026-102474 | dash | Pinned dash 0.5.12 source lacks the affected Unicode encoder; literal-escape regression retained. |
| CVE-2026-97399 | libc6 | Power8-specific implementation; published target is linux/amd64. |
| CVE-2026-95818 | libc6 | Existing checksum-pinned glibc backport retained in v15; official Trixie package remains open. Reuse source/runtime evidence before changing the carry. |
| CVE-2026-6791 | libc6 | Existing checksum-pinned glibc backport retained in v15; official Trixie package remains open. Reuse source/runtime evidence before changing the carry. |
| CVE-2010-4756 | libc6 | No verified safe universal source fix established; keep visible. A glibc 2.43 upgrade does not resolve this legacy entry. |
| CVE-2026-6368 | libc6 | Existing checksum-pinned glibc backport retained in v15; official Trixie package remains open. Reuse source/runtime evidence before changing the carry. |

## What the successful build proves

The v15 build applied/reused the carried sources and completed the final verification layer. Logs include successful strfmon/strfmon_l guard-page checks, TSIG fallback/buffer-boundary checks, aligned-allocation checks, and minimized native runtime verification. The same layer runs the regex verifier in the C locale, asserts libc6 2.41-12+deb13u4+rcamarda4, and verifies tokenizers 0.23.1+rcamarda1. The native verifier exercises malformed BPE merges, normal encoding, and offline 384-dimensional ONNX inference.

These are source/build/runtime facts, not proof that Xray scanned those exact bytes. The supplied table lacks installed versions, digest and scanner match explanation. Continued matches are consistent with package/advisory matching that does not recognize local carries, but that remains an inference.

## Upstream recheck and next remediation

- Official Debian tracker still shows no fixed Trixie versions for these pending Debian entries. Newer-suite glibc/GCC fixed versions are source-review leads, not permission to mix runtime packages blindly.
- Official Tokenizers latest release is v0.23.3 (2026-10-09). Its BPE builder still subtracts prefix_len and copies the concatenation into the longest-vocabulary-token buffer before checking the resulting token. Our bounds/prefix patch remains necessary; an upgrade alone would not remediate CVE-2026-85670.
- PR #78's other agent is validating newer glibc source for Headroom. Its eventual successful build, retained-patch coverage and runtime ABI checks are prerequisites to proposing the same migration for Gnosis. No shared-branch edits or speculative sibling migration were made here.
- Five legacy glibc CVEs remain without a verified usable fix; the PBDS consumer issue remains open. Keep them separate from the 16 carried corrections/mitigations and from architecture/feature applicability evidence.
- No new source defect missing from the Gnosis recipe was established by this repeated table, so this reconciliation does not increment a revision or trigger an identical image rebuild.

## References

- https://security-tracker.debian.org/tracker/source-package/glibc
- https://security-tracker.debian.org/tracker/source-package/gcc-14
- https://security-tracker.debian.org/tracker/source-package/dash
- https://github.com/huggingface/tokenizers/issues/2094
- https://github.com/huggingface/tokenizers/blob/v0.23.3/tokenizers/src/models/bpe/model.rs
- images/gnosis-mcp/Dockerfile
- images/gnosis-mcp/verify-native-runtime.py
- images/gnosis-mcp/verify-security-runtime.py
- images/headroom-mcp/SECURITY-20261015.md
- docs/security/PBDS-CONSUMERS-20261016.md

Agent: ChatGPT Work Codex /root. Model identifier unavailable.
