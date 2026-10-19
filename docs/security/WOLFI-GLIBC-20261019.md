# Wolfi glibc: AI CLI runner Xray intake and LiteLLM sibling fix

## Report

User screenshot 2026-10-19 identifies ai-cli-runner
`claude2.1.303-cline3.0.73-v1`, not the data-only Gnosis model image.
The screenshot supplies no digest or CVSS vector. Current Docker Hub lookup
resolves that tag to `sha256:83bddd39d51ed6753d80d05910999bea9384dcd965210aab4b21e9fda0b5f508`;
this lookup is separate evidence and does not prove which digest Xray scanned.

| CVE | Reported component | Version | Score | CWE | Supplied fix |
| --- | --- | --- | --- | --- | --- |
| CVE-2026-86805 | wolfi:ld-linux-2.44 | 2.44-r6 | 6.3 v3 | CWE-367 | N/A |
| CVE-2026-89092 | wolfi:glibc-2.44-locale-posix | 2.44-r6 | 4.2 v3 | CWE-789 | N/A |
| CVE-2026-8674 | wolfi:glibc-2.44-locale-posix | 2.44-r6 | 5.3 v3 | CWE-617 | N/A |

Preserve the screenshot's component/CWE attribution. In particular, 89092
affects nscd, not locale data itself; source-package association can cause
the scanner to report another glibc subpackage. This fix uses the vendor's
corrected packages rather than a suppression or package removal.

## Root cause and correction

The digest-pinned Wolfi base contains exact `/etc/apk/world` constraints:
`glibc-2.44=2.44-r6`, `ld-linux-2.44=2.44-r6`,
`glibc-2.44-locale-posix=2.44-r6`, and `libcrypt1-2.44=2.44-r6`.
These were read from the published image's base layers. The existing
`apk upgrade --available` and `apk add --upgrade glibc` operated under those
concrete pins. The original runner build logs show no glibc upgrade.
The exact-pinned libcrypt1 package also depends on glibc-2.44=2.44-r6.

Wolfi security.json lists all three supplied CVEs fixed in glibc-2.44
2.44-r8. Both packages.wolfi.dev and the actual base's apk.cgr.dev repository
index contain r8 for the four concrete packages. The vendor recipe uses
the glibc release/2.44 branch, expected commit
34106fee698c83eb0af71d4d0381e66b399be746, epoch 8.

Replace the concrete world constraints through normal apk add/upgrade with
minimum 2.44-r8 for all four packages. Do not mix Debian packages, rebuild
glibc, switch distributions, remove required libraries, or relabel an old
package. Each Dockerfile checks actual installed versions with apk's native
version comparator. Missing packages and versions below r8 fail the build.
Existing offline CLI smoke, LiteLLM health and blocking HIGH/CRITICAL scan
gates remain unchanged. A passing Trivy gate does not clear these MEDIUM rows.

## Sibling review

| Images | Evidence and treatment |
| --- | --- |
| ai-cli-runner | Supplied Xray report; r6 base pins and no upgrade confirmed. Install and assert all four r8 packages. |
| litellm | Same exact base; recent PR candidate run 39248408715 fetched the same repository and retained base glibc. Same normal package upgrade and assertions in final runtime. Builder-only r6 does not enter the final venv as an OS library. |
| agentmemory-mcp, gnosis-mcp | Existing checksum-pinned glibc resolver/secure-loader backports; nscd absent. Retain Debian treatment and pending scan status. Wolfi package upgrades are not interchangeable with Debian fixes. |
| headroom-mcp | Existing forky-source glibc 2.43-7 rebuild on trixie. Preserve it and pending Xray status. |
| bifrost-mcp, ebay-mcp, docker-socket-proxy, sooperset-mcp-atlassian, sqz-mcp | Alpine/musl final runtime source recipes. No Wolfi package applicability established; embedded copies remain unknown without exact artifact inventory. |
| zeus-dev-image | UBI final runtime. Requires Red Hat-specific review; Wolfi r8 is not a compatible replacement. |
| slim-archify, slim-agentmemory-mcp, slim-docker-vsix, slim-docker-vsix-upgrades, slim-docker-codeburn, gnosis-model-mdbr-leaf-ir | Scratch payloads; do not inherit builder glibc by base image alone. Embedded/native dependency coverage remains artifact-specific. Gnosis model contains only approved data files. |

Ran tools/check-debian-security.py against a fresh tracker snapshot:
49 pending source/CVE pairs reviewed. For these three CVEs, trixie remains
open/no-dsa; forky/sid fixes are 2.43-7 (86805/89092) and 2.43-6 (8674).
This does not clear existing Debian findings or replace their carried fixes.

## Sources checked 2026-10-19

- https://packages.wolfi.dev/os/security.json
- https://packages.wolfi.dev/os/x86_64/APKINDEX.tar.gz
- https://apk.cgr.dev/chainguard/x86_64/APKINDEX.tar.gz
- https://github.com/wolfi-dev/os/blob/main/glibc-2.44.yaml
- https://sourceware.org/pipermail/libc-announce/2026/000064.html
- https://sourceware.org/git/?p=glibc.git;a=commit;h=ed0c137b97eb940b4b64981e84ed806d3276edd9
- https://sourceware.org/git/?p=glibc.git;a=commit;h=506ea57086bfb9ce3daff1c14246a1cb532aba0a
- https://sourceware.org/git/?p=glibc.git;h=c90398e00571476711792baacb6d92bd2a7b6891
- https://github.com/rcamarda390/my-docker-images/actions/runs/39253933575
- https://github.com/rcamarda390/my-docker-images/actions/runs/39248408715

## Validation status

Candidate builds, package-version assertions, existing runtime tests and
scans pending. Revisions have floor 2 and publication chooses the next
unused tag; preserve upstream CLI/LiteLLM versions. All three ledger rows
remain pending until a fresh Xray report identifies the rebuilt digest.

Agent: OpenAI Codex /root. LLM: GPT-6.
