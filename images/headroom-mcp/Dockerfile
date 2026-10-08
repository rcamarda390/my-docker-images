# syntax=docker/dockerfile:1.7

ARG HEADROOM_VERSION=0.40.0
ARG HEADROOM_COMMIT=855390d6110e0bbb199d9b97025baac16c2f5cf3
ARG LITELLM_VERSION=1.101.3
ARG PYTHON_VERSION=3.13.15
ARG PYTHON_ABI=3.13
ARG DEBIAN_SUITE=trixie
ARG GLIBC_DEBIAN_VERSION=2.41-12+deb13u4
ARG GLIBC_BACKPORT_VERSION=2.41-12+deb13u4+rcamarda2
ARG PIP_VERSION=26.2.1
ARG PYJWT_VERSION=2.15.1
ARG TOKENIZERS_VERSION=0.23.2
ARG TOKENIZERS_BACKPORT_VERSION=0.23.2+rcamarda1
ARG TOKENIZERS_SOURCE_SHA256=7f0f085686b9de0d0079e6f874ae053600db64c5d13049e0bbc0119926d25aac
ARG MCP_VERSION=1.30.0
ARG FSSPEC_VERSION=2026.6.0
ARG MULTIDICT_VERSION=6.9.1
ARG DASH_DEBIAN_VERSION=0.5.12-12
ARG DASH_BACKPORT_VERSION=0.5.12-12+rcamarda1
ARG TRANSFORMERS_VERSION=5.17.0
ARG URLLIB3_VERSION=2.8.0
ARG RUSTUP_VERSION=1.28.2
ARG SQLITE_VERSION=3.53.4
ARG SQLITE_AUTOCONF=3530400
ARG SQLITE_SHA3=454e45f61c6bd75b7420e7190732dea03ce6639c63ada47bbc592f67fc340338
ARG ZLIB_VERSION=1.3.2
ARG ZLIB_SHA256=b99a0b86c0ba9360ec7e78c4f1e43b1cbdf1e6936c8fa0f6835c0cd694a495a1

# Retain the existing glibc fixes and reuse the checked Gnosis backports
# against the same Debian source. See SECURITY-20261005.md for CVE mapping.
FROM debian:${DEBIAN_SUITE}-slim AS glibc_patched
ARG DEBIAN_SUITE
ARG GLIBC_DEBIAN_VERSION
ARG GLIBC_BACKPORT_VERSION
ARG DASH_DEBIAN_VERSION
ARG DASH_BACKPORT_VERSION
COPY patches/glibc/ /tmp/glibc-patches/
COPY verify-glibc-normalize.c /tmp/verify-glibc-normalize.c
RUN set -eux; \
    sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/debian.sources; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl devscripts dpkg-dev git quilt; \
    apt-get build-dep -y --no-install-recommends "glibc=${GLIBC_DEBIAN_VERSION}" "dash=${DASH_DEBIAN_VERSION}"; \
    mkdir -p /build /out; cd /build; \
    apt-get source "glibc=${GLIBC_DEBIAN_VERSION}"; \
    cd "glibc-${GLIBC_DEBIAN_VERSION%%-*}"; \
    for patch_spec in \
      "965b580070b8184b0dd390800d9194291a600e67:e564c003db5103b22e5b5ed8d624690ca6722eb1cd1c5b867649a345694a7bdd" \
      "dfc8ef388ef7856f318ade7dec501f92ce54f9e3:d8646d3888c1c6bff55e77bbf275f5549391f4536efcd176c2a1e654857f8f4b" \
      "9318c2571576017d280a31b7b9ab576c9b696b1a:4dac7eb1610b938dbb3c9ddc390bdf0f4da01e1f757a47f61022ed45bffaa88e" \
      "5256941bc811248670eda4636dccd0a390d34dec:aaa730edd654b954bc7f2b82eaadee091d87c47c5ea250a9f579172cfbda6b96" \
      "e43e46f94398b3de446fec11da1e7633ea5202ec:b521dbf688487b2a6f3f4f51cc5968382cff04d556c56c25ae87b3b4905ce823" \
      "ec116a0fbedcc860631e525e70b409cf295f27da:eb93b11c64893543ad81a8afffbc9d51c822f8d60fc416439433f37dfcbc66cd" \
      "f806c45178dbca3be08a25cc5dd6d5542ce84a59:ffad85d2a8e7e6b420e085483a1ae1031a13421b5eb7c1df281b6e35468eb9c3" \
      "506ea57086bfb9ce3daff1c14246a1cb532aba0a:1e3b92a4fdb8ca306c8272b156a30ed9aa3b26f4851f11430b64b118621d5382"; do \
      commit="${patch_spec%%:*}"; checksum="${patch_spec#*:}"; \
      patch="/tmp/glibc-${commit}.patch"; \
      curl -fsSL "https://sourceware.org/git/?p=glibc.git;a=patch;h=${commit}" -o "$patch"; \
      echo "$checksum  $patch" | sha256sum -c -; \
      if git apply --check "$patch"; then \
        git apply "$patch"; \
      elif git apply --reverse --check "$patch"; then \
        echo "Upstream patch already present in Debian source: $commit"; \
      else \
        echo "Upstream patch is neither applicable nor already present: $commit" >&2; \
        exit 1; \
      fi; \
    done; \
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
    gcc -Wall -Wextra -Werror -O2 -I elf /tmp/verify-glibc-normalize.c -o /tmp/verify-glibc-normalize; \
    /tmp/verify-glibc-normalize; \
    DEBFULLNAME="rcamarda390 image build" DEBEMAIL="rcamarda390@users.noreply.github.com" \
      dch --force-distribution --distribution "${DEBIAN_SUITE}" --newversion "${GLIBC_BACKPORT_VERSION}" \
      "Retain Headroom rcamarda1 fixes; add resolver, wordexp, tdelete, strfmon, iconv and secure-loader backports."; \
    if ! DEB_BUILD_OPTIONS="nocheck" dpkg-buildpackage -B -uc -us -j"$(nproc)" > /tmp/glibc-build.log 2>&1; then \
      tail -n 200 /tmp/glibc-build.log; exit 1; \
    fi; \
    cp ../libc6_*_*.deb ../libc-bin_*_*.deb /out/; \
    dpkg-deb -f /out/libc6_*_*.deb Version | grep -Fx "${GLIBC_BACKPORT_VERSION}"; \
    dpkg-deb -f /out/libc-bin_*_*.deb Version | grep -Fx "${GLIBC_BACKPORT_VERSION}"

