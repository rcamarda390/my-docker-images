<!-- File: images/slim-docker-vsix-upgrades/AGENT.md -->
# VSIX upgrades scan image

Image holds files. No runtime. No shell. Scan artifact only. Use by digest.
Target VS Code: `1.98.2`. Source: Microsoft Marketplace only.

## Layout

- `/slim/manifest.json` — extension id, version, sha256, platform.
- `/slim/payload/vsix/<id>-<version>.vsix` — original, byte-exact.
- `/slim/payload/unpacked/<id>-<version>/` — full unzip, nothing removed, no npm install.
- `/slim/metadata/` — inventory, compatibility, provenance, SHA256SUMS, per-extension files.json/coverage.json.
- `/slim/sbom/` — CycloneDX 1.5 per extension + combined.

## Rules

- Do not rezip unpacked trees. Do not edit payload.
- Do not delete vulnerable bundled deps. Report them.
- No Cline fork (`saoudrizwan.claude-dev`) here.
- Pin list = `extensions.json`. Change a version only after checking `engines.vscode` permits 1.98.2, not pre-release.
- Build fails on any download, identity, engine, pre-release, or extraction problem. No silent substitution.

## Limits

SBOM = package.json files found in the VSIX only. Minified bundles are not enumerated.
Xray scanned / components found / vulns found / zero vulns are four different claims.
SHA-256 recorded at build time (not pinned in git). Compare with `metadata/SHA256SUMS`.

## Extract

```bash
cid=$(docker create ghcr.io/rcamarda390/slim-docker-vsix-upgrades:<tag> /unused)
docker cp "$cid:/slim/payload/vsix/." /tmp/.vsix/
docker cp "$cid:/slim/payload/unpacked/." /tmp/.vsix-unpacked/
docker rm "$cid"
```
