# CodeBurn security payload image

Downstream security repack of Marketplace CodeBurn VSIX 1.0.2.
Source: https://marketplace.visualstudio.com/items?itemName=CodeBurn.codeburn
Upstream: https://github.com/getagentseal/codeburn
Original VSIX SHA-256: 2ba28c0750433108639fe5af698f3e00ec23d494ac4cb39d67d56382e4f364ee

## Remediation

| Component | Original | Fixed | Findings |
|---|---|---|---|
| @modelcontextprotocol/sdk | 1.31.0 | 1.32.0 | XRAY-1099702, XRAY-1100629, XRAY-1099704 |
| @hono/node-server | 1.19.17 | 2.1.3 | XRAY-1095349 |
| hono | 4.13.7 | 4.13.11 | XRAY-1095348 |
| ip-address | 10.7.3 | 10.7.4 | XRAY-1107110 |

The checked-in official VSIX is input only. The final image contains the patched
installable VSIX and its matching extracted tree. Four external CLI package
folders are replaced with authentic npm release contents verified against pinned
SHA-512 integrity values. Application bundles and other dependencies are unchanged.
This is a custom unsigned VSIX, not the original Marketplace artifact. Extension
identity and version remain 1.0.2; Docker image revision distinguishes the repack.

## Payload

- VSIX: /slim/payload/vsix/codeburn.codeburn-1.0.2/codeburn.codeburn-1.0.2.vsix
- Unpacked: /slim/payload/unpacked/codeburn.codeburn-1.0.2/
- Evidence: /slim/metadata/codeburn.codeburn-1.0.2/
- Fixed npm versions, release URLs and integrity hashes: /slim/metadata/security-fixes.json

Scratch image, linux/amd64, files only. No shell or extension execution at runtime.
Build requires npm registry access; installed payload requires no dependency download.
Metadata is regenerated from patched contents: CycloneDX SBOM, package manifests,
file hashes, ELF inventory, coverage, origin and patched VSIX checksum.
Original source digest is recorded separately from the patched artifact digest.

Builder checks safe extraction, original integrity, replacement package identity
and final fixed versions. Node 22 checks CLI help, extension stdio readiness,
MCP initialization and tools/list with an empty temporary home.
The Node/Python builders do not enter the final image.

VS Code engine remains ^1.82.0. GUI functionality is not tested by this build.
Xray must rescan the new image; six rows were visible in the supplied screenshot,
while its sidebar indicated seven findings. Any additional finding needs its details.
Bundled code without manifests may require content analysis beyond this SBOM.