# CVE-2026-102473 affects Dash's recursive internal pattern matcher.
# Use its existing libc fnmatch build option rather than removing /bin/sh,
# which runs the service entrypoint.
RUN set -eux; \
    cd /build; apt-get source "dash=${DASH_DEBIAN_VERSION}"; \
    cd "dash-${DASH_DEBIAN_VERSION%%-*}"; \
    grep -q -- '--disable-fnmatch' debian/rules; \
    sed -i 's/--disable-fnmatch/--enable-fnmatch/' debian/rules; \
    DEBFULLNAME="rcamarda390 image build" DEBEMAIL="rcamarda390@users.noreply.github.com" \
      dch --force-distribution --distribution "${DEBIAN_SUITE}" --newversion "${DASH_BACKPORT_VERSION}" \
      "Use libc fnmatch instead of recursive pmatch for CVE-2026-102473."; \
    dpkg-buildpackage -B -uc -us -j"$(nproc)"; \
    grep -Fx '#define HAVE_FNMATCH 1' config.h; \
    cp ../dash_*_*.deb /out/; \
    dpkg-deb -f /out/dash_*_*.deb Version | grep -Fx "${DASH_BACKPORT_VERSION}"; \
    dpkg-deb -x /out/dash_*_*.deb /tmp/dash-check; \
    readelf -Ws /tmp/dash-check/usr/bin/dash | grep -E 'UND.* fnmatch@'

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
ARG TOKENIZERS_BACKPORT_VERSION
ARG TOKENIZERS_SOURCE_SHA256
ARG MCP_VERSION
ARG FSSPEC_VERSION
ARG MULTIDICT_VERSION
ARG TRANSFORMERS_VERSION
ARG URLLIB3_VERSION
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
# LiteLLM 1.101.3 fixes GHSA-7hp6-4w63-5g45 in the existing 1.101 line.
# The Bedrock regression below must still verify native cache-point conversion.
RUN uv pip install --python /opt/venv/bin/python --upgrade-package litellm \
      "litellm==${LITELLM_VERSION}" \
    && PATH="/opt/venv/bin:${PATH}" python -c \
      "import importlib.metadata; assert importlib.metadata.version('litellm') == '${LITELLM_VERSION}'"
