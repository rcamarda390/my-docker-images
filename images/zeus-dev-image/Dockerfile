# syntax=docker/dockerfile:1.7
# ============================================================
# zeus-dev-image -- base image candidate
# ============================================================
# Public software layer for the restricted-environment developer image.
# Internal users, site configuration, mounts, and startup behavior belong
# in the downstream Dockerfile after this image passes Xray.

# ============================================================
# Archify CLI source -- fetch the exact commit without carrying Git metadata
# into the final image.
# ============================================================
ARG ARCHIFY_COMMIT=06dd052602dd9a369e4d034e24faef0917b5a60c
ARG XDG_USER_DIRS_COMMIT=cd05b6d29da1abdb3cd253ef496ae7fd1593e4bb
FROM alpine:3.23.4@sha256:5b10f432ef3da1b8d4c7eb6c487f2f5a8f096bc91145e68878dd4a5019afde11 AS archify-source
ARG ARCHIFY_COMMIT
RUN apk add --no-cache ca-certificates git \
    && git init /src \
    && git -C /src remote add origin https://github.com/tt-a1i/archify.git \
    && n=0; until [ "$n" -ge 5 ]; do \
        git -C /src fetch --depth 1 origin "$ARCHIFY_COMMIT" \
            && git -C /src checkout --detach FETCH_HEAD && break; \
        n=$((n + 1)); \
        echo "git fetch failed (attempt $n/5), retrying..."; \
        sleep $((n * 3)); \
    done \
    && test "$(git -C /src rev-parse HEAD)" = "$ARCHIFY_COMMIT"

# ============================================================
# xdg-user-dirs source -- UBI10 does not package xdg-user-dirs
# ============================================================
# xdg-user-dir is a small standalone program used by Cline hooks and other
# user-directory-aware tooling. Build only that upstream command in a UBI10
# stage so it remains compatible with the final glibc-based image.
FROM registry.access.redhat.com/ubi10/ubi:latest AS xdg-user-dirs-source
ARG XDG_USER_DIRS_COMMIT
USER 0
RUN set -e; \
    dnf install -y gcc git python3 python3-pip; \
    python3 -m pip install --no-cache-dir meson==1.10.0 ninja==1.13.0; \
    git init /src; \
    git -C /src remote add origin https://gitlab.freedesktop.org/xdg/xdg-user-dirs.git; \
    n=0; until [ "$n" -ge 5 ]; do \
        git -C /src fetch --depth 1 origin "$XDG_USER_DIRS_COMMIT" \
            && git -C /src checkout --detach FETCH_HEAD && break; \
        n=$((n + 1)); \
        echo "git fetch failed (attempt $n/5), retrying..."; \
        sleep $((n * 3)); \
    done; \
    test "$(git -C /src rev-parse HEAD)" = "$XDG_USER_DIRS_COMMIT"; \
    meson setup /build /src --prefix=/usr/local -Ddocs=false -Dnls=false; \
    meson compile -C /build xdg-user-dir; \
    install -D -m 0755 /build/src/xdg-user-dir /out/usr/local/bin/xdg-user-dir; \
    test "$(HOME=/tmp/xdg-user-dirs-test /out/usr/local/bin/xdg-user-dir DOCUMENTS)" = /tmp/xdg-user-dirs-test

# ============================================================
# Final image
# ============================================================
# ponytail: base image uses the mutable `:latest` tag, matching the internal
# build. Pin to a digest if this image needs to stop tracking upstream UBI10
# security updates automatically.
FROM registry.access.redhat.com/ubi10/ubi:latest

# The UBI base defaults to UID 1001. Build layers need root to install OS
# packages and write under /etc, /opt, and /usr/local.
USER 0

