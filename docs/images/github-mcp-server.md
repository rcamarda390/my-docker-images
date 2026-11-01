# GitHub MCP Server image

[Back to repository README](../../README.md) · [Image source](../../images/github-mcp-server/)

Current release metadata: [image.wolfi.yaml](../../images/github-mcp-server/image.wolfi.yaml).
Upstream: https://github.com/github/github-mcp-server (releases).

## Build

- Builds upstream tag `v<upstream_version>` from a pinned commit (`GITHUB_MCP_COMMIT`).
- UI assets are built with upstream's Node and Go toolchain digests, then embedded.
- Go binary: `CGO_ENABLED=0`, `-trimpath`, version stamped as `v<upstream_version>`.
- Runtime: stock Wolfi base, with the same glibc/zlib/CA carries as `bifrost-mcp`.
- Entrypoint `/app/github-mcp-server`, default command `stdio`. Run `http` for the Streamable HTTP server (port 8082).

## Runtime notes

- Authentication: set `GITHUB_PERSONAL_ACCESS_TOKEN` at runtime. Never bake a token into the image.
- The build does not bake an OAuth client. Upstream's official release embeds one; this image does not, so OAuth login needs `--oauth-client-id`.
- The smoke test runs `--version` and an MCP stdio `initialize` with a disposable token. It makes no GitHub API call.

## Open items

- Xray/Trivy clearance is not established. No Go module pins were added. Review the first scan of the published tag before adding any.
- The first CI run is the build validation. Do not treat this document as proof a build passed.
