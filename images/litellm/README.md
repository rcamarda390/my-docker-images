# LiteLLM AI Gateway

Builds the exact published LiteLLM v1.94.3 Python distribution. Version 1.94.3 is the first release that fixes the
LiteLLM CVE-2026-84377 finding reported against v1.91.0.

The image uses LiteLLM's pinned Wolfi base and `uv` without pip or a compiler, installs only
the core proxy feature set, and runs the OpenAI-compatible gateway on port 4000
as an unprivileged user. Downstream minimums enforce the Xray fix versions for
RestrictedPython, Tornado, cryptography, aiohttp, MCP, and pyasn1. Optional
`ddtrace` and `pypdf` are excluded because this gateway does not enable the
upstream `proxy-runtime` feature group that requires them.

Published images use immutable tags:

- `ghcr.io/rcamarda390/litellm:1.94.3-vN`
- `docker.io/rcamarda390/litellm:1.94.3-vN`

The manual `Build and publish LiteLLM image` workflow calculates the next
revision from successfully published Docker Hub tags, smoke-tests the health
endpoint, and blocks publication on HIGH/CRITICAL Trivy findings.

Runtime credentials and configuration must be supplied through environment
variables or mounted files. Do not bake AWS credentials into the image.
