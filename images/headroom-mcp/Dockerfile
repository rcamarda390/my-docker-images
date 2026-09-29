# syntax=docker/dockerfile:1.7

ARG HEADROOM_VERSION=0.39.1
ARG HEADROOM_COMMIT=d13e1966f820220b482a33c30bde1e926743939a
ARG LITELLM_VERSION=1.101.0
ARG PYTHON_VERSION=3.13.15
ARG PYTHON_ABI=3.13
ARG DEBIAN_SUITE=trixie
ARG GLIBC_DEBIAN_VERSION=2.41-12+deb13u4
ARG GLIBC_BACKPORT_VERSION=2.41-12+deb13u4+rcamarda1
ARG PIP_VERSION=26.2.1
ARG PYJWT_VERSION=2.14.0
ARG TOKENIZERS_VERSION=0.23.2
ARG TRANSFORMERS_VERSION=5.17.0
ARG URLLIB3_VERSION=2.8.0
ARG ANYIO_VERSION=4.14.2
ARG RUSTUP_VERSION=1.28.2
ARG SQLITE_VERSION=3.53.4
ARG SQLITE_AUTOCONF=3530400
ARG SQLITE_SHA3=454e45f61c6bd75b7420e7190732dea03ce6639c63ada47bbc592f67fc340338
ARG ZLIB_VERSION=1.3.2
ARG ZLIB_SHA256=b99a0b86c0ba9360ec7e78c4f1e43b1cbdf1e6936c8fa0f6835c0cd694a495a1

# The three patches below carry CVE-2026-5928 (BZ #33998), CVE-2026-5435
# (BZ #34033), and CVE-2026-5450 (BZ #34008). Xray's follow-up scan of
# 0.37.0-v12 still reports CVE-2026-5435 against libc-bin/libc6 -- it matches
# the vulnerable package by name/CPE and cannot read the "+rcamarda1" local
# Debian revision that carries the cherry-picked fix. The version assertion at
# the end of the runtime stage (libc6/libc-bin == GLIBC_BACKPORT_VERSION) is
# the proof this exact patched build is what ships; no further source change
# addresses this finding.
FROM debian:${DEBIAN_SUITE}-slim AS glibc_patched
ARG DEBIAN_SUITE
ARG GLIBC_DEBIAN_VERSION
ARG GLIBC_BACKPORT_VERSION

ENV DEBIAN_FRONTEND=noninteractive

COPY patches/glibc/ /tmp/glibc-patches/

