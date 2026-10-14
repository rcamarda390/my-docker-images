# Project URLs

Use these links to identify projects. Check an image's `image.yaml`, Dockerfile, and build workflow for the actual source and version before recommending an update. This list also includes related projects that are not built by this repository. A project may use its repository or package page as its documentation; a separate documentation site is not required.

| # | Project | Project URL | Documentation or releases | Repository use |
| ---: | --- | --- | --- | --- |
| 1 | AgentMemory | https://github.com/rohitg00/agentmemory | https://github.com/rohitg00/agentmemory/blob/main/CHANGELOG.md | images/agentmemory-server |
| 2 | AI CLI runner — Claude Code | https://github.com/anthropics/claude-code | https://www.npmjs.com/package/@anthropic-ai/claude-code | images/ai-cli-runner (Claude CLI) |
| 3 | AI CLI runner — Cline CLI | https://github.com/cline/cline | https://www.npmjs.com/package/cline | images/ai-cli-runner (Cline CLI) |
| 4 | Archify | https://github.com/tt-a1i/archify | https://github.com/tt-a1i/archify/releases | images/slim-archify; also used by Zeus Dev Image |
| 5 | Bifrost | https://github.com/maximhq/bifrost | https://docs.getbifrost.ai/overview | images/bifrost-mcp |
| 6 | CodeBurn VS Code extension | https://github.com/getagentseal/codeburn | https://marketplace.visualstudio.com/items?itemName=CodeBurn.codeburn | images/slim-docker-codeburn; compare VSIX marketplace release and repository |
| 7 | Docker Socket Proxy | https://github.com/Tecnativa/docker-socket-proxy | https://github.com/Tecnativa/docker-socket-proxy/releases | images/docker-socket-proxy; check HAProxy base image separately |
| 8 | eBay MCP | https://github.com/YosefHayim/ebay-mcp | https://github.com/YosefHayim/ebay-mcp/releases | images/ebay-mcp |
| 9 | Gnosis MCP | https://github.com/nicholasglazer/gnosis-mcp | https://github.com/nicholasglazer/gnosis-mcp/releases | images/gnosis-mcp; Dockerfile currently installs pinned PyPI distribution; verify GitHub-to-package provenance |
| 10 | Headroom | https://github.com/headroomlabs-ai/headroom | https://docs.headroomlabs.ai/docs | images/headroom-mcp |
| 11 | LiteLLM | https://github.com/BerriAI/litellm | https://github.com/BerriAI/litellm/releases | images/litellm |
| 12 | OmniRoute | https://github.com/diegosouzapw/OmniRoute | https://github.com/diegosouzapw/OmniRoute/wiki/User-Guide ; https://github.com/diegosouzapw/OmniRoute/blob/release/v3.8.51/docs/guides/DOCKER_GUIDE.md | Related project; no image listed here |
| 13 | Sooperset MCP Atlassian | https://github.com/sooperset/mcp-atlassian | https://github.com/sooperset/mcp-atlassian/releases | images/sooperset-mcp-atlassian; not Atlassian Rovo MCP |
| 14 | SQZ MCP | https://github.com/ojuschugh1/sqz | https://github.com/ojuschugh1/sqz/releases | images/sqz-mcp; check vendored Cargo.lock |
| 15 | Zeus Dev Image | https://github.com/rcamarda390/my-docker-images/tree/main/images/zeus-dev-image | https://gitlab.freedesktop.org/xdg/xdg-user-dirs | Composite image; inspect Dockerfile and installed components |

## Check all images for updates

When asked for a repository-wide update check, enumerate all `images/*/image.yaml` files from the current default branch, including new images not yet listed here. For each image, inspect its `image.yaml`, Dockerfile, workflow, relevant lockfile, and image-specific documentation. Compare the configured version with the latest applicable stable release or package version. For composite images, check each installed upstream product; check compatibility-coupled dependencies together.

Report the configured version, latest applicable version, source URL, release date, status (update available, current, blocked, or unverified), and material compatibility or security caveat for each image. Mark inaccessible or incomparable sources unverified. Review release notes, local patches, persistence, and build inputs before proposing an upgrade. The scheduled `.github/workflows/check-upstream-versions.yml` covers only five images and opens manifest-only candidate PRs; it does not perform a full inventory or prove that images build. Do not modify or publish images merely to check for updates.
