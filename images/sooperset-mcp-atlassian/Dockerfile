# syntax=docker/dockerfile:1.7

ARG ALPINE_VERSION=3.24
ARG PYTHON_APK_VERSION=3.14.7-r1

# Exact application dependency versions already resolved in the hardened
# uv.lock. These are promoted to explicit build inputs so the Docker build
# fails closed if lock resolution ever drifts below the Xray-remediated set.
ARG CRYPTOGRAPHY_VERSION=50.0.0
ARG PYJWT_VERSION=2.14.0
ARG URLLIB3_VERSION=2.7.0
ARG CLICK_VERSION=8.4.2
ARG IDNA_VERSION=3.19
ARG SOUPSIEVE_VERSION=2.9.2
ARG PYMDOWN_EXTENSIONS_VERSION=11.0.2
ARG PYDANTIC_SETTINGS_VERSION=2.15.0
ARG PYTHON_DOTENV_VERSION=1.2.3
ARG PYGMENTS_VERSION=2.21.0

FROM alpine:${ALPINE_VERSION} AS builder

ARG PYTHON_APK_VERSION
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

# Use Alpine's packaged Python instead of the Docker Official Python image.
# Xray can then resolve the exact interpreter from authoritative APK metadata
# rather than fingerprinting the source-built interpreter as an older release.
RUN apk upgrade --no-cache \
    && apk add --no-cache \
        ca-certificates \
        libgcc \
        libstdc++ \
        "python3=${PYTHON_APK_VERSION}" \
    && apk info -e "python3=${PYTHON_APK_VERSION}" \
    && python3 -c "import platform; assert platform.python_version() == '${PYTHON_APK_VERSION%-r*}', platform.python_version()"

# uv is copied as a standalone binary and is forbidden from downloading or
# substituting another interpreter.
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /usr/local/bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_PREFERENCE=only-system \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/bin/python3

ARG VERSION

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --extra wpad --no-install-project --no-dev --no-editable

COPY . /app
RUN if [ -n "$VERSION" ] && echo "$VERSION" | grep -qE '^[0-9]'; then \
      sed -i "s/fallback-version = \"0.0.0\"/fallback-version = \"$VERSION\"/" pyproject.toml; \
    fi

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra wpad --no-dev --no-editable

# Bifrost-style fail-closed version assertions: prove the interpreter and each
# Xray-remediated application dependency resolved to the exact intended version
# before anything is copied into the runtime image.
RUN /app/.venv/bin/python -c "import platform; assert platform.python_version() == '${PYTHON_APK_VERSION%-r*}', platform.python_version()" \
    && /app/.venv/bin/python -c "from importlib.metadata import version; expected={'cryptography':'${CRYPTOGRAPHY_VERSION}','PyJWT':'${PYJWT_VERSION}','urllib3':'${URLLIB3_VERSION}','click':'${CLICK_VERSION}','idna':'${IDNA_VERSION}','soupsieve':'${SOUPSIEVE_VERSION}','pymdown-extensions':'${PYMDOWN_EXTENSIONS_VERSION}','pydantic-settings':'${PYDANTIC_SETTINGS_VERSION}','python-dotenv':'${PYTHON_DOTENV_VERSION}','Pygments':'${PYGMENTS_VERSION}'}; actual={name:version(name) for name in expected}; assert actual == expected, (actual, expected); print('remediated:', actual)" \
    && find /app/.venv -name '__pycache__' -type d -exec rm -rf {} + \
    && find /app/.venv -name '*.pyc' -delete \
    && find /app/.venv -name '*.pyo' -delete \
    && find /app/.venv -path '*/site-packages/setuptools*' -delete \
    && find /app/.venv -path '*/site-packages/pip*' -delete

FROM alpine:${ALPINE_VERSION}

ARG PYTHON_APK_VERSION
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
ARG SQLITE_MIN_VERSION=3.53.4-r0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN apk upgrade --no-cache \
    && apk add --no-cache \
        ca-certificates \
        libgcc \
        libstdc++ \
        "python3=${PYTHON_APK_VERSION}" \
        "sqlite-libs>=${SQLITE_MIN_VERSION}" \
    && rm -rf /usr/lib/python3.*/ensurepip \
    && rm -rf /var/cache/apk/* \
    && adduser -D -h /home/app -s /bin/sh app

WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Verify the final artifact, not merely the builder inputs. Xray should see the
# APK package record for Python 3.14.7-r1, while the runtime check proves the
# venv uses that same interpreter and retains every fixed dependency version.
RUN apk info -e "python3=${PYTHON_APK_VERSION}" \
    && apk info -v python3 sqlite-libs \
    && python3 -c "import platform; assert platform.python_version() == '${PYTHON_APK_VERSION%-r*}', platform.python_version()" \
    && /app/.venv/bin/python -c "import platform; assert platform.python_version() == '${PYTHON_APK_VERSION%-r*}', platform.python_version()" \
    && /app/.venv/bin/python -c "from importlib.metadata import version; expected={'cryptography':'${CRYPTOGRAPHY_VERSION}','PyJWT':'${PYJWT_VERSION}','urllib3':'${URLLIB3_VERSION}','click':'${CLICK_VERSION}','idna':'${IDNA_VERSION}','soupsieve':'${SOUPSIEVE_VERSION}','pymdown-extensions':'${PYMDOWN_EXTENSIONS_VERSION}','pydantic-settings':'${PYDANTIC_SETTINGS_VERSION}','python-dotenv':'${PYTHON_DOTENV_VERSION}','Pygments':'${PYGMENTS_VERSION}'}; actual={name:version(name) for name in expected}; assert actual == expected, (actual, expected); print('remediated:', actual)" \
    && /app/.venv/bin/python -c "import importlib.util, pathlib, sqlite3; from importlib.metadata import distributions; from packaging.version import Version; assert importlib.util.find_spec('pip') is None, importlib.util.find_spec('pip'); assert importlib.util.find_spec('setuptools') is None, importlib.util.find_spec('setuptools'); roots=(pathlib.Path('/app/.venv'), pathlib.Path('/usr/lib')); forbidden=[str(path) for root in roots for path in root.rglob('*') if path.is_file() and ('/pip/_vendor/' in str(path) or '/ensurepip/_bundled/' in str(path))]; assert not forbidden, forbidden[:20]; packages={d.metadata['Name'].lower(): d.version for d in distributions() if d.metadata.get('Name')}; assert sqlite3.sqlite_version_info >= (3,53,4), sqlite3.sqlite_version; assert 'msgpack' not in packages or Version(packages['msgpack']) >= Version('1.2.1'), packages.get('msgpack'); import mcp_atlassian; from mcp_atlassian import main; assert callable(main)" \
    && /app/.venv/bin/mcp-atlassian --help

USER app

ENTRYPOINT ["/app/.venv/bin/mcp-atlassian"]
