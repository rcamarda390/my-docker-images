<!-- File: images/slim-docker-vsix/AGENT.md -->
# Live Preview security rebuild

Image holds files. No runtime. No shell. Use image by digest.

VSIX: `/slim/payload/vsix/ms-vscode.live-server-0.4.16/ms-vscode.live-server-0.4.16.vsix`
Unpacked: `/slim/payload/unpacked/ms-vscode.live-server-0.4.16/`
Evidence: `/slim/metadata/ms-vscode.live-server-0.4.16/`

CUSTOM BUILD. Not original Microsoft Marketplace VSIX. Display name marks rebuild.
Source: Microsoft v0.4.16 commit 79e9df2ffed927625988dfeb6876f84b087f12dd.
Preserve VS Code engine ^1.80.0. Replace bundled ws 8.17.1 with 8.21.0.
Fix CVE-2026-48779 and CVE-2026-45736. Both regressions run during build.
Original vulnerable VSIX exists only in builder. Final image excludes it.
Original artifact checksum and change provenance recorded in SECURITY-REBUILD.json.

Copy VSIX. Verify SHA256SUMS from evidence folder. VS Code: Install from VSIX.
Do not rezip unpacked tree. Do not mistake image publication for organizational approval.

`live-preview.cdx.json`: CycloneDX 1.5, actual webpack module package inventory plus preserved codicons media.
`coverage.json`: unresolved declarations and limitations. No guessed exact versions.
`files.json`: extracted file hashes. Audit evidence, not Xray input.
`manifest.json`: payload facts, not Xray dependency input.

Dependency bundle rebuilt. Original other files, licenses, notices and translations preserved.
ws notice corrected because shipped implementation changed. Build lockfile pins dependency closure.
Runtime component versions come from resolved package metadata used by webpack.
Prebundled code inside dependencies may hide further transitive packages.
No claim all security defects fixed. No full VS Code GUI test in builder.

Current JFrog docs support embedded .cdx.json aggregation:
https://docs.jfrog.com/security/docs/sbom-import
Verify Xray detects ws 8.21.0 after importing new image. Compare full inventory.
If embedded aggregation unavailable, upload SBOM to indexed Generic repository.

Upstream fixes:
https://github.com/websockets/ws/security/advisories/GHSA-96hv-2xvq-fx4p
https://github.com/websockets/ws/security/advisories/GHSA-58qx-3vcg-4xpx
