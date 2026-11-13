# syntax=docker/dockerfile:1.7

ARG WOLFI_IMAGE=cgr.dev/chainguard/wolfi-base@sha256:65e1acb87a2bf356b92c5f70f3980f03b4bb51dfd483c834e01557525f15c1d9
ARG MCP_VERSION=1.30.0
ARG AUTHLIB_VERSION=1.9.5
ARG CERTIFI_VERSION=2026.10.23
ARG DNSPYTHON_VERSION=2.9.2
ARG JOSERFC_VERSION=1.7.7
ARG OAUTHLIB_VERSION=4.0.1

# Exact application dependency versions already resolved in the hardened
# uv.lock. These are promoted to explicit build inputs so the Docker build
# fails closed if lock resolution ever drifts below the Xray-remediated set.
ARG CRYPTOGRAPHY_VERSION=50.0.0
ARG PYJWT_VERSION=2.15.1
ARG URLLIB3_VERSION=2.8.0
ARG CLICK_VERSION=8.4.2
ARG IDNA_VERSION=3.19
ARG SOUPSIEVE_VERSION=4.0
ARG PYMDOWN_EXTENSIONS_VERSION=11.0.2
ARG PYDANTIC_SETTINGS_VERSION=2.15.0
ARG PYTHON_DOTENV_VERSION=1.2.3
ARG PYGMENTS_VERSION=2.21.0
ARG FASTMCP_VERSION=3.4.11
ARG PYDANTIC_VERSION=2.14.2
ARG OPENTELEMETRY_API_VERSION=1.45.1
ARG MARKDOWN_VERSION=3.11.3

FROM ${WOLFI_IMAGE} AS python-base

# Share the installed interpreter and libraries between builder and runtime.
RUN apk upgrade --available --no-cache \
    && apk add --no-cache --upgrade \
        'ca-certificates-bundle>=20260909-r3' \
        'zlib>=1.3.2.1_rc20260601-r0' \
        'glibc-2.44>=2.44-r8' \
        'ld-linux-2.44>=2.44-r8' \
        'glibc-2.44-locale-posix>=2.44-r8' \
        'libcrypt1-2.44>=2.44-r8' \
        libgcc \
        libstdc++ \
        'python-3.14-runtime>=3.14.10-r0' \
        'libexpat1>=2.8.5-r0' \
        'sqlite-libs>=3.53.4-r0'

FROM python-base AS builder

ARG MCP_VERSION
ARG AUTHLIB_VERSION
ARG CERTIFI_VERSION
ARG DNSPYTHON_VERSION
ARG JOSERFC_VERSION
ARG OAUTHLIB_VERSION
ARG CRYPTOGRAPHY_VERSION
ARG PYJWT_VERSION
ARG URLLIB3_VERSION
ARG CLICK_VERSION
ARG IDNA_VERSION
ARG SOUPSIEVE_VERSION
ARG PYMDOWN_EXTENSIONS_VERSION
ARG PYDANTIC_SETTINGS_VERSION
ARG PYTHON_DOTENV_VERSION
ARG PYGMENTS_VERSION
ARG FASTMCP_VERSION
ARG PYDANTIC_VERSION
ARG OPENTELEMETRY_API_VERSION
ARG MARKDOWN_VERSION

# uv is copied as a standalone binary and is forbidden from downloading or
# substituting another interpreter.
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /usr/local/bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-system \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/bin/python3.14

ARG VERSION

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --extra wpad --no-install-project --no-dev --no-editable

# Apply downstream Python-Markdown fixes in the builder only.
RUN apk add --no-cache patch

COPY . /app
RUN if [ -n "$VERSION" ] && echo "$VERSION" | grep -qE '^[0-9]'; then \
      sed -i "s/fallback-version = \"0.0.0\"/fallback-version = \"$VERSION\"/" pyproject.toml; \
    fi

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra wpad --no-dev --no-editable

# Apply to the locked wheel after the final sync. Any source mismatch fails the build.
RUN cd /app/patches \
    && sha256sum -c SHA256SUMS \
    && site_packages=$(/app/.venv/bin/python -c 'import sysconfig; print(sysconfig.get_path("purelib"))') \
    && patch --batch --forward --fuzz=0 -d "$site_packages" -p1 < markdown-1680.patch \
    && patch --batch --forward --fuzz=0 -d "$site_packages" -p1 < markdown-1664.patch

# Bifrost-style fail-closed version assertions: prove the interpreter and each
# Xray-remediated application dependency resolved to the exact intended version
# before anything is copied into the runtime image.
RUN /app/.venv/bin/python -c "import platform; assert tuple(map(int, platform.python_version_tuple())) >= (3, 14, 10), platform.python_version()" \
    && /app/.venv/bin/python -c "from importlib.metadata import version; expected={'mcp':'${MCP_VERSION}','Authlib':'${AUTHLIB_VERSION}','certifi':'${CERTIFI_VERSION}','dnspython':'${DNSPYTHON_VERSION}','joserfc':'${JOSERFC_VERSION}','oauthlib':'${OAUTHLIB_VERSION}','cryptography':'${CRYPTOGRAPHY_VERSION}','PyJWT':'${PYJWT_VERSION}','urllib3':'${URLLIB3_VERSION}','click':'${CLICK_VERSION}','idna':'${IDNA_VERSION}','soupsieve':'${SOUPSIEVE_VERSION}','pymdown-extensions':'${PYMDOWN_EXTENSIONS_VERSION}','pydantic-settings':'${PYDANTIC_SETTINGS_VERSION}','python-dotenv':'${PYTHON_DOTENV_VERSION}','Pygments':'${PYGMENTS_VERSION}','fastmcp':'${FASTMCP_VERSION}','fastmcp-slim':'${FASTMCP_VERSION}','pydantic':'${PYDANTIC_VERSION}','opentelemetry-api':'${OPENTELEMETRY_API_VERSION}','Markdown':'${MARKDOWN_VERSION}'}; actual={name:version(name) for name in expected}; assert actual == expected, (actual, expected); print('remediated:', actual)" \
    && find /app/.venv -name '__pycache__' -type d -exec rm -rf {} + \
    && find /app/.venv -name '*.pyc' -delete \
    && find /app/.venv -name '*.pyo' -delete \
    && find /app/.venv -path '*/site-packages/setuptools*' -delete \
    && find /app/.venv -path '*/site-packages/pip*' -delete

