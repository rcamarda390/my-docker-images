# Project URLs

Use these links to identify projects and locate their Docker image definitions and build workflows. Check an image's `image.yaml`, Dockerfile, and build workflow for the actual source and version before recommending an update. This list also includes related projects that are not built by this repository; their Docker image and build action fields are blank. A project may use its repository or package page as its documentation; a separate documentation site is not required.

| # | Project | Project URL | Documentation or releases | Docker image | Build Action | Notes |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | AgentMemory | https://github.com/rohitg00/agentmemory | https://github.com/rohitg00/agentmemory/blob/main/CHANGELOG.md | [`agentmemory-server`](../images/agentmemory-server/) | [`build-agentmemory-server.yml`](../.github/workflows/build-agentmemory-server.yml) | images/agentmemory-server |
| 2 | AI CLI runner — Claude Code | https://github.com/anthropics/claude-code | https://www.npmjs.com/package/@anthropic-ai/claude-code | [`ai-cli-runner`](../images/ai-cli-runner/) | [`build-ai-cli-runner.yml`](../.github/workflows/build-ai-cli-runner.yml) | images/ai-cli-runner (Claude CLI) |
| 3 | AI CLI runner — Cline CLI | https://github.com/cline/cline | https://www.npmjs.com/package/cline | [`ai-cli-runner`](../images/ai-cli-runner/) | [`build-ai-cli-runner.yml`](../.github/workflows/build-ai-cli-runner.yml) | images/ai-cli-runner (Cline CLI) |
| 4 | Archify | https://github.com/tt-a1i/archify | https://github.com/tt-a1i/archify/releases | [`slim-archify`](../images/slim-archify/) | [`build-slim-archify.yml`](../.github/workflows/build-slim-archify.yml) | images/slim-archify; also used by Zeus Dev Image |
| 5 | Bifrost | https://github.com/maximhq/bifrost | https://docs.getbifrost.ai/overview | [`bifrost-mcp`](../images/bifrost-mcp/) | [`build-bifrost-mcp.yml`](../.github/workflows/build-bifrost-mcp.yml) | images/bifrost-mcp |
| 6 | CodeBurn VS Code extension | https://github.com/getagentseal/codeburn | https://marketplace.visualstudio.com/items?itemName=CodeBurn.codeburn | [`slim-docker-codeburn`](../images/slim-docker-codeburn/) | [`build-slim-docker-codeburn.yml`](../.github/workflows/build-slim-docker-codeburn.yml) | images/slim-docker-codeburn; compare VSIX marketplace release and repository |
| 7 | Docker Socket Proxy | https://github.com/Tecnativa/docker-socket-proxy | https://github.com/Tecnativa/docker-socket-proxy/releases | [`docker-socket-proxy`](../images/docker-socket-proxy/) | [`build-docker-socket-proxy.yml`](../.github/workflows/build-docker-socket-proxy.yml) | images/docker-socket-proxy; check HAProxy base image separately |
| 8 | eBay MCP | https://github.com/YosefHayim/ebay-mcp | https://github.com/YosefHayim/ebay-mcp/releases | [`ebay-mcp`](../images/ebay-mcp/) | [`build-ebay-mcp.yml`](../.github/workflows/build-ebay-mcp.yml) | images/ebay-mcp |
| 9 | Gnosis MCP | https://github.com/nicholasglazer/gnosis-mcp | https://github.com/nicholasglazer/gnosis-mcp/releases | [`gnosis-mcp`](../images/gnosis-mcp/) | [`build-gnosis-mcp.yml`](../.github/workflows/build-gnosis-mcp.yml) | images/gnosis-mcp; single upstream = this GitHub repo; build installs its hash-locked release (see docs/images/gnosis-mcp.md) |
| 10 | Headroom | https://github.com/headroomlabs-ai/headroom | https://docs.headroomlabs.ai/docs | [`headroom-mcp`](../images/headroom-mcp/) | [`build-headroom-mcp.yml`](../.github/workflows/build-headroom-mcp.yml) | images/headroom-mcp |
| 11 | LiteLLM | https://github.com/BerriAI/litellm | https://github.com/BerriAI/litellm/releases | [`litellm`](../images/litellm/) | [`build-litellm.yml`](../.github/workflows/build-litellm.yml) | images/litellm |
| 12 | OmniRoute | https://github.com/diegosouzapw/OmniRoute | https://github.com/diegosouzapw/OmniRoute/wiki/User-Guide ; https://github.com/diegosouzapw/OmniRoute/blob/release/v3.8.51/docs/guides/DOCKER_GUIDE.md | — | — | Related project; no image listed here |
| 13 | Sooperset MCP Atlassian | https://github.com/sooperset/mcp-atlassian | https://github.com/sooperset/mcp-atlassian/releases | [`sooperset-mcp-atlassian`](../images/sooperset-mcp-atlassian/) | [`build-sooperset-mcp-atlassian.yml`](../.github/workflows/build-sooperset-mcp-atlassian.yml) | images/sooperset-mcp-atlassian; not Atlassian Rovo MCP |
| 14 | SQZ MCP | https://github.com/ojuschugh1/sqz | https://github.com/ojuschugh1/sqz/releases | [`sqz-mcp`](../images/sqz-mcp/) | [`build-sqz-mcp.yml`](../.github/workflows/build-sqz-mcp.yml) | images/sqz-mcp; check vendored Cargo.lock |
| 15 | Zeus Dev Image | https://github.com/rcamarda390/my-docker-images/tree/main/images/zeus-dev-image | https://gitlab.freedesktop.org/xdg/xdg-user-dirs | [`zeus-dev-image`](../images/zeus-dev-image/) | [`build-zeus-dev-image.yml`](../.github/workflows/build-zeus-dev-image.yml) | Composite image; inspect Dockerfile and installed components |

