# my-docker-images

Docker image builds for connected build environments and restricted Linux runtimes. Images are built and validated in GitHub Actions, then published or transferred through an approved artifact path. The runtime host can run Docker without installing application software on the host.

## Images

Each image directory contains an `image.yaml` manifest. Refer to it for the current upstream version, local revision, and publication settings.

| Image | Documentation | Source |
| --- | --- | --- |
| AgentMemory server | [Runtime and architecture](images/agentmemory-server/README.md) | [Image files](images/agentmemory-server/) |
| Bifrost gateway | [Build notes](docs/images/bifrost-mcp.md) | [Image files](images/bifrost-mcp/) |
| AI CLI runner (Claude Code + Cline) | [Build notes](docs/images/ai-cli-runner.md) | [Image files](images/ai-cli-runner/) |
| Docker socket proxy | [Image files](images/docker-socket-proxy/) | [Manifest](images/docker-socket-proxy/image.yaml) |
| eBay MCP | [Runtime guide](images/ebay-mcp/README.md) | [Image files](images/ebay-mcp/) |
| Gnosis MCP | [Offline runtime and transport](docs/images/gnosis-mcp.md) | [Image files](images/gnosis-mcp/) |
| Headroom | [Bedrock integration](docs/images/headroom-mcp.md) | [Image files](images/headroom-mcp/) |
| LiteLLM gateway | [Image guide](images/litellm/README.md) | [Image files](images/litellm/) |
| Sooperset MCP Atlassian | [Upstream guide](images/sooperset-mcp-atlassian/README.md) | [Image files](images/sooperset-mcp-atlassian/) |
| SQZ MCP | [Build notes](docs/images/sqz-mcp.md) | [Image files](images/sqz-mcp/) |

## Build and deployment

Image-specific workflows in [`.github/workflows/`](.github/workflows/) call the shared [build workflow](.github/workflows/build-image.yml). Published images use explicit version and revision tags. The GHCR image format is `ghcr.io/rcamarda390/<image-name>:<version>-v<revision>`.

- [Development, publishing, validation, and troubleshooting](docs/OPERATIONS.md)
- [MCP build methodology](docs/MCP_BUILD_METHODOLOGY.md)
- [Upstream project URLs](docs/PROJECT_URLS.md)
- [Agent instructions](docs/AGENT_INSTRUCTIONS.md)

Persistent data belongs on mounts or volumes, and runtime credentials must be supplied by the deployment environment.
