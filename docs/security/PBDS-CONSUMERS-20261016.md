# PBDS consumer investigation — 2026-10-16

## Outcome

CVE-2026-102010 has a verified upstream fix. No affected ONNX consumer has been demonstrated by this investigation. Rebuilding ONNX or replacing libgcc/libstdc++ solely on the basis of a source-package CVE would be speculative. Keep the finding open pending complete artifact provenance or a scanner disposition based on the evidence.

The upstream change updates m_a_entries after allocation in the PBDS binary_heap erase_if template. It changes a header, not shared-library implementation code:
https://github.com/gcc-mirror/gcc/commit/aaa8351f4d2e636f9680a1f0a8ebc2f0a60611e6

## Match evidence to the built versions

| Image observed in successful publication logs | ONNX Runtime | Publication run | Published manifest digest |
| --- | --- | --- | --- |
| headroom-mcp:0.41.0-v2 | Python 1.26.0 | https://github.com/rcamarda390/my-docker-images/actions/runs/38752923881 | sha256:b0fa91ed856626a6addbb98cad29b5e282f2d19e3b56ea2f03c7401a548114f0 |
| agentmemory-mcp:0.9.30-v5 | Node package 1.24.3 | https://github.com/rcamarda390/my-docker-images/actions/runs/38752923432 | sha256:a491b8bc4e871a52b55e8a509a0a691d8f437c4da4fa99bbced6d417cf62c747 |
| gnosis-mcp:0.17.5-v15 | Python 1.28.0 | https://github.com/rcamarda390/my-docker-images/actions/runs/38784810311 | sha256:9b738800e09206c0ccc4d0fc0de819dfa679c84429111b5d42944f6300276c06 |

These are build-log observations of named artifacts, not the identity of any previously supplied Xray scan. No scan_digest or scan_status is changed by this review.

The earlier Gnosis review of ONNX 1.28.0 cannot establish applicability to Headroom 1.26.0 or AgentMemory 1.24.3. Version-matched source review was required and is now recorded.

## Source review

Searched every regular file in the versioned ONNX archives and every file in 22 selected pinned dependency archives per version for pb_ds, __gnu_pbds and binary_heap_tag. There were no matches. Dependency archive SHA-1 values matched each version's cmake/deps.txt; SHA-256 values are retained in evidence/PBDS-SOURCES-20261016.json. SHA-1 was used only to verify the existing upstream lock, not as a new integrity standard.

| ONNX Runtime | Source files searched | Dependency files searched | Source archive SHA-256 |
| --- | ---: | ---: | --- |
| 1.24.3 | 9,648 | 30,870 | 70364aa2cddfe535974bd160261c25743aca0ec3708770578813b0f9404bd064 |
| 1.26.0 | 9,955 | 30,972 | 2a90eb9a306c1eeb29213f5b165a55008ac5cb7d27e0935c4458c51a49ef091d |
| 1.28.0 | 10,656 | 31,531 | 9616cbdbbfcb1420b3261cd280a047d74ab0a249825e577b0e2dd310e22f6b83 |

The 22 dependency names are abseil_cpp, cxxopts, date, dlpack, eigen, flatbuffers, fp16, fxdiv, googlexnnpack, json, microsoft_gsl, mimalloc, mp11, onnx, protobuf, psimd, pthreadpool, pybind11, pytorch_cpuinfo, re2, safeint and extensions. This deliberately includes some optional source dependencies, not a claim they were all compiled into a particular wheel.

Not covered: all native packages outside ONNX, recursively fetched dependencies of every reviewed dependency, platform/GPU/test-only dependency archives, release-vendor compiler modifications, and complete stripped-binary build provenance. Identifier absence is supporting evidence, not proof that all native binaries are unaffected.

## Demonstrate the actual fix

Ran the upstream three-element priority-queue erase_if/clear regression using the local GCC 13 development headers and AddressSanitizer:

- Original header: exit 1, AddressSanitizer reports attempting double-free.
- Identical test with only m_a_entries = new_entries added at the upstream location: exit 0, no AddressSanitizer diagnostic.
- LeakSanitizer cannot inspect processes in this sandbox; disabled leak detection for both runs. AddressSanitizer remained enabled. This is a local demonstration of the header fix, not a test of an image's precompiled ONNX library.

Upstream runnable regression:
https://github.com/gcc-mirror/gcc/blob/aaa8351f4d2e636f9680a1f0a8ebc2f0a60611e6/libstdc%2B%2B-v3/testsuite/ext/pb_ds/regression/priority_queues_erase_if.cc

For a confirmed affected consumer, compile it against the fixed header and rerun that consumer's own tests. Replacing only runtime libraries cannot repair an embedded instantiation.

## Prevent missing official fix leads

The repository tracker checker previously printed only the configured suite. It now also reports fixed-version candidates from Forky and Sid while preserving the configured suite status. Records marked resolved with fixed_version 0 (not affected), missing versions, open records and non-Debian entries do not produce replacement candidates. These leads require source/ABI and carried-patch review; they never authorize mixing binary packages across suites or establish scanner clearance.

Validated with the existing unittest file and the dated tracker snapshot. GCC 14.4.0-3 appears as a Sid candidate for both saved GCC CVEs. No image, package pin, workflow or release revision changes are included.

## Build decision and remaining work

AgentMemory's successful v5 publication already contains the regex carry in current main. Comparing that publication commit 155c03f40139e3817b4e719654cae400f4d66d23 with main found no AgentMemory source changes. Gnosis v15 and Headroom v2 also published successfully. Repeating those builds would add no newly established PBDS correction.

PR #78's Headroom glibc migration remains owned by the other agent at the user's direction. This work does not modify that branch or migrate its changes to sibling images.

Remaining: exact-digest Xray observations for the current published images; vendor/consumer provenance for the remaining native dependency closure; source rebuild only if an affected consumer is identified. Keep prior downstream fixes and runtime libraries intact.

Agent: ChatGPT Work Codex /root. Model identifier unavailable.
