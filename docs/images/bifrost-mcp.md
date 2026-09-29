# Bifrost image

[Back to repository README](../../README.md) · [Image source](../../images/bifrost-mcp/)

This repository has also been used for Bifrost dependency and base-image maintenance.

For Bifrost v1.6.11, prior investigation established that the upstream release should be followed closely rather than maintaining unnecessary dependency overrides.

Relevant upstream characteristics identified during that work included:

- Bifrost v1.6.11
- released `transports/go.mod`
- `GOWORK=off`
- Alpine-based build/runtime stages

The project removed or avoided custom Go dependency overrides that downgraded dependencies relative to the upstream release.

When maintaining the Bifrost image, prefer an upstream-compatible build unless a documented air-gap or security requirement makes a divergence necessary.
