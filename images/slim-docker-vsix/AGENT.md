<!-- File: images/slim-docker-vsix/AGENT.md -->
# VSIX security payload image

Image holds files. No runtime. No shell. Use image by digest.
Holds ONE extension at a time, swapped per Xray scan.

## Microsoft SQL Server (mssql)

Official Marketplace VSIX `ms-mssql.mssql` 1.38.0. No rebuild. No modification.
Marketplace gzip transport decoded, then SHA-256 checked against VSIX_SHA256 in image.yaml. Mismatch rejects build.

VSIX: `/slim/payload/vsix/ms-mssql.mssql-1.38.0/ms-mssql.mssql-1.38.0.vsix`
Unpacked: `/slim/payload/unpacked/ms-mssql.mssql-1.38.0/`
Evidence: `/slim/metadata/ms-mssql.mssql-1.38.0/`

Evidence files: `mssql.cdx.json` (CycloneDX from package.json manifests), `files.json`, `package-manifests.json`, `native-binaries.json`, `SHA256SUMS`, `coverage.json`, `manifest.json`.
Bundled/minified deps may lack manifests; Xray binary analysis authoritative.

## Usage

Copy VSIX from image. Verify `SHA256SUMS`. VS Code: Install from VSIX.
Do not rezip unpacked trees. Image publication is not organizational approval.
