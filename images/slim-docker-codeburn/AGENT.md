# CodeBurn security payload image

Official Microsoft Marketplace CodeBurn VSIX 1.0.2, preserved byte-for-byte.
Source: https://marketplace.visualstudio.com/items?itemName=CodeBurn.codeburn
Upstream source declared by the extension: https://github.com/getagentseal/codeburn
VSIX SHA-256: 2ba28c0750433108639fe5af698f3e00ec23d494ac4cb39d67d56382e4f364ee

## Payload

- Original: `/slim/payload/vsix/codeburn.codeburn-1.0.2/codeburn.codeburn-1.0.2.vsix`
- Unpacked: `/slim/payload/unpacked/codeburn.codeburn-1.0.2/`
- Evidence: `/slim/metadata/codeburn.codeburn-1.0.2/`

Scratch image, linux/amd64, files only. No shell or extension execution.
The VSIX is checked into this image's build context; the build does not download it.
Builder verifies its checksum, extension identity and safe ZIP paths before copying the final payload.

## Xray evidence

- `codeburn.cdx.json`: CycloneDX 1.5 with 165 distinct named/versioned packages physically present in the VSIX. Extension root is application metadata, not an npm dependency.
- `package-manifests.json`: 186 package manifests, paths, exact versions and declared dependency ranges.
- `files.json`: all 3,999 unpacked files, sizes and SHA-256 hashes.
- `native-binaries.json`: ELF inventory; none found in this release.
- `SHA256SUMS`: original VSIX checksum; verify from its VSIX folder.
- `manifest.json`: origin, version, platform, payload paths and digest.
- `coverage.json`: inventory counts and scan coverage limits.

Payload includes the extension host bundle, webview bundles/assets, staged CLI and its node_modules, README, license and changelog. Original manifests and notices remain in the unpacked tree. No dependencies installed, replaced or removed.

Exact dependency versions come only from shipped manifests. Bundled/minified code without manifests is not fully represented in the SBOM. Source-repository development dependencies are not assumed to be runtime payload. Archive, unpacked files and embedded SBOM should all be inspected by the deployed Xray instance; scan results are required to establish findings. This image does not claim a clean scan.

VS Code engine declaration is ^1.82.0. VS Code runtime functionality is not tested by this payload build.
