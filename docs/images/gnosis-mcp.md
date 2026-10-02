# Gnosis MCP image

[Back to repository README](../../README.md) · [Image source](../../images/gnosis-mcp/)

The repository contains an air-gap-oriented Gnosis MCP image at:

```text
images/gnosis-mcp/
```

Current release metadata: [image.yaml](../../images/gnosis-mcp/image.yaml).

Its purpose is to provide a self-hosted MCP documentation server suitable for restricted/offline runtime environments.

The image pre-bundles the local embedding model required by Gnosis rather than downloading it after deployment. The Docker build downloads the required tokenizer and ONNX model artifacts into:

```text
/gnosis-model-cache
```

Runtime defaults include:

```text
GNOSIS_MCP_HOST=0.0.0.0
GNOSIS_MCP_PORT=8000
GNOSIS_MCP_DATABASE_URL=sqlite:////data/docs.db
GNOSIS_MCP_EMBED_PROVIDER=local
GNOSIS_MCP_WRITABLE=false
XDG_DATA_HOME=/gnosis-model-cache
```

Persistent state is expected under:

```text
/data
```

and the image exposes port:

```text
8000
```

The runtime runs as the non-root `gnosis` user.

### Gnosis Streamable HTTP support

Gnosis 0.17.5 includes the REST/StreamableHTTP lifespan handling required to
initialize the MCP session manager when both transports are mounted together.
The image therefore no longer carries a local `rest.py` patch; the build still
verifies the resulting runtime and exercises the combined transport through
the image smoke test.

The image starts Gnosis with:

```text
gnosis-mcp serve --transport streamable-http --rest
```

The image also includes security-hardening work, including Python 3.13 and Debian package updates. Security scanner findings should remain a release gate when a critical base-library vulnerability does not yet have an upstream distribution fix.

### Build and publish

The Gnosis workflow validates relevant pull requests without publishing. Changes
under the image directory merged to main build and publish automatically; manual
workflow dispatch also publishes. Run titles explicitly identify Gnosis.

Before publishing, the candidate must pass database checks, HTTP health,
Streamable HTTP initialization, and a search_docs call with Docker networking
disabled. Trivy HIGH/CRITICAL findings, including unfixed findings, block release.

Successful publication pushes the same immutable 0.17.5-vN tag to Docker Hub
(rcamarda390/gnosis-mcp) and GHCR. The next N is one above the highest existing
Docker Hub revision for the upstream version; failed builds do not consume it.
The workflow summary supplies the exact image reference to import into Artifactory.

New PyPI upstream releases require updating image.yaml and requirements.in,
regenerating requirements.lock, and validating compatibility before publication.