# This image is a composite base image, not a build of one upstream
# project, so there is no single "upstream_version" to track. This ARG is
# the version_arg the shared build-image.yml workflow expects; it labels
# the image with the local zeus-dev-image release number from image.yaml.
ARG ZEUS_DEV_IMAGE_VERSION=2.0.0
LABEL org.opencontainers.image.title="zeus-dev-image" \
      org.opencontainers.image.description="UBI10/Python 3.12 base image candidate: Airflow, AWS CLI, Cline, Claude Code, AgentMemory MCP" \
      org.opencontainers.image.version="${ZEUS_DEV_IMAGE_VERSION}"

# Archify must not check for updates when running in the restricted environment.
ENV ARCHIFY_UPDATE_CHECK_DISABLED=1
# PostgreSQL 15 from PGDG installs its client binaries outside the default
# RHEL path.
ENV PATH=/usr/pgsql-15/bin:${PATH}

# ============================================================
# Install OS packages
# ============================================================
# UBI10 does not publish RHEL's PostgreSQL module metadata, so attempting to
# enable postgresql:15 fails before package installation. Install the required
# PostgreSQL 15 client from PGDG's official EL10 repository instead.
#
# Use RHEL 10's supported Node.js 22 AppStream packages; Node.js 24 remains Technology Preview.
RUN dnf install -y \
        https://download.postgresql.org/pub/repos/yum/reporpms/EL-10-x86_64/pgdg-redhat-repo-latest.noarch.rpm \
    && dnf install -y \
        python3 \
        python3-pip \
        vim \
        vi \
        shadow-utils \
        findutils \
        file \
        hostname \
        procps-ng \
        nodejs \
        npm \
        git \
        jq \
        tar \
        postgresql15 \
    && dnf clean all \
    && rm -rf /var/cache/dnf /var/cache/yum /tmp/* /var/tmp/* \
    && echo "=== Verifying Node.js version ===" \
    && node --version \
    && npm --version \
    && case "$(node --version)" in \
        v22.*) echo "OK: Node.js 22.x confirmed" ;; \
        *) echo "ERROR: Expected Node.js v22.x, got $(node --version)"; exit 1 ;; \
    esac \
    && case "$(psql --version)" in \
        'psql (PostgreSQL) 15.'*) echo "OK: PostgreSQL 15.x client confirmed" ;; \
        *) echo "ERROR: Expected PostgreSQL 15.x client, got $(psql --version)"; exit 1 ;; \
    esac

COPY --from=xdg-user-dirs-source /out/usr/local/bin/xdg-user-dir /usr/local/bin/xdg-user-dir
RUN test "$(HOME=/tmp/xdg-user-dirs-test xdg-user-dir DOCUMENTS)" = /tmp/xdg-user-dirs-test

# ============================================================
# Optional convenience packages (not in every UBI10 AppStream/BaseOS repo
# set without extra repos enabled - continue on failure like Docker CLI
# and unzip below).
# ============================================================
RUN dnf install -y htop btop \
    || echo "WARNING: htop/btop not available in repository, continuing build"

# ============================================================
# Install Docker CLI (optional - continues on failure)
# ============================================================
# Base image uses microdnf which doesn't support config-manager.
# Create repo file directly instead.
RUN set -e; \
    echo "=== Installing Docker CLI ==="; \
    echo '[docker-ce-stable]' > /etc/yum.repos.d/docker-ce.repo; \
    echo 'name=Docker CE Stable - $basearch' >> /etc/yum.repos.d/docker-ce.repo; \
    echo 'baseurl=https://download.docker.com/linux/rhel/10/$basearch/stable' >> /etc/yum.repos.d/docker-ce.repo; \
    echo 'enabled=1' >> /etc/yum.repos.d/docker-ce.repo; \
    echo 'gpgcheck=0' >> /etc/yum.repos.d/docker-ce.repo; \
    echo 'repo_gpgcheck=0' >> /etc/yum.repos.d/docker-ce.repo; \
    if dnf install -y docker-ce-cli; then \
        echo "Docker CLI installed successfully"; \
        docker --version; \
    else \
        echo "WARNING: Docker CLI installation failed; continuing without it"; \
    fi; \
    dnf clean all

# ============================================================
# Install unzip (optional - continues on failure)
# ============================================================
RUN dnf install -y unzip \
    || echo "WARNING: unzip not available in repository, continuing build"

# ============================================================
# npm registry: default npmjs.org (no configuration needed)
# ============================================================

# ============================================================
# Optional: Pyright for Python type checking (dev tool only)
# ============================================================
RUN npm install -g pyright \
    || echo "WARNING: pyright not available in registry, continuing build"

# ============================================================
# Source-installed tools
# ============================================================

# ============================================================
# Apache Airflow 3.3.2 from public PyPI, constrained for Python 3.12.
# ============================================================
RUN set -eux; \
    CONSTRAINTS=/tmp/constraints-airflow.txt; \
    curl -fsSL -o "$CONSTRAINTS" \
        https://raw.githubusercontent.com/apache/airflow/constraints-3.3.2/constraints-3.12.txt; \
    pip3 install --no-input --no-cache-dir --constraint "$CONSTRAINTS" apache-airflow==3.3.2; \
    pip3 install --no-input --no-cache-dir --constraint "$CONSTRAINTS" \
        apache-airflow-providers-common-compat \
        apache-airflow-providers-common-io \
        apache-airflow-providers-common-sql \
        apache-airflow-providers-ftp \
        apache-airflow-providers-http \
        apache-airflow-providers-imap \
        apache-airflow-providers-smtp \
        apache-airflow-providers-sqlite \
        apache-airflow-providers-amazon \
        apache-airflow-providers-ssh \
        apache-airflow-providers-fab; \
    rm -f "$CONSTRAINTS"; \
    installed_version=$(python3 -c "import airflow; print(airflow.__version__)"); \
    test "$installed_version" = "3.3.2"; \
    python3 -c "from airflow.providers.fab import __version__; print('FAB version:', __version__)"
# ============================================================
# Python dependencies
# ============================================================
RUN set -eux; \
    pip3 install --no-input --no-cache-dir --upgrade pip; \
    pip3 install --no-input --no-cache-dir \
        numpy==1.26.4 \
        pandas==2.2.3 \
        psycopg2-binary==2.9.11 \
        tabulate==0.10.0 \
        sqlparse==0.6.0 \
        cryptography==50.0.0 \
        colorama==0.4.6 \
        PyYAML==6.0.3 \
        duckdb==1.5.3 \
        sqlglot==30.4.2 \
        s3fs==2026.3.0 \
        jira==3.10.5 \
        beautifulsoup4==4.15.0 \
        html2text==2025.4.15 \
        markdown-it-py==3.0.0; \
    \
    pip3 install --no-input --no-cache-dir sqlfluff==4.2.0; \
    \
    pip3 install --no-input --no-cache-dir \
        botocore==1.43.75 \
        boto3==1.43.75; \
    python3 -m venv /opt/aws-cli; \
    /opt/aws-cli/bin/pip install --no-input --no-cache-dir awscli==1.46.1; \
    ln -sf /opt/aws-cli/bin/aws /usr/local/bin/aws; \
    aws --version; \
    pip3 install --no-input --no-cache-dir ruff==0.15.11 \
        || echo "WARNING: ruff not available in repository, continuing build"; \
    pip3 install --no-input --no-cache-dir pyfiglet \
        || echo "WARNING: pyfiglet not available in repository, continuing build"; \
    pip3 install --no-input --no-cache-dir --upgrade msgpack==1.2.2 setuptools==84.0.0; \
    python3 -c "import msgpack, setuptools; assert msgpack.__version__ == '1.2.2'; assert tuple(map(int, setuptools.__version__.split('.')[:2])) >= (78, 1)"; \
    rm -rf /root/.cache /tmp/* /var/tmp/*

# ============================================================
# Source-installed Node.js tools
# ============================================================
# Install packages directly from their public npm sources. The internal
# air-gapped Dockerfile consumes the resulting commands and paths; it does
# not need the original artifact files.
COPY patch-iii-otel2.mjs /tmp/patch-iii-otel2.mjs
RUN set -eux; \
    mkdir -p /opt/agentmemory /opt/agentmemory-mcp; \
    printf '%s\n' '{"name":"zeus-agentmemory","version":"1.0.0","private":true,"overrides":{"iii-sdk":"0.11.2","@opentelemetry/api-logs":"0.200.0","@opentelemetry/core":"2.9.0","@opentelemetry/context-async-hooks":"2.9.0","@opentelemetry/instrumentation":"0.200.0","@opentelemetry/otlp-transformer":"0.200.0","@opentelemetry/propagator-b3":"2.9.0","@opentelemetry/propagator-jaeger":"2.9.0","@opentelemetry/resources":"2.9.0","@opentelemetry/sdk-logs":"0.200.0","@opentelemetry/sdk-metrics":"2.9.0","@opentelemetry/sdk-trace-base":"2.9.0","@opentelemetry/sdk-trace-node":"2.9.0"}}' > /opt/agentmemory/package.json; \
    cp /opt/agentmemory/package.json /opt/agentmemory-mcp/package.json; \
    npm install --prefix /opt/agentmemory @agentmemory/agentmemory@0.9.29; \
    npm install --prefix /opt/agentmemory-mcp --omit=dev @agentmemory/mcp@0.9.29; \
    for prefix in /opt/agentmemory /opt/agentmemory-mcp; do \
        AGENTMEMORY_ROOT="$prefix" node /tmp/patch-iii-otel2.mjs; \
        (cd "$prefix" && node --input-type=module -e "await import('iii-sdk'); console.log('iii-sdk OpenTelemetry compatibility smoke OK')"); \
    done; \
    ln -sf /opt/agentmemory/node_modules/.bin/agentmemory /usr/local/bin/agentmemory; \
    ln -sf /opt/agentmemory-mcp/node_modules/@agentmemory/mcp/bin.mjs /usr/local/bin/agentmemory-mcp; \
    mkdir -p /opt/cline; \
    printf '%s\n' '{"name":"zeus-cline","version":"1.0.0","private":true,"overrides":{"undici":"6.28.1"}}' > /opt/cline/package.json; \
    npm install --prefix /opt/cline cline@3.0.61; \
    ln -sf /opt/cline/node_modules/.bin/cline /usr/local/bin/cline; \
    npm install -g @anthropic-ai/claude-code@2.1.252; \
    cline --version; \
    claude --version; \
    rm -f /tmp/patch-iii-otel2.mjs

# ============================================================
# GitLab MCP server dependencies
# ============================================================
# Recreate the node_modules bundle described by the internal build:
# @modelcontextprotocol/sdk, axios, TypeScript, and Node.js types.
RUN set -eux; \
    npm install --prefix /opt/gitlab-mcp-server --legacy-peer-deps \
        @modelcontextprotocol/sdk@1.29.0 \
        axios@1.18.0 \
        @types/node \
        typescript@6.0.3; \
    test -d /opt/gitlab-mcp-server/node_modules/@modelcontextprotocol/sdk; \
    test -d /opt/gitlab-mcp-server/node_modules/axios; \
    test -x /opt/gitlab-mcp-server/node_modules/.bin/tsc

# ============================================================
# Archify CLI (vendored from the pinned upstream commit)
# ============================================================
COPY --from=archify-source /src/archify/ /opt/archify/
RUN ln -sf /opt/archify/bin/archify.mjs /usr/local/bin/archify \
    && chmod +x /opt/archify/bin/archify.mjs \
    && archify --help >/dev/null \
    && archify_version="$(node -p "require('/opt/archify/package.json').version")" \
    && echo "Archify version: ${archify_version}" \
    && test "${archify_version}" = "2.17.0-dev.1"

# Fail the build if required software is missing.
COPY verify-installation.sh /usr/local/bin/verify-installation.sh
RUN chmod 755 /usr/local/bin/verify-installation.sh \
    && /usr/local/bin/verify-installation.sh

# The UBI Python image defaults to an unprivileged runtime user.
USER 1001
CMD ["/bin/bash"]
