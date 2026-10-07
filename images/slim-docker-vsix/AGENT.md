<!-- File: images/slim-docker-vsix/AGENT.md -->
# Live Preview VSIX payload

Image holds files. No runtime. No shell. No VS Code. Use image by digest.

Original: `/slim/payload/vsix/ms-vscode.live-server-0.4.16/ms-vscode.live-server-0.4.16.vsix`
Unpacked: `/slim/payload/unpacked/ms-vscode.live-server-0.4.16/`
Evidence: `/slim/metadata/ms-vscode.live-server-0.4.16/`

Copy original VSIX. Verify SHA256SUMS from same evidence folder. VS Code: Extensions → Install from VSIX.
Do not rezip unpacked tree. Do not modify original. VS Code engine: ^1.80.0.

## Scan coverage

Preserve every shipped file, metadata, license, notice, and source map.
`live-preview.cdx.json`: CycloneDX 1.5. Partial runtime inventory from exact publisher notice versions.
`coverage.json`: full notice inventory, unresolved declarations, coverage limits.
`files.json`: SHA-256 inventory of extracted files. Human audit evidence; not Xray input.
`manifest.json`: payload facts. Not Xray dependency input.

SBOM omits build/type packages. No invented versions. No invented dependency edges.
Bundled telemetry dependency lacks exact version evidence. Transitive bundle coverage incomplete.
Clean scan alone does not prove complete coverage or extension approval.

Current JFrog docs support embedded .cdx.json SBOM aggregation:
https://docs.jfrog.com/security/docs/sbom-import
Container layers and nested archives:
https://docs.jfrog.com/security/docs/xray-docker-containers
VSIX packaging:
https://code.visualstudio.com/api/working-with-extensions/publishing-extension

Verify deployed Xray sees SBOM components: @vscode/codicons 0.0.32, mime 3.0.0, url 0.11.0, ws 8.17.1.
If aggregation unavailable, upload .cdx.json to indexed Generic repo. Compare inventories.
No claim of vulnerability remediation. No claim of complete extension security review.