# Keep the Transformers/tokenizer API range, then source-patch their unfixed
# load paths below. PyJWT 2.15.0 fixes CVE-2026-102275 and CVE-2026-101918.
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
# Upstream 0.40.0 already locks urllib3 2.8.0; verify without overriding it.
RUN PATH="/opt/venv/bin:${PATH}" python -c \
      "import importlib.metadata, boto3, botocore; \
       assert importlib.metadata.version('urllib3') == '${URLLIB3_VERSION}'" \
    && ! PATH="/opt/venv/bin:${PATH}" python -c "import pip" 2>/dev/null
# MCP stays on the supported 1.x API. Upstream 0.40.0 already locks
# the fixed fsspec and multidict releases, verified by security-regression.py.
RUN uv pip install --python /opt/venv/bin/python \
      --upgrade-package mcp "mcp==${MCP_VERSION}" \
    && uv pip check --python /opt/venv/bin/python

# 0.23.2 still contains CVE-2026-85670. Reuse the Gnosis bounds-check patch
# against this source release instead of downgrading to its patched 0.23.1.
COPY patches/tokenizers/ /tmp/tokenizers-patches/
RUN set -eux; \
    curl -fsSL https://files.pythonhosted.org/packages/18/1e/bc6587c5ab643b2e17776cace9070a2ae73549c86bffac9934a600bf3c31/tokenizers-0.23.2.tar.gz -o /tmp/tokenizers.tar.gz; \
    echo "${TOKENIZERS_SOURCE_SHA256}  /tmp/tokenizers.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/tokenizers.tar.gz -C /tmp; \
    cd "/tmp/tokenizers-${TOKENIZERS_VERSION}"; \
    patch -p1 < /tmp/tokenizers-patches/0001-bpe-reject-invalid-merges-CVE-2026-85670.patch; \
    python -c "from pathlib import Path; p=Path('bindings/python/Cargo.toml'); s=p.read_text(); old='version = \"${TOKENIZERS_VERSION}\"'; assert s.count(old) == 1; p.write_text(s.replace(old, 'version = \"${TOKENIZERS_BACKPORT_VERSION}\"')); p=Path('bindings/python/Cargo.lock'); s=p.read_text(); old='name = \"tokenizers-python\"\\nversion = \"${TOKENIZERS_VERSION}\"'; assert s.count(old) == 1; p.write_text(s.replace(old, old.replace('${TOKENIZERS_VERSION}', '${TOKENIZERS_BACKPORT_VERSION}')))"; \
    uv pip install --python /usr/local/bin/python "maturin==1.15.0"; \
    maturin build --release --locked --out /tmp/tokenizers-wheel --interpreter /opt/venv/bin/python; \
    python -c "from pathlib import Path; from zipfile import ZipFile; from email.parser import Parser; wheels=list(Path('/tmp/tokenizers-wheel').glob('*.whl')); assert len(wheels) == 1, wheels; z=ZipFile(wheels[0]); names=[n for n in z.namelist() if n.endswith('.dist-info/METADATA')]; assert len(names) == 1; m=Parser().parsestr(z.read(names[0]).decode()); assert m['Name'] == 'tokenizers', m['Name']; assert m['Version'] == '${TOKENIZERS_BACKPORT_VERSION}', m['Version']; assert 'tokenizers/__init__.py' in z.namelist()"; \
    uv pip install --python /opt/venv/bin/python --reinstall --no-deps /tmp/tokenizers-wheel/tokenizers-*.whl; \
    uv pip check --python /opt/venv/bin/python