FROM python-base AS runtime

ARG MCP_VERSION
ARG AUTHLIB_VERSION
ARG CERTIFI_VERSION
ARG DNSPYTHON_VERSION
ARG JOSERFC_VERSION
ARG OAUTHLIB_VERSION
ARG CRYPTOGRAPHY_VERSION
ARG PYJWT_VERSION
ARG URLLIB3_VERSION
ARG CLICK_VERSION
ARG IDNA_VERSION
ARG SOUPSIEVE_VERSION
ARG PYMDOWN_EXTENSIONS_VERSION
ARG PYDANTIC_SETTINGS_VERSION
ARG PYTHON_DOTENV_VERSION
ARG PYGMENTS_VERSION
ARG FASTMCP_VERSION
ARG PYDANTIC_VERSION
ARG OPENTELEMETRY_API_VERSION
ARG MARKDOWN_VERSION

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN adduser -D -h /home/app -s /bin/sh app

WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Verify the final Wolfi image and preserve package provenance for scanners.
RUN grep -qx 'ID=wolfi' /etc/os-release \
    && apk info -e python-3.14-runtime libexpat1 sqlite-libs \
    && apk info -v python-3.14-runtime libexpat1 sqlite-libs ca-certificates-bundle zlib \
    && /app/.venv/bin/python -c "import ssl, pyexpat; assert tuple(map(int, pyexpat.EXPAT_VERSION.removeprefix('expat_').split('.'))) >= (2,8,5), pyexpat.EXPAT_VERSION; assert pyexpat.ParserCreate().Parse('<root/>', True) == 1" \
    && /app/.venv/bin/python -c "import platform; assert tuple(map(int, platform.python_version_tuple())) >= (3, 14, 10), platform.python_version()" \
    && /app/.venv/bin/python -c "from importlib.metadata import version; expected={'mcp':'${MCP_VERSION}','Authlib':'${AUTHLIB_VERSION}','certifi':'${CERTIFI_VERSION}','dnspython':'${DNSPYTHON_VERSION}','joserfc':'${JOSERFC_VERSION}','oauthlib':'${OAUTHLIB_VERSION}','cryptography':'${CRYPTOGRAPHY_VERSION}','PyJWT':'${PYJWT_VERSION}','urllib3':'${URLLIB3_VERSION}','click':'${CLICK_VERSION}','idna':'${IDNA_VERSION}','soupsieve':'${SOUPSIEVE_VERSION}','pymdown-extensions':'${PYMDOWN_EXTENSIONS_VERSION}','pydantic-settings':'${PYDANTIC_SETTINGS_VERSION}','python-dotenv':'${PYTHON_DOTENV_VERSION}','Pygments':'${PYGMENTS_VERSION}','fastmcp':'${FASTMCP_VERSION}','fastmcp-slim':'${FASTMCP_VERSION}','pydantic':'${PYDANTIC_VERSION}','opentelemetry-api':'${OPENTELEMETRY_API_VERSION}','Markdown':'${MARKDOWN_VERSION}'}; actual={name:version(name) for name in expected}; assert actual == expected, (actual, expected); print('remediated:', actual)" \
    && /app/.venv/bin/python -c "import importlib.util, pathlib, sqlite3; from importlib.metadata import distributions; from packaging.version import Version; assert importlib.util.find_spec('pip') is None, importlib.util.find_spec('pip'); assert importlib.util.find_spec('setuptools') is None, importlib.util.find_spec('setuptools'); roots=(pathlib.Path('/app/.venv'), pathlib.Path('/usr/lib')); forbidden=[str(path) for root in roots for path in root.rglob('*') if path.is_file() and ('/pip/_vendor/' in str(path) or '/ensurepip/_bundled/' in str(path))]; assert not forbidden, forbidden[:20]; packages={d.metadata['Name'].lower(): d.version for d in distributions() if d.metadata.get('Name')}; assert sqlite3.sqlite_version_info >= (3,53,4), sqlite3.sqlite_version; assert 'msgpack' not in packages or Version(packages['msgpack']) >= Version('1.2.1'), packages.get('msgpack'); import mcp_atlassian; from mcp_atlassian import main; assert callable(main)" \
    && /app/.venv/bin/mcp-atlassian --help

USER app

RUN --mount=type=bind,source=verify-markdown.py,target=/tmp/verify-markdown.py \
    /app/.venv/bin/python /tmp/verify-markdown.py

ENTRYPOINT ["/app/.venv/bin/mcp-atlassian"]
