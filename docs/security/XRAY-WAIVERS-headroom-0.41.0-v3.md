# Xray waiver justifications: headroom-mcp 0.41.0-v3

Image: `ghcr.io/rcamarda390/headroom-mcp:0.41.0-v3`
Digest: `sha256:650e062a13da135d3a82b63b80f6ad16d02695dca558ac5f845eb56bd4d9bb12`
Build: https://github.com/rcamarda390/my-docker-images/actions/runs/38927566443 (PR 78)

74 rows / 28 CVEs reported, no fix versions. Xray flags `debian:trixie:*` by advisory, not by installed version.
Waiver != cleared. Ledger scan_status stays `pending`. Review each before applying.

## A. Fixed in image via Debian forky glibc 2.43-7 source (trixie: "vulnerable, no DSA")
Components: libc6, libc-bin, libc-gconv-modules-extra. Justification: "Fixed in Debian forky/sid; image rebuilds forky glibc 2.43-7 (2.43-7+rcamarda1)."
CVE-2026-5435, 6238, 6368, 6791, 8674, 18374, 19499, 19542, 77117, 80489, 86805, 95818

## B. Not applicable in this image
- CVE-2026-89092 (nscd): nscd package/binary absent; asserted in build.
- CVE-2026-97399 (Power8 strncasecmp): image is linux/amd64 only.
- CVE-2026-102474 (dash printf Unicode): dash 0.5.12 has no u/U encoder.
- CVE-2026-42250 (libbz2): defect in bzip2recover CLI; CLI absent (asserted). Python bz2 library retained.

## C. Mitigated downstream, no official fix
- CVE-2018-20796, CVE-2019-9192 (glibc regex recursion): Debian "unimportant"/disputed. Image adds 64-frame recursion bound (REG_ESPACE); verified by `verify-glibc-regex` in build. Complex valid patterns over 64 frames fail explicitly.
- CVE-2026-102473 (dash pmatch): dash rebuilt with libc `fnmatch`; linkage asserted.
- CVE-2026-93355 (LiteLLM JWT): downstream `email_verified` guard + verification test; LiteLLM proxy server not started (provider SDK only).
- CVE-2026-75104 (transformers): downstream shard-path guard.

## D. Open / no usable fix
- CVE-2019-1010022, 1010023, 1010024, 1010025, CVE-2010-4756 (glibc): Debian "unimportant" in all suites; upstream disputes/hardening-only. libc is required. Accept risk or waive as disputed.
- CVE-2026-95619, CVE-2026-102010 (gcc-14 runtime libs: libstdc++6, libgcc-s1, gcc-14-base): fix only in sid 14.4.0-3. 95619 allocation path not used on Linux posix_memalign; 102010 is a template compiled into the ONNX wheel, needs consumer rebuild. Runtime libs required by ONNX/Rust. Open.

## Note
Version suffix changes cannot clear these; do not rename versions to satisfy the scanner. Clearing requires Xray waivers/ignore rules, or a base whose advisory data lists the fixes (forky), which is a separate decision.

## Absent from this scan (headroom-mcp only, marked cleared in ledger)
CVE-2025-69720, 6141 (ncurses), 2026-54369, 54370 (acl), 54371 (attr), 56391, 56392, 2017-18018, 2025-5278 (coreutils), 2026-85091, 27171 (zlib), 2026-85670 (tokenizers).
Assumes the supplied Xray table is the complete result for the digest. Other images keep their own status.
