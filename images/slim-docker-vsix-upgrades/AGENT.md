<!-- File: images/slim-docker-vsix-upgrades/AGENT.md -->
# Scan artifact instructions

Purpose: preserve complete official upgrade-candidate VSIX packages for Xray inspection. Supported editor: Microsoft VS Code 1.98.2. This is not a runnable service. Read the repository `docs/AGENT_INSTRUCTIONS.md` and this directory's README before changes.

`manifest.json` records selected installed/new versions, official sources, hashes, engine requirements, platforms and package dependencies. `/slim/metadata` records per-file hashes, byte counts, extraction completeness and provenance; `/slim/sbom` contains CycloneDX inventories. All source pins are in repository `extensions.json`. Preserve both `/slim/payload/vsix` and `/slim/payload/unpacked` entirely. Never install dependencies, remove vulnerable bundled files, or claim scanner clearance without scan evidence.

Build with the dedicated workflow. It validates PRs and publishes manual runs to GHCR and Docker Hub under immutable versioned tags. No latest. Pull with the full registry host (`ghcr.io/...` or `docker.io/...`). Read the Actions summary for exact reference/digest. Use `docker create IMAGE /unused`, `docker cp CID:/slim/payload/vsix/. DEST`, then `docker rm CID` to retrieve archives; use `/slim/payload/unpacked/.` for expanded payloads. No shell exists in this image.

Xray acceptance requires scanning the exact digest and comparing detected components with inventory paths/counts. JSON SBOMs enumerate identifiable package manifests; bundled/minified code, native dependencies and Xray SBOM support can limit coverage. No Xray result was available during package preparation. Engine validation does not establish AL2 native ABI compatibility. Future remediation must follow the shared security ledger and keep original official packages intact unless a distinct source rebuild is explicitly authorized.
