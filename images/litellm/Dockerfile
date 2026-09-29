# syntax=docker/dockerfile:1.7

ARG WOLFI_IMAGE=cgr.dev/chainguard/wolfi-base@sha256:65e1acb87a2bf356b92c5f70f3980f03b4bb51dfd483c834e01557525f15c1d9
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.7@sha256:240fb85ab0f263ef12f492d8476aa3a2e4e1e333f7d67fbdd923d00a506a516a
ARG LITELLM_VERSION=1.94.3

FROM ${UV_IMAGE} AS uvbin

FROM ${WOLFI_IMAGE} AS builder

ARG LITELLM_VERSION

RUN apk upgrade --available --no-cache \
    && apk add --no-cache ca-certificates libsndfile python3

COPY --from=uvbin /uv /usr/local/bin/uv

ENV PATH="/opt/litellm/bin:${PATH}"

# Install the exact published security release without pip or a local compiler,
# then raise every supplied Xray component to its stated fix version.
RUN UV_NO_MANAGED_PYTHON=1 uv venv --python /usr/bin/python3 /opt/litellm \
    && uv pip install --python /opt/litellm/bin/python \
        "litellm[proxy]==${LITELLM_VERSION}" \
        'RestrictedPython>=8.3,<9' \
        'tornado>=6.5.8' \
        'cryptography>=50.0.0,<51' \
        'aiohttp>=3.14.3,<4' \
        'mcp>=1.28.1,<2' \
        'pyasn1>=0.6.4' \
    && /opt/litellm/bin/python -c 'from importlib.metadata import version; from packaging.version import Version as V; floors={"litellm":"1.94.3","RestrictedPython":"8.3","tornado":"6.5.8","cryptography":"50.0.0","aiohttp":"3.14.3","mcp":"1.28.1","pyasn1":"0.6.4"}; assert all(V(version(p)) >= V(v) for p,v in floors.items())' \
    && /opt/litellm/bin/python -c 'import importlib.util; assert importlib.util.find_spec("ddtrace") is None; assert importlib.util.find_spec("pypdf") is None' \
    && /opt/litellm/bin/python -c 'import litellm; import litellm.proxy.proxy_server'

FROM ${WOLFI_IMAGE} AS runtime

ARG LITELLM_VERSION

RUN apk upgrade --available --no-cache \
    && apk add --no-cache --upgrade glibc \
    && apk add --no-cache ca-certificates libsndfile python3 \
    && adduser -D -u 10001 litellm

COPY --from=builder /opt/litellm /opt/litellm

ENV PATH="/opt/litellm/bin:${PATH}" \
    LITELLM_PORT=4000

WORKDIR /app
USER 10001:10001

EXPOSE 4000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:4000/health/liveliness", timeout=5)'

LABEL org.opencontainers.image.title="litellm" \
      org.opencontainers.image.description="LiteLLM AI Gateway built from pinned upstream source" \
      org.opencontainers.image.source="https://github.com/BerriAI/litellm" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${LITELLM_VERSION}" \
      org.opencontainers.image.revision="${LITELLM_VERSION}"

ENTRYPOINT ["litellm"]
CMD ["--port", "4000"]
