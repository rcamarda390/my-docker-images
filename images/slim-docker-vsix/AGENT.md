<!-- File: images/slim-docker-vsix/AGENT.md -->
# VSIX security payload image

Image holds files. No runtime. No shell. Use image by digest.

## Microsoft Live Preview

VSIX: `/slim/payload/vsix/ms-vscode.live-server-0.4.16/ms-vscode.live-server-0.4.16.vsix`
Unpacked: `/slim/payload/unpacked/ms-vscode.live-server-0.4.16/`
Evidence: `/slim/metadata/ms-vscode.live-server-0.4.16/`

CUSTOM BUILD. Not original Microsoft Marketplace VSIX. Display name marks rebuild.
Source: Microsoft v0.4.16 commit 79e9df2ffed927625988dfeb6876f84b087f12dd.
Preserve VS Code engine ^1.80.0. Replace bundled ws 8.17.1 with 8.21.0.
Fix CVE-2026-48779 and CVE-2026-45736. Both regressions run during build.
Original vulnerable VSIX exists only in builder. Final image excludes it.
Original artifact checksum and change provenance recorded in SECURITY-REBUILD.json.

`live-preview.cdx.json`: CycloneDX 1.5, actual webpack module package inventory plus preserved codicons media.
`coverage.json`: unresolved declarations and limitations. No guessed exact versions.
`files.json`: extracted file hashes. Audit evidence, not Xray input.

## Anthropic Claude Code

Official Marketplace VSIX, pinned linux-x64 version 2.1.291. No rebuild or modification. Decode Marketplace gzip transport before comparing the\nVSIX to CLAUDE_CODE_SHA256 in image.yaml; reject mismatches before writing payload.

VSIX: `/slim/payload/vsix/anthropic.claude-code-2.1.291-linux-x64/anthropic.claude-code-2.1.291-linux-x64.vsix`
Unpacked: `/slim/payload/unpacked/anthropic.claude-code-2.1.291-linux-x64/`
Evidence: `/slim/metadata/anthropic.claude-code-2.1.291-linux-x64/`

Xray-oriented evidence:
- `claude-code.cdx.json`: CycloneDX 1.5 inventory from package manifests physically present in the VSIX. The extension manifest is application metadata, not an npm dependency.
- `files.json`: every unpacked file with size and SHA-256.
- `package-manifests.json`: package.json locations, versions and dependency declarations.
- `native-binaries.json`: ELF binaries with hashes for native-component triage.
- `SHA256SUMS`: checksum of the original VSIX.
- `coverage.json`: scan coverage and limitations.
- `manifest.json`: source, version, platform and payload paths.

The original VSIX and unpacked tree are both retained so Xray can inspect archive and file-level content. Bundled/minified dependencies may not expose package manifests; Xray binary/content analysis remains authoritative for those.

## Usage

Copy the required VSIX from the image. Verify `SHA256SUMS` from its evidence folder. VS Code: Install from VSIX.
Do not rezip unpacked trees. Do not mistake image publication for organizational approval.

Current JFrog docs support embedded .cdx.json aggregation:
https://docs.jfrog.com/security/docs/sbom-import
Verify Xray findings against both the unpacked payload and generated SBOM after importing the new image.

Upstream Live Preview fixes:
https://github.com/websockets/ws/security/advisories/GHSA-96hv-2xvq-fx4p
https://github.com/websockets/ws/security/advisories/GHSA-58qx-3vcg-4xpx

