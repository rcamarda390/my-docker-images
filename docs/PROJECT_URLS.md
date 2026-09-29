# Project URLs

Use these links to identify projects. Check an image's `image.yaml`, Dockerfile, and build workflow for the actual source and version before recommending an update. This list also includes related projects that are not built by this repository. A project may use its repository or package page as its documentation; a separate documentation site is not required.

| Project | Project URL | Documentation or releases | Repository use |
| --- | --- | --- | --- |
| Headroom | https://github.com/headroomlabs-ai/headroom | https://docs.headroomlabs.ai/docs | `images/headroom-mcp` |
| Docker Socket Proxy | https://github.com/Tecnativa/docker-socket-proxy | https://github.com/Tecnativa/docker-socket-proxy/releases | `images/docker-socket-proxy`; check the HAProxy base image separately |
| eBay MCP | https://github.com/YosefHayim/ebay-mcp | https://github.com/YosefHayim/ebay-mcp/releases | `images/ebay-mcp` |
| AgentMemory | https://github.com/rohitg00/agentmemory | https://github.com/rohitg00/agentmemory/blob/main/CHANGELOG.md | `images/agentmemory-server` |
| OmniRoute | https://github.com/diegosouzapw/OmniRoute | https://github.com/diegosouzapw/OmniRoute/wiki/User-Guide ; https://github.com/diegosouzapw/OmniRoute/blob/release/v3.8.51/docs/guides/DOCKER_GUIDE.md | Related project; no image listed here |
| Bifrost | https://github.com/maximhq/bifrost | https://docs.getbifrost.ai/overview | `images/bifrost-mcp` |
| LiteLLM | https://github.com/BerriAI/litellm | https://github.com/BerriAI/litellm/releases | `images/litellm` |
| SQZ MCP | https://github.com/ojuschugh1/sqz | https://github.com/ojuschugh1/sqz/releases | `images/sqz-mcp`; check the vendored Cargo.lock |
| Zeus Dev Image | Composite image; see `images/zeus-dev-image/Dockerfile` | Check installed products individually, including https://github.com/tt-a1i/archify and https://gitlab.freedesktop.org/xdg/xdg-user-dirs | `images/zeus-dev-image` |
| Gnosis MCP | https://pypi.org/project/gnosis-mcp/ | https://pypi.org/project/gnosis-mcp/#files | `images/gnosis-mcp` installs the PyPI package; use PyPI for version checks |
| Gnosis (different project) | https://github.com/skorokithakis/gnosis | — | Related project; not the source of `images/gnosis-mcp` |
| Atlassian Rovo MCP (official) | https://github.com/atlassian/atlassian-mcp-server | https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/ | Related cloud service; not the source of the Sooperset image |
| Sooperset MCP Atlassian (used here) | https://github.com/sooperset/mcp-atlassian | https://pypi.org/project/mcp-atlassian/ | Source for `images/sooperset-mcp-atlassian` |

The Sooperset image does not contain Atlassian's official Rovo MCP server.

## Check all images for updates

When asked for a repository-wide update check, enumerate all `images/*/image.yaml` files from the current default branch, including new images not yet listed here. For each image, inspect its `image.yaml`, Dockerfile, workflow, relevant lockfile, and image-specific documentation. Compare the configured version with the latest applicable stable release or package version. For composite images, check each installed upstream product; check compatibility-coupled dependencies together.

Report the configured version, latest applicable version, source URL, release date, status (update available, current, blocked, or unverified), and material compatibility or security caveat for each image. Mark inaccessible or incomparable sources unverified. Review release notes, local patches, persistence, and build inputs before proposing an upgrade. The scheduled `.github/workflows/check-upstream-versions.yml` covers only five images and opens manifest-only candidate PRs; it does not perform a full inventory or prove that images build. Do not modify or publish images merely to check for updates.