RUN set -eux; \
    sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/debian.sources; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates devscripts dpkg-dev git quilt; \
    apt-get build-dep -y --no-install-recommends "glibc=${GLIBC_DEBIAN_VERSION}"; \
    mkdir -p /build /out; \
    cd /build; \
    apt-get source "glibc=${GLIBC_DEBIAN_VERSION}"; \
    cd "glibc-${GLIBC_DEBIAN_VERSION%%-*}"; \
    for patch in /tmp/glibc-patches/*.patch; do \
      if git apply --check "$patch"; then \
        git apply "$patch"; \
      elif git apply --reverse --check "$patch"; then \
        echo "Patch already present in Debian source: $patch"; \
      else \
        echo "Patch is neither applicable nor already present: $patch" >&2; \
        exit 1; \
      fi; \
    done; \
    DEBFULLNAME="rcamarda390 image build" \
      DEBEMAIL="rcamarda390@users.noreply.github.com" \
      dch --force-distribution --distribution "${DEBIAN_SUITE}" \
        --newversion "${GLIBC_BACKPORT_VERSION}" \
        "Rebuild from Debian deb13u4; retain local backports for CVE-2026-5435, CVE-2026-5450, and CVE-2026-5928."; \
    DEB_BUILD_OPTIONS="nocheck" dpkg-buildpackage -B -uc -us -j"$(nproc)"; \
    cp ../libc6_*_*.deb ../libc-bin_*_*.deb /out/; \
    dpkg-deb -f /out/libc6_*_*.deb Version | grep -Fx "${GLIBC_BACKPORT_VERSION}"; \
    dpkg-deb -f /out/libc-bin_*_*.deb Version | grep -Fx "${GLIBC_BACKPORT_VERSION}"

FROM alpine:3.23.4@sha256:5b10f432ef3da1b8d4c7eb6c487f2f5a8f096bc91145e68878dd4a5019afde11 AS source
ARG HEADROOM_VERSION
ARG HEADROOM_COMMIT
RUN apk add --no-cache ca-certificates git \
    && git clone --depth 1 --branch "v${HEADROOM_VERSION}" \
       https://github.com/headroomlabs-ai/headroom.git /src \
    && test "$(git -C /src rev-parse HEAD)" = "$HEADROOM_COMMIT"

FROM python:${PYTHON_VERSION}-slim-${DEBIAN_SUITE} AS builder
ARG HEADROOM_VERSION
ARG PYTHON_VERSION
ARG PIP_VERSION
ARG LITELLM_VERSION
ARG PYJWT_VERSION
ARG TOKENIZERS_VERSION
ARG TRANSFORMERS_VERSION
ARG URLLIB3_VERSION
ARG ANYIO_VERSION
ARG RUSTUP_VERSION
ARG SQLITE_VERSION
ARG SQLITE_AUTOCONF
ARG SQLITE_SHA3
ARG ZLIB_VERSION
ARG ZLIB_SHA256

ENV CARGO_HOME=/usr/local/cargo \
    RUSTUP_HOME=/usr/local/rustup \
    PATH=/usr/local/cargo/bin:${PATH} \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
       build-essential g++ curl ca-certificates patchelf \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir \
      "pip==${PIP_VERSION}" \
      "uv==0.11.18"

# Debian trixie's SQLite fixes CVE-2025-7458, but its 3.46 package predates
# the 3.53.2 fixes for CVE-2026-11822 and CVE-2026-11824. Build the current
# upstream 3.53.4 amalgamation as a shared library, verify SQLite's published
# SHA3-256, and retain FTS5 rather than avoiding the vulnerable code by
# disabling application functionality.
RUN set -eux; \
    curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
      "https://sqlite.org/2026/sqlite-autoconf-${SQLITE_AUTOCONF}.tar.gz" \
      --output /tmp/sqlite.tar.gz; \
    python -c "import hashlib; actual=hashlib.file_digest(open('/tmp/sqlite.tar.gz','rb'),'sha3_256').hexdigest(); assert actual == '${SQLITE_SHA3}', actual"; \
    tar -xzf /tmp/sqlite.tar.gz -C /tmp; \
    mkdir -p /opt/sqlite/lib; \
    cc -O2 -fPIC -shared -Wl,-soname,libsqlite3.so.0 \
      -DSQLITE_THREADSAFE=1 \
      -DSQLITE_ENABLE_COLUMN_METADATA \
      -DSQLITE_ENABLE_DBSTAT_VTAB \
      -DSQLITE_ENABLE_FTS5 \
      -DSQLITE_ENABLE_MATH_FUNCTIONS \
      -DSQLITE_ENABLE_RTREE \
      "/tmp/sqlite-autoconf-${SQLITE_AUTOCONF}/sqlite3.c" \
      -ldl -lpthread -lm \
      -o /opt/sqlite/lib/libsqlite3.so.0.8.6; \
    ln -s libsqlite3.so.0.8.6 /opt/sqlite/lib/libsqlite3.so.0; \
    LD_LIBRARY_PATH=/opt/sqlite/lib python -c "import sqlite3; assert sqlite3.sqlite_version == '${SQLITE_VERSION}', sqlite3.sqlite_version; db=sqlite3.connect(':memory:'); db.execute('create virtual table docs using fts5(body)'); db.execute('insert into docs values (\"headroom\")'); assert db.execute('select body from docs where docs match \"headroom\"').fetchone() == ('headroom',)"; \
    rm -rf /tmp/sqlite.tar.gz "/tmp/sqlite-autoconf-${SQLITE_AUTOCONF}"
# Xray fixes CVE-2026-85091 and CVE-2026-27171 in zlib 1.3.2. Debian
# Trixie's zlib1g release remains at 1.3.1, while Python's stdlib module needs
# libz.so.1 at runtime. Build the checksum-pinned upstream release, retain its
# ABI-compatible shared library, and remove the older Debian package only
# after every apt operation is complete.
RUN set -eux; \
    curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
      "https://github.com/madler/zlib/archive/refs/tags/v${ZLIB_VERSION}.tar.gz" \
      --output /tmp/zlib.tar.gz; \
    echo "${ZLIB_SHA256}  /tmp/zlib.tar.gz" | sha256sum --check --status; \
    tar -xzf /tmp/zlib.tar.gz -C /tmp; \
    cd "/tmp/zlib-${ZLIB_VERSION}"; \
    ./configure --prefix=/opt/zlib; \
    make -j"$(nproc)" install; \
    LD_LIBRARY_PATH=/opt/zlib/lib python -c \
      "import zlib; assert zlib.ZLIB_RUNTIME_VERSION == '${ZLIB_VERSION}', zlib.ZLIB_RUNTIME_VERSION"; \
    rm -rf /tmp/zlib.tar.gz "/tmp/zlib-${ZLIB_VERSION}"
# Checksums come from the matching rustup-init.sha256 file in the Rust release
# archive.
RUN set -eux; \
    case "$(dpkg --print-architecture)" in \
      amd64) rust_arch=x86_64-unknown-linux-gnu; rust_sha=20a06e644b0d9bd2fbdbfd52d42540bdde820ea7df86e92e533c073da0cdd43c ;; \
      arm64) rust_arch=aarch64-unknown-linux-gnu; rust_sha=e3853c5a252fca15252d07cb23a1bdd9377a8c6f3efa01531109281ae47f841c ;; \
      *) echo "Unsupported architecture for rustup installer" >&2; exit 1 ;; \
    esac; \
    curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
      "https://static.rust-lang.org/rustup/archive/${RUSTUP_VERSION}/${rust_arch}/rustup-init" \
      --output /tmp/rustup-init; \
    echo "${rust_sha}  /tmp/rustup-init" | sha256sum --check --status; \
    chmod +x /tmp/rustup-init; \
    /tmp/rustup-init -y --no-modify-path --profile minimal \
      -c rustfmt -c clippy --default-toolchain 1.95.0; \
    rm /tmp/rustup-init

WORKDIR /build
COPY --from=source /src/pyproject.toml /src/uv.lock /src/README.md ./
COPY --from=source /src/Cargo.toml /src/Cargo.lock /src/rust-toolchain.toml ./
COPY --from=source /src/crates/ crates/
COPY --from=source /src/headroom/ headroom/

# The pinned upstream release can contain a lockfile that uv considers stale
# when evaluated against the release metadata. Use the checked-in resolution
# without attempting to rewrite it during the image build.
# The proxy extra includes Headroom's MCP server, compression, and general
# LiteLLM backends. The bedrock extra adds boto3 and botocore for AWS SDK
# support required to reach AWS Bedrock from an air-gapped GovCloud environment.
RUN uv sync --frozen --extra proxy --extra bedrock --no-dev --no-editable
# Headroom 0.39.1's lock resolves LiteLLM 1.88.1. Keep the Bedrock cache-point
# conversion on the tested 1.101.0 runtime used by the preceding image release.
RUN uv pip install --python /opt/venv/bin/python --upgrade-package litellm \
      "litellm==${LITELLM_VERSION}" \
    && PATH="/opt/venv/bin:${PATH}" python -c \
      "import importlib.metadata; assert importlib.metadata.version('litellm') == '${LITELLM_VERSION}'"
# Debian's tracker records CVE-2026-64847, CVE-2026-63374, and
# CVE-2026-63349 against the locked AnyIO 4.12.1; all three are fixed upstream
# in 4.14.2. Keep the upstream lock immutable, then apply this narrow runtime
# override until a future Headroom release locks AnyIO at the fixed floor.
RUN uv pip install --python /opt/venv/bin/python --upgrade-package anyio \
      "anyio==${ANYIO_VERSION}" \
    && test "$(PATH="/opt/venv/bin:${PATH}" python -c 'import importlib.metadata; print(importlib.metadata.version("anyio"))')" = "$ANYIO_VERSION"
# Xray reports these high/critical PyJWT advisories against the upstream lock's
# 2.13.0 release: XRAY-1076251 (CVSS 9.1, CWE-347), XRAY-1076205,
# XRAY-1076201, XRAY-1076198, XRAY-1076197, XRAY-1076195, and XRAY-1076185
# (each CVSS 7.4). Their fixed floor is 2.14.0. CVE-2026-85670 separately
# fixes Tokenizers 0.22.2 in 0.23.1; Transformers 5.13.1 caps Tokenizers at
# 0.23.0. Headroom 0.39.1's installed Transformers 5.17.0 allows
# tokenizers>=0.23.1,<0.24.0, so 0.23.2 (the latest release in that range as
# of the 2026-09-18 scan) is used instead of the 0.23.1 floor. This downstream
# override is scoped to these package families; remove it when Headroom locks
# these or newer releases itself.
RUN uv pip install --python /opt/venv/bin/python \
      --upgrade-package PyJWT \
      --upgrade-package tokenizers \
      --upgrade-package transformers \
      "PyJWT==${PYJWT_VERSION}" \
      "tokenizers==${TOKENIZERS_VERSION}" \
      "transformers==${TRANSFORMERS_VERSION}" \
    && PATH="/opt/venv/bin:${PATH}" python -c \
      "import importlib.metadata, jwt, tokenizers, transformers; \
       assert importlib.metadata.version('PyJWT') == '${PYJWT_VERSION}'; \
       assert tokenizers.__version__ == '${TOKENIZERS_VERSION}'; \
       assert transformers.__version__ == '${TRANSFORMERS_VERSION}'" \
    && ! PATH="/opt/venv/bin:${PATH}" python -c "import pip" 2>/dev/null
# The 2026-09-18 Xray scan reports XRAY-1079914 (CWE-295/440) and XRAY-1079919
# (CWE-835) against the upstream lock's urllib3 2.7.0 with no fixed version
# published yet, plus XRAY-1079926 (CWE-770) whose stated fix floor, 2.7.0, is
# already installed. urllib3 2.8.0 (released 2026-09-15, three days before the
# scan) is the newest release on PyPI; move to it so the image carries
# whatever fix each advisory ships with once Xray's database catches up.
# botocore accepts urllib3<3 for Python >=3.10, so this stays within its
# declared range; the assertion below proves boto3/botocore still import
# cleanly against the bumped version.
RUN uv pip install --python /opt/venv/bin/python --upgrade-package urllib3 \
      "urllib3==${URLLIB3_VERSION}" \
    && PATH="/opt/venv/bin:${PATH}" python -c \
      "import importlib.metadata, boto3, botocore; \
       assert importlib.metadata.version('urllib3') == '${URLLIB3_VERSION}'" \
    && ! PATH="/opt/venv/bin:${PATH}" python -c "import pip" 2>/dev/null
# The setuptools/msgpack upgrades that used to live here targeted packages
# that Headroom does not install: neither appears in the proxy+bedrock
# resolution. Re-check that on an upstream version bump with `uv export
# --frozen --extra proxy --extra bedrock --no-dev`. Trivy reports any
# reappearance with a known advisory.
RUN cd /tmp && PATH="/opt/venv/bin:${PATH}" python -c \
    "from headroom._core import DiffCompressor, SmartCrusher; \
     print(f'Headroom Rust core OK: {DiffCompressor.__name__}, {SmartCrusher.__name__}')"
RUN test "$(PATH="/opt/venv/bin:${PATH}" python -c 'import importlib.metadata; print(importlib.metadata.version("headroom-ai"))')" = "$HEADROOM_VERSION"
RUN PATH="/opt/venv/bin:${PATH}" python -c \
    "import boto3, botocore; \
     print(f'Bedrock dependencies OK: boto3 {boto3.__version__}, botocore {botocore.__version__}')"

# ---------------------------------------------------------------------------
# Downstream carry: Cline's OpenAI-compatible transport to AWS Bedrock.
# Short-lived -- delete this block, the two ENV lines in the runtime stage that
# reference it, and the two scripts once the fixes land upstream. See
# CLINE_BEDROCK.md.
#
# Apply the patch directly to the venv built from the pinned upstream source so
# one action produces the complete deployable image. The patch fails closed if
# upstream's two OpenAI call sites change, and the regression script verifies
# both streaming and non-streaming Bedrock behavior.
COPY patch-headroom-bedrock-openai.py bedrock-openai-regression.py /tmp/
RUN set -eu; \
    export PATH="/opt/venv/bin:${PATH}"; \
    cd /tmp; \
    target="$(python -c 'import headroom.backends.litellm as m; print(m.__file__)')"; \
    python /tmp/patch-headroom-bedrock-openai.py "$target"; \
    python -m py_compile "$target"; \
    python /tmp/bedrock-openai-regression.py
# ---------------------------------------------------------------------------

# Pre-cache Hugging Face models needed for Kompress compression in the air-gapped runtime.
# When HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1 are set at runtime, these models
# must already be present in the image cache. Kompress uses:
#   - chopratejas/kompress-v2-base: ONNX model for text importance scoring
#   - answerdotai/ModernBERT-base: Tokenizer (shared with Kompress model)
# Only the required ONNX artifacts and tokenizer are downloaded, not full weights.
# Timeout/retry handling: HF downloads can timeout; skip this step if network fails.
ENV HF_HOME=/opt/headroom-cache/huggingface
RUN mkdir -p /opt/headroom-cache/huggingface || true
RUN <<EOF
#!/bin/sh
set -eu
export PATH="/opt/venv/bin:${PATH}"
python << 'HFCACHE'
import os
import sys
from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer

hf_home = '/opt/headroom-cache/huggingface'
os.environ['HF_HOME'] = hf_home

# Download Kompress model artifacts: prefer int8-wo (weight-only quantized),
# fallback to fp32 and older int8 for compatibility
kompress_model = 'chopratejas/kompress-v2-base'
kompress_onnx_files = [
    'onnx/kompress-int8-wo.onnx',
    'onnx/kompress-fp32.onnx',
    'onnx/kompress-int8.onnx',
]

onnx_success = False
for onnx_file in kompress_onnx_files:
    try:
        hf_hub_download(
            repo_id=kompress_model,
            filename=onnx_file,
            repo_type="model",
            resume_download=True,
            force_download=False,
        )
        print(f"✓ Downloaded {kompress_model}/{onnx_file}")
        onnx_success = True
        break  # Use first successfully downloaded artifact
    except Exception as e:
        print(f"⚠ Could not download {onnx_file}: {e}")

if not onnx_success:
    print("⚠ Warning: Could not download Kompress ONNX artifact, models will be downloaded at runtime")
else:
    # Download tokenizer from ModernBERT-base (Kompress reuses this exact tokenizer)
    tokenizer_model = "answerdotai/ModernBERT-base"
    try:
        AutoTokenizer.from_pretrained(
            tokenizer_model,
            trust_remote_code=True,
        )
        print(f"✓ Downloaded tokenizer from {tokenizer_model}")
    except Exception as e:
        print(f"⚠ Warning: Could not download tokenizer from {tokenizer_model}: {e}")

print("✓ Hugging Face model cache population completed (may be partial)")
HFCACHE
EOF


FROM python:${PYTHON_VERSION}-slim-${DEBIAN_SUITE} AS runtime_rootfs
ARG HEADROOM_VERSION
ARG HEADROOM_COMMIT
ARG LITELLM_VERSION
ARG PYJWT_VERSION
ARG TOKENIZERS_VERSION
ARG TRANSFORMERS_VERSION
ARG URLLIB3_VERSION
ARG ANYIO_VERSION
ARG GLIBC_BACKPORT_VERSION
ARG PYTHON_VERSION
ARG PYTHON_ABI
ARG SQLITE_VERSION
ARG ZLIB_VERSION

ENV HEADROOM_HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/opt/venv/bin:${PATH} \
    HF_HOME=/opt/headroom-cache/huggingface \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    LITELLM_LOCAL_MODEL_COST_MAP=True \
    HEADROOM_UPDATE_CHECK=off

# Skip only Headroom's external upstream readiness probe. The air-gapped
# GovCloud runtime intentionally cannot reach the Anthropic HTTP endpoint;
# this does not change TLS verification for real Bedrock traffic.
ENV HEADROOM_SKIP_UPSTREAM_CHECK=1

# Enable Headroom's live per-request output-token shaping. No fixed verbosity
# level is set; a learned profile remains a deployment-time choice.
ENV HEADROOM_OUTPUT_SHAPER=1

COPY --from=glibc_patched /out/ /tmp/glibc/
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends /tmp/glibc/libc6_*_*.deb /tmp/glibc/libc-bin_*_*.deb \
    && rm -rf /tmp/glibc \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --create-home --home-dir /home/headroom \
      --shell /bin/false headroom \
    && mkdir -p /home/headroom/.headroom \
    && chown -R headroom:headroom /home/headroom
# Remove the base interpreter's pip instead of upgrading it. Nothing in this
# image runs pip: the payload is /opt/venv, which uv builds without seeding
# pip, and the entrypoint invokes /opt/venv/bin/headroom directly.
#
# Upgrading pip here is what put the scanner's three "fixable" findings in the
# image in the first place. pip vendors its own dependency tree, and
# pip 26.2.1's pip/_vendor/vendor.txt pins exactly the versions reported:
#   setuptools==70.3.0  -> CVE-2026-23949, CVE-2025-47273
#   msgpack==1.1.2      -> CVE-2026-57585
# Bumping PIP_VERSION cannot fix those, because the vendored pins travel with
# whatever pip release is installed; only removing pip removes the files. The
# ensurepip bundled wheel carries the same vendored tree, so it goes too.
#
# Neither finding was reachable -- nothing invokes pip at runtime, and the
# vendored msgpack is the pure-Python fallback with no _cmsgpack extension,
# while CVE-2026-57585 is a use-after-free that can only exist in the C
# extension -- but the code is genuinely gone now rather than argued away.
# The verification at the end of this stage asserts pip is absent, so this
# cannot silently regress into a no-op.
RUN rm -rf /usr/local/lib/python${PYTHON_ABI}/site-packages/pip \
           /usr/local/lib/python${PYTHON_ABI}/site-packages/pip-*.dist-info \
           /usr/local/lib/python${PYTHON_ABI}/ensurepip/_bundled \
           /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip${PYTHON_ABI} \
           /root/.cache
# Every perl-base CVE the scanner reports against the Debian runtime is published with no
# fixed version, so `apt-get upgrade` above cannot clear them. Nothing in this
# image invokes perl: the entrypoint is dash and the payload is Python plus a
# Rust extension module. Drop the package outright rather than carry unfixable
# findings. dpkg is used instead of `apt-get purge --auto-remove` because
# perl-base is Essential and apt would cascade into debconf; no further apt
# operations run after this layer, so the unsatisfied dependency is inert. The
# final check fails the build if perl somehow survives, so this can never
# silently degrade into a no-op.
RUN dpkg --purge --force-depends --force-remove-essential perl-base \
    && ! command -v perl
# Scanner-visible packages that are not used at runtime are removed after the
# final apt operation:
#   gzip            -- nothing shells out to gzip or untars at runtime. Python
#                      still retains the dynamically linked zlib module.
#   ncurses packages -- CVE-2025-69720 is in the infocmp CLI. Headroom has no
#                       terminal UI, so both the CLI and Python's optional
#                       _curses modules are removed instead of retaining the
#                       source-package finding through libncursesw6.
#   libacl1        CVE-2026-54369 -- only cp/mv/install/tar link libacl.so.1;
#   libattr1       CVE-2026-54371    headroom uses mkdir/chown/cat only
#   libpam0g       CVE-2025-8941  -- headroom doesn't authenticate through PAM;
#   libpam-modules, libpam-modules-bin, libpam-runtime
#                                     user lookup uses glibc NSS, not PAM
#   libtasn1-6     CVE-2025-13151 -- only used for X.509 cert parsing; Python's
#                                    ssl uses system certs, doesn't need libtasn1
#   openssl         -- the CLI is unused; Python ssl retains trixie's patched
#                      libssl runtime package.
#   tar             CVE-2026-5704, CVE-2026-18477, CVE-2026-18508,
#                    CVE-2005-2541 -- headroom never shells out to tar; the
#                    only archive handling in the image is the build-time HF
#                    artifact download (individual ONNX/tokenizer files, not
#                    tarballs). Python's stdlib tarfile module, unaffected by
#                    these findings, remains available if ever needed.
#   libudev1        CVE-2026-40228, CVE-2026-15059, CVE-2023-31439,
#                    CVE-2023-31438 -- device hot-plug enumeration. This
#                    container runs no udev daemon and headroom never queries
#                    device metadata.
#   libsystemd0     CVE-2013-4392, CVE-2026-16742, CVE-2023-31437 -- systemd
#                    IPC/journal client library. No systemd process runs as
#                    PID 1 or otherwise in this image; headroom's proxy has no
#                    systemd integration (no sd_notify, no journal logging).
#   apt, libapt-pkg7.0
#                    CVE-2011-3374 -- package management is build-only and
#                    this air-gapped runtime does not invoke apt after its
#                    final package installation. Debian records the advisory
#                    as not exploitable in Debian, but removing the unused
#                    binaries and library eliminates the runtime attack
#                    surface entirely.
#   diffutils       CVE-2026-53910 -- Headroom parses and compresses diffs in
#                    Python/Rust; it never invokes diff, diff3, or cmp. Debian
#                    has no packaged fix, so do not retain an unused toolset.
#   login, passwd, login.defs
#                    CVE-2026-3184, CVE-2026-76642, CVE-2026-78408,
#                    CVE-2026-78409, CVE-2026-78410, CVE-2024-56433, and
#                    CVE-2007-5686 -- these are interactive-login and account
#                    administration tools. `useradd` is needed only above to
#                    create the fixed service account. Docker starts the
#                    entrypoint as that existing account; Headroom's proxy does
#                    not authenticate through PAM or invoke login, passwd,
#                    useradd, groupadd, chage, or nologin. Keep /bin/false as
#                    the account shell before purging login's nologin binary.
#   liblastlog2-2   CVE-2022-0563 -- records PAM login history; already
#                    unreachable now that the libpam-* packages above are
#                    gone, since nothing in the image performs an
#                    interactive/PAM login. (The 2026-09-18 Xray report
#                    attributed CVE-2026-78408 to this package, but the
#                    0.37.0-v14 build's Trivy scan shows it's actually a
#                    util-linux/nsenter advisory -- see the note further
#                    down near the util-linux version check. Removing
#                    liblastlog2-2 doesn't clear it.)
#
# Headroom imports sqlite3 on the `mcp serve` path (compression cache store,
# memory store, and Codex thread recovery), so SQLite cannot simply disappear.
# The builder compiles the verified 3.53.4 upstream release; copy it into the
# loader's preferred /usr/local path, then remove Debian's older libsqlite3-0
# package so scanners see only the remediated implementation. The final check
# exercises both ordinary queries and FTS5 through Python's real extension.
#
# The scanner's remaining critical/high findings are in trixie's glibc 2.41
# packages. Debian has no stable fix yet, so the glibc_patched stage rebuilds
# the matching trixie source package with upstream release/2.41 fixes for
# CVE-2026-5435, CVE-2026-5450, and CVE-2026-5928, and the runtime stage
# installs the coherent libc6/libc-bin pair from that rebuild.
# dpkg is used instead of `apt-get purge --auto-remove` because gzip and
# ncurses-bin are Essential and apt would cascade into debconf. No apt
# operations run after this layer, so unsatisfied dependencies are inert.
#
# libpam-modules needs both halves of this next step. apt cannot do it:
# util-linux PreDepends on libpam-modules, and apt will not break a PreDepends,
# so it re-selects the package for install and declines. dpkg can force past
# that -- util-linux is on the very line below -- but its postrm execs
# /usr/share/debconf/frontend, and the perl-base purge above cascades into
# debconf, so the script exits 127 and fails the build. The stub below
# satisfies the exec so the purge completes and dpkg records it as such.
# Skipping that cleanup is harmless: it only drops the package's entries from
# the debconf database. dpkg removes the package's files either way.
COPY --from=builder /opt/sqlite/lib/ /usr/local/lib/
COPY --from=builder /opt/zlib/lib/ /usr/local/lib/
RUN ldconfig \
 && rm -f /usr/local/lib/python${PYTHON_ABI}/lib-dynload/_curses*.so \
 && mkdir -p /usr/share/debconf \
 && printf '#!/bin/sh\nexit 0\n' > /usr/share/debconf/frontend \
 && chmod 0755 /usr/share/debconf/frontend \
 && dpkg --purge --force-depends --force-remove-essential --force-remove-protected \
      gzip ncurses-bin ncurses-base libtinfo6 libncursesw6 \
      libacl1 libattr1 \
      libpam-runtime libpam-modules libpam-modules-bin libpam0g libtasn1-6 \
      libsqlite3-0 zlib1g openssl \
      tar libudev1 libsystemd0 liblastlog2-2 \
      apt libapt-pkg7.0 diffutils \
      login passwd login.defs \
 && rm -rf /usr/share/debconf
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/headroom-cache /opt/headroom-cache
COPY mcp-smoke.py /usr/local/bin/mcp-smoke.py
COPY entrypoint.sh /usr/local/bin/headroom-entrypoint
RUN find /usr/local/lib/python${PYTHON_ABI} /opt/venv \
      -name '_curses*.so' -delete \
    && chmod +x /usr/local/bin/headroom-entrypoint \
    && chown -R headroom:headroom /opt/headroom-cache
# Verify that purged packages didn't break critical runtime functionality.
# `python -c "import sys"` proved nothing: it passed while libsqlite3-0 was
# purged, so a green build shipped an image that died on startup. Import every
# stdlib module whose backing shared library a purge could plausibly remove and
# actually exercise sqlite3 and ssl, so a bad purge fails here -- in the stage
# that caused it -- instead of surfacing later as an opaque MCP startup error.
# bz2 is imported and exercised below because headroom's `mcp serve` path can
# reach it (compressed cache/session data); CVE-2026-42250 (libbz2-1.0,
# CWE-787) has no fixed version published anywhere upstream or in Debian as of
# the 2026-09-18 scan, so there is nothing to upgrade to and the module cannot
# be dropped without breaking the import check that already guards this stage.
# Tracked as an open, currently unfixable finding -- re-scan on the next
# rebuild to pick up a Debian security update once one ships.
#
# Correction (2026-09-18, post-publish): the 0.37.0-v14 build's own Trivy scan
# shows util-linux 1:2.41.5-0+deb13u1 -- meeting the floor below -- still
# "affected" with no Fixed Version for CVE-2026-76642, CVE-2026-78408,
# CVE-2026-78409, and CVE-2026-78410 (bsdutils, mount, libblkid1, libmount1,
# and siblings from the same source package). Xray's "2.41.5" and "6.15"
# fix-version hints do not hold up against Debian's real advisory status:
# none of these four are fixed in trixie yet, not just CVE-2026-78409. The
# assertion below is kept as a floor/regression guard (fail the build if a
# future rebuild somehow lands on an older util-linux than this scan already
# covered), not as proof of remediation. All four are open, upstream/Debian
# findings with no fix to apply from this image build; re-scan each rebuild
# to pick up a Debian security update once one ships.
# Headroom 0.39.1's SBOM/lock resolves LiteLLM 1.88.1, below the image's
# verified 1.101.0 Bedrock-cache runtime and XRAY-1062440's fixed floor. Keep
# the tested version pinned above and assert it survives into the final image.
RUN PATH="/opt/venv/bin:${PATH}" python -c \
    "import importlib.util, ssl, sqlite3, hashlib, lzma, bz2, ctypes, zlib, socket; \
     assert sqlite3.sqlite_version == '${SQLITE_VERSION}', sqlite3.sqlite_version; \
     assert zlib.ZLIB_RUNTIME_VERSION == '${ZLIB_VERSION}', zlib.ZLIB_RUNTIME_VERSION; \
     sqlite3.connect(':memory:').execute('select 1').fetchone(); \
     db=sqlite3.connect(':memory:'); db.execute('create virtual table docs using fts5(body)'); db.execute('insert into docs values (\"headroom\")'); assert db.execute('select body from docs where docs match \"headroom\"').fetchone() == ('headroom',); \
     assert importlib.util.find_spec('_curses') is None; \
     ssl.create_default_context(); \
     print(f'Verification: Python stdlib (SQLite {sqlite3.sqlite_version}, FTS5, ssl, compression) OK')" \
 && PATH="/opt/venv/bin:${PATH}" python -c \
    "from packaging.version import Version; import boto3, botocore, importlib.metadata, jwt, litellm, tokenizers, transformers, urllib3; \
     litellm_version = importlib.metadata.version('litellm'); \
     assert litellm_version == '${LITELLM_VERSION}', litellm_version; \
     assert Version(litellm_version) >= Version('1.96.2'), litellm_version; \
     assert importlib.metadata.version('anyio') == '${ANYIO_VERSION}'; \
     assert importlib.metadata.version('PyJWT') == '${PYJWT_VERSION}'; \
     assert tokenizers.__version__ == '${TOKENIZERS_VERSION}'; \
     assert transformers.__version__ == '${TRANSFORMERS_VERSION}'; \
     assert importlib.metadata.version('urllib3') == '${URLLIB3_VERSION}'; \
     print(f'Verification: LiteLLM {litellm_version}, PyJWT {importlib.metadata.version(\"PyJWT\")}, Tokenizers {tokenizers.__version__}, Transformers {transformers.__version__}, urllib3 {urllib3.__version__}; AWS dependencies (boto3 {boto3.__version__}, botocore {botocore.__version__}) OK')" \
 && { PATH="/opt/venv/bin:${PATH}" python -c \
    "import awscrt; print(f'  awscrt {awscrt.__version__} also available')" || true; } \
 && /bin/dash -c "echo 'Verification: dash entrypoint shell OK'" \
 && test "$(dpkg-query -W -f='${Version}' libc6)" = "${GLIBC_BACKPORT_VERSION}" \
 && test "$(dpkg-query -W -f='${Version}' libc-bin)" = "${GLIBC_BACKPORT_VERSION}" \
 && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' libssl3t64)" ge '3.5.7-1~deb13u2' \
 && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' util-linux)" ge '2.41.5' \
 && dpkg-query -W libc6 libc-bin libssl3t64 util-linux \
 && for package in \
      libsqlite3-0 zlib1g libpam-modules-bin libncursesw6 openssl tar libudev1 \
      libsystemd0 liblastlog2-2 apt libapt-pkg7.0 diffutils login passwd login.defs; do \
      ! dpkg-query -W "$package" 2>/dev/null; \
    done \
 && getent passwd headroom >/dev/null \
 && ! command -v perl \
 && ! command -v gzip \
 && ! command -v tar \
 && ! command -v apt \
 && ! command -v diff \
 && ! command -v login \
 && ! command -v passwd \
 && ! command -v useradd \
 && ! command -v groupadd \
 && ! command -v chage \
 && ! command -v nologin \
 && ! command -v tput \
 && ! command -v openssl \
 && ! command -v pip \
 && ! PATH="/opt/venv/bin:${PATH}" python -c "import pip" 2>/dev/null


# Xray reports packages/files from superseded base-image layers even after the
# runtime stage upgrades or removes them. Copy the fully verified effective
# root filesystem into a fresh final stage so scanners see exactly what runs.
# This retains all final files and dpkg records; it does not suppress findings.
FROM scratch AS runtime
COPY --from=runtime_rootfs / /

ARG HEADROOM_VERSION
ARG HEADROOM_COMMIT

ENV HEADROOM_HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    HF_HOME=/opt/headroom-cache/huggingface \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    LITELLM_LOCAL_MODEL_COST_MAP=True \
    HEADROOM_UPDATE_CHECK=off \
    HEADROOM_SKIP_UPSTREAM_CHECK=1 \
    HEADROOM_OUTPUT_SHAPER=1

USER headroom
WORKDIR /home/headroom
VOLUME ["/home/headroom/.headroom"]

LABEL org.opencontainers.image.title="headroom-mcp" \
      org.opencontainers.image.description="Headroom MCP server for context optimization" \
      org.opencontainers.image.source="https://github.com/headroomlabs-ai/headroom" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="${HEADROOM_VERSION}" \
      org.opencontainers.image.revision="${HEADROOM_COMMIT}"

ENTRYPOINT ["/usr/local/bin/headroom-entrypoint"]
