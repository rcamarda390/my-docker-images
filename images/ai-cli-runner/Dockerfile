# syntax=docker/dockerfile:1.7

# GitLab CI job image carrying the Claude Code and Cline CLIs for an air-gapped
# network. Both CLIs ship as self-contained glibc executables, so the final
# image needs no Node.js, npm, or package registry access at runtime.
#
# Both binaries link against glibc (libc.so.6 / ld-linux-x86-64.so.2), which is
# why the runtime is Debian slim rather than Alpine/musl.
ARG DEBIAN_SUITE=trixie
ARG CLAUDE_CODE_VERSION=2.1.289
ARG CLINE_VERSION=3.0.68

# Builder only: npm resolves the pinned platform packages from package-lock.json
# (integrity-checked) and is discarded with this stage.
FROM node:24-trixie-slim@sha256:8ec5d7557396cfe32d21c3f9c13072355ceab22b584578ca4bb28af31120cffe AS builder
ARG CLAUDE_CODE_VERSION
ARG CLINE_VERSION
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
# image.yaml is the version source of truth; fail if the lockfile has drifted
# from it rather than silently shipping a different version.
RUN set -eu; \
    claude_pkg=node_modules/@anthropic-ai/claude-code-linux-x64; \
    cline_pkg=node_modules/@cline/cli-linux-x64; \
    test "$(node -p "require('./$claude_pkg/package.json').version")" = "$CLAUDE_CODE_VERSION"; \
    test "$(node -p "require('./$cline_pkg/package.json').version")" = "$CLINE_VERSION"; \
    mkdir -p /out/opt; \
    cp -a "$claude_pkg" /out/opt/claude-code; \
    cp -a "$cline_pkg" /out/opt/cline; \
    chmod 0755 /out/opt/claude-code/claude /out/opt/cline/bin/cline

FROM debian:${DEBIAN_SUITE}-slim
ARG CLAUDE_CODE_VERSION
ARG CLINE_VERSION
# Composite claude+cline string supplied by the shared workflow; label only.
ARG IMAGE_VERSION=unknown

# git and ca-certificates are what GitLab's docker executor and the CLIs need
# beyond the binaries (bash and coreutils come with the slim base). Add nothing
# else without an Xray-driven reason: every package is scanned.
RUN apt-get update \
    && apt-get -y --no-install-recommends upgrade \
    && apt-get -y --no-install-recommends install git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /out/opt /opt
RUN ln -s /opt/claude-code/claude /usr/local/bin/claude \
    && ln -s /opt/cline/bin/cline /usr/local/bin/cline \
    && useradd --uid 1000 --gid 0 --create-home --shell /bin/bash runner

# Air-gap defaults: no self-update, telemetry, or other non-essential traffic.
# Claude Code talks to AWS Bedrock; region, credentials and role/ARN come from
# the job environment or instance role at runtime and are never baked in.
ENV CLAUDE_CODE_USE_BEDROCK=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
    DISABLE_AUTOUPDATER=1 \
    DISABLE_TELEMETRY=1 \
    DO_NOT_TRACK=1

# Fail the build if the executables are not the pinned versions or cannot run
# on this base (missing glibc, wrong arch).
RUN claude --version | grep -qwF "$CLAUDE_CODE_VERSION" \
    && cline --version | grep -qwF "$CLINE_VERSION" \
    && git --version \
    && ! command -v node \
    && ! command -v npm

LABEL org.opencontainers.image.title="ai-cli-runner" \
      org.opencontainers.image.description="Claude Code and Cline CLIs for air-gapped GitLab CI jobs" \
      org.opencontainers.image.source="https://github.com/rcamarda390/my-docker-images" \
      org.opencontainers.image.version="${IMAGE_VERSION}"

# No ENTRYPOINT/CMD of consequence: GitLab runs job scripts through the shell.
CMD ["/bin/bash"]
