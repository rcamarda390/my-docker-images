# Bifrost image

[Back to repository README](../../README.md) · [Image source](../../images/bifrost-mcp/)

Current release metadata: [image.yaml](../../images/bifrost-mcp/image.yaml).

The notes below describe earlier dependency and base-image maintenance. Inspect the current Dockerfile and manifest before applying them to a newer release.

For Bifrost v1.6.11, prior investigation established that the upstream release should be followed closely rather than maintaining unnecessary dependency overrides.

Relevant upstream characteristics identified during that work included:

- Bifrost v1.6.11
- released `transports/go.mod`
- `GOWORK=off`
- Alpine-based build/runtime stages

The project removed or avoided custom Go dependency overrides that downgraded dependencies relative to the upstream release.

When maintaining the Bifrost image, prefer an upstream-compatible build unless a documented air-gap or security requirement makes a divergence necessary.