## Version-check GitHub Actions

These workflows check upstream versions and may create candidate PRs. They are separate from image build workflows and from the read-only ChatGPT audit described in [WEEKLY_VERSION_AUDIT.md](WEEKLY_VERSION_AUDIT.md).

| Workflow | Scope |
| --- | --- |
| [`check-upstream-versions.yml`](../.github/workflows/check-upstream-versions.yml) | Bifrost, Headroom, LiteLLM, SQZ, and Sooperset Atlassian; candidate manifest PRs |
| [`check-ai-cli-versions.yml`](../.github/workflows/check-ai-cli-versions.yml) | Claude Code and Cline CLI versions; candidate lockfile and manifest PRs |

## Additional image workflows

The following images have build workflows but do not have independent upstream rows in the table above. Keep them discoverable without inventing a single upstream project for a composite payload.

| Docker image | Build Action | Notes |
| --- | --- | --- |
| [`slim-docker-vsix`](../images/slim-docker-vsix/) | [`build-slim-docker-vsix.yml`](../.github/workflows/build-slim-docker-vsix.yml) | Multiple VS Code extensions; inspect payload manifest individually |

## Check all images for updates

When asked for a repository-wide update check, enumerate all `images/*/image.yaml` files from the current default branch, including new images not yet listed here. For each image, inspect its `image.yaml`, Dockerfile, workflow, relevant lockfile, and image-specific documentation. Compare the configured version with the latest applicable stable release or package version. For composite images, check each installed upstream product; check compatibility-coupled dependencies together.

Report the configured version, latest applicable version, source URL, release date, status (update available, current, blocked, or unverified), and material compatibility or security caveat for each image. Mark inaccessible or incomparable sources unverified. Review release notes, local patches, persistence, and build inputs before proposing an upgrade. The scheduled `.github/workflows/check-upstream-versions.yml` covers only five images and opens manifest-only candidate PRs; it does not perform a full inventory or prove that images build. Do not modify or publish images merely to check for updates.