# Transformers 5.17.0 still trusts local checkpoint weight_map paths.
COPY patch-transformers-shards.py security-regression.py /tmp/
RUN PATH="/opt/venv/bin:${PATH}" python /tmp/patch-transformers-shards.py \
    && PATH="/opt/venv/bin:${PATH}" python /tmp/security-regression.py packages

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
ARG TOKENIZERS_BACKPORT_VERSION
ARG TOKENIZERS_SOURCE_SHA256
ARG MCP_VERSION
ARG FSSPEC_VERSION
ARG MULTIDICT_VERSION
ARG TRANSFORMERS_VERSION
ARG URLLIB3_VERSION
ARG GLIBC_BACKPORT_VERSION
ARG DASH_BACKPORT_VERSION
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
    && apt-get install -y --no-install-recommends /tmp/glibc/libc6_*_*.deb /tmp/glibc/libc-bin_*_*.deb /tmp/glibc/dash_*_*.deb \
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
# The glibc_patched stage retains required libc/loader functionality and
# extends the local patch set against the same Debian 2.41 source.
# The coherent libc6/libc-bin pair is installed together; the custom revision
# is verified below. See SECURITY-20261005.md for individual dispositions.
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
# Headroom uses fcntl.flock and Python UUIDs, not util-linux commands.
# _uuid is optional: UUID generation falls back to Python/os.urandom.
# Proxy/MCP does not invoke coreutils; host-installation/wrapper features are
# outside this image's confirmed runtime scope. Audit reverse dependencies and
# every retained native library before removing the unused command suites.
COPY verify-runtime-unused.py security-regression.py /tmp/
RUN rm -f /usr/local/lib/python${PYTHON_ABI}/lib-dynload/_uuid*.so \
    && PATH="/opt/venv/bin:${PATH}" python /tmp/verify-runtime-unused.py \
    && dpkg --purge --force-depends --force-remove-essential --force-remove-protected --force-bad-path \
      util-linux mount bsdutils libmount1 libblkid1 libsmartcols1 libuuid1 coreutils \
    && PATH="/opt/venv/bin:${PATH}" python /tmp/security-regression.py runtime \
    && PATH="/opt/venv/bin:${PATH}" python -c "from pathlib import Path; Path('/tmp/verify-runtime-unused.py').unlink(); Path('/tmp/security-regression.py').unlink()"
# Verify that purged packages didn't break critical runtime functionality.
# `python -c "import sys"` proved nothing: it passed while libsqlite3-0 was
# purged, so a green build shipped an image that died on startup. Import every
# stdlib module whose backing shared library a purge could plausibly remove and
# actually exercise sqlite3 and ssl, so a bad purge fails here -- in the stage
# that caused it -- instead of surfacing later as an opaque MCP startup error.
# CVE-2026-42250 is in the bzip2recover CLI, not libbz2's decompressor.
# Keep Python bz2 for cache/session data; security-regression.py requires
# bzip2recover to be absent. No library fix is claimed for the scanner row.
#
# Runtime package versions and actual imports are checked after all carries.
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
     assert importlib.metadata.version('anyio') == '4.14.2'; \
     assert importlib.metadata.version('PyJWT') == '${PYJWT_VERSION}'; \
     assert importlib.metadata.version('mcp') == '${MCP_VERSION}'; \
     assert importlib.metadata.version('fsspec') == '${FSSPEC_VERSION}'; \
     assert importlib.metadata.version('multidict') == '${MULTIDICT_VERSION}'; \
     assert importlib.metadata.version('tokenizers') == '${TOKENIZERS_BACKPORT_VERSION}'; \
     assert transformers.__version__ == '${TRANSFORMERS_VERSION}'; \
     assert importlib.metadata.version('urllib3') == '${URLLIB3_VERSION}'; \
     print(f'Verification: LiteLLM {litellm_version}, PyJWT {importlib.metadata.version(\"PyJWT\")}, Tokenizers {tokenizers.__version__}, Transformers {transformers.__version__}, urllib3 {urllib3.__version__}; AWS dependencies (boto3 {boto3.__version__}, botocore {botocore.__version__}) OK')" \
 && { PATH="/opt/venv/bin:${PATH}" python -c \
    "import awscrt; print(f'  awscrt {awscrt.__version__} also available')" || true; } \
 && /bin/dash -c "echo 'Verification: dash entrypoint shell OK'" \
 && test "$(dpkg-query -W -f='${Version}' libc6)" = "${GLIBC_BACKPORT_VERSION}" \
 && test "$(dpkg-query -W -f='${Version}' libc-bin)" = "${GLIBC_BACKPORT_VERSION}" \
 && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' libssl3t64)" ge '3.5.7-1~deb13u3' \
 && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' openssl-provider-legacy)" ge '3.5.7-1~deb13u3' \
 && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' libpcre2-8-0)" ge '10.46-1~deb13u3' \
 && test "$(dpkg-query -W -f='${Version}' dash)" = "${DASH_BACKPORT_VERSION}" \
 && dpkg-query -W libc6 libc-bin libssl3t64 libpcre2-8-0 dash \
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
