# syntax=docker/dockerfile:1.7
# =============================================================================
# gnosis-mcp — air-gap variant
# =============================================================================
# Upstream 0.17.5 includes the combined REST/MCP lifespan required when
# mounting StreamableHTTP alongside the REST API. Earlier image revisions
# injected that fix with patch_rest.py; the local patch is no longer needed.
# Security: Python 3.13 on Debian Trixie plus checksum-pinned glibc, SQLite,
# and zlib fixes. Packages that are not required by the service are removed
# from the final filesystem. See SECURITY-v17.md for the finding disposition.
# =============================================================================

ARG PYTHON_VERSION=3.13

# ---------------------------------------------------------------------------
# Stage 1 — builder
# ---------------------------------------------------------------------------
ARG DEBIAN_SUITE=trixie
ARG GLIBC_DEBIAN_VERSION=2.41-12+deb13u4
ARG GLIBC_BACKPORT_VERSION=2.41-12+deb13u4+rcamarda3
ARG DASH_DEBIAN_VERSION=0.5.12-12
ARG DASH_BACKPORT_VERSION=0.5.12-12+rcamarda1

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
      "Retain rcamarda2 fixes; add CVE-2026-8674 resolver and CVE-2026-86805/CVE-2026-95818 secure-loader backports."; \
    DEB_BUILD_OPTIONS="nocheck" dpkg-buildpackage -B -uc -us -j"$(nproc)"; \
    cp ../libc6_*_*.deb ../libc-bin_*_*.deb /out/; \
    dpkg-deb -f /out/libc6_*_*.deb Version | grep -Fx "${GLIBC_BACKPORT_VERSION}"; \
    dpkg-deb -f /out/libc-bin_*_*.deb Version | grep -Fx "${GLIBC_BACKPORT_VERSION}"

# CVE-2026-102473 affects Dash's recursive internal pattern matcher.
# Use its existing libc fnmatch build option rather than removing /bin/sh,
# which is required by Docker's CMD-SHELL health checks.
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
    readelf -Ws "$(find /tmp/dash-check -type f -name dash -print -quit)" | grep -E 'UND.* fnmatch@'

FROM rust:1.94.0-slim-trixie AS rust_toolchain

FROM python:${PYTHON_VERSION}-slim-${DEBIAN_SUITE} AS builder
COPY --from=rust_toolchain /usr/local/cargo /usr/local/cargo
COPY --from=rust_toolchain /usr/local/rustup /usr/local/rustup
ENV CARGO_HOME=/usr/local/cargo \
    RUSTUP_HOME=/usr/local/rustup \
    PATH=/usr/local/cargo/bin:$PATH

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Debian Trixie's sqlite3 source remains vulnerable to CVE-2026-11822 and
# CVE-2026-11824. Build the fixed upstream release from SQLite's official
# amalgamation archive. SHA3-256 is published on sqlite.org/download.html.
# FTS5 is load-bearing for gnosis-mcp and must remain compiled in.
ARG SQLITE_AUTOCONF=3530400
ARG SQLITE_VERSION=3.53.4
ARG SQLITE_SHA3=454e45f61c6bd75b7420e7190732dea03ce6639c63ada47bbc592f67fc340338
RUN curl -fsSL "https://sqlite.org/2026/sqlite-autoconf-${SQLITE_AUTOCONF}.tar.gz" \
        -o /tmp/sqlite.tar.gz \
    && python -c "import hashlib; p='/tmp/sqlite.tar.gz'; actual=hashlib.sha3_256(open(p,'rb').read()).hexdigest(); expected='${SQLITE_SHA3}'; assert actual == expected, f'{actual} != {expected}'" \
    && tar -xzf /tmp/sqlite.tar.gz -C /tmp \
    && cd "/tmp/sqlite-autoconf-${SQLITE_AUTOCONF}" \
    && CFLAGS="-O2 -DSQLITE_ENABLE_FTS5 -DSQLITE_ENABLE_COLUMN_METADATA -DSQLITE_ENABLE_DBSTAT_VTAB -DSQLITE_ENABLE_RTREE -DSQLITE_ENABLE_UNLOCK_NOTIFY -DSQLITE_SECURE_DELETE" \
        ./configure --prefix=/opt/sqlite --disable-static --enable-fts5 \
    && make -j"$(nproc)" \
    && make install \
    && test "$(LD_LIBRARY_PATH=/opt/sqlite/lib /opt/sqlite/bin/sqlite3 :memory: 'select sqlite_version();')" = "${SQLITE_VERSION}" \
    && rm -rf /tmp/sqlite.tar.gz "/tmp/sqlite-autoconf-${SQLITE_AUTOCONF}"

# zlib 1.3.2 fixes CVE-2026-27171. CVE-2026-85091 was fixed after that
# release, so apply and checksum the exact upstream commit as well.
ARG ZLIB_VERSION=1.3.2
ARG ZLIB_SHA256=bb329a0a2cd0274d05519d61c667c062e06990d72e125ee2dfa8de64f0119d16
ARG ZLIB_CVE_PATCH_SHA256=110ff14375733173d8aa54574473424fbd7dfe4b81f1ca34a759c6fe14b15b14
RUN curl -fsSL "https://zlib.net/zlib-${ZLIB_VERSION}.tar.gz" -o /tmp/zlib.tar.gz \
    && echo "${ZLIB_SHA256}  /tmp/zlib.tar.gz" | sha256sum -c - \
    && curl -fsSL "https://github.com/madler/zlib/commit/df84af25dc1942490e1d1c899a07619152a46148.patch" \
        -o /tmp/zlib-cve-2026-85091.patch \
    && echo "${ZLIB_CVE_PATCH_SHA256}  /tmp/zlib-cve-2026-85091.patch" | sha256sum -c - \
    && tar --no-same-owner -xzf /tmp/zlib.tar.gz -C /tmp \
    && cd "/tmp/zlib-${ZLIB_VERSION}" \
    && patch -p1 < /tmp/zlib-cve-2026-85091.patch \
    && ./configure --prefix=/opt/zlib \
    && make -j"$(nproc)" \
    && make test \
    && make install \
    && test "$(LD_LIBRARY_PATH=/opt/zlib/lib ./example | sed -n '1s/^zlib version \([^ ]*\).*/\1/p')" = "${ZLIB_VERSION}" \
    && rm -rf /tmp/zlib.tar.gz /tmp/zlib-cve-2026-85091.patch "/tmp/zlib-${ZLIB_VERSION}"

WORKDIR /build

ARG GNOSIS_VERSION=0.17.5
ARG EXTRAS="embeddings"
COPY requirements.lock /build/requirements.lock
# gnosis-mcp is locked to its PyPI release, so the extras are resolved away and
# no longer appear in the requirement line. sqlite-vec is pulled in by the
# embeddings extra alone, so it stands in as the marker that the lock really was
# compiled with that extra.
RUN test "$EXTRAS" = "embeddings" \
    && grep -qE "^gnosis-mcp==${GNOSIS_VERSION}( |$)" /build/requirements.lock \
    && grep -qE "^sqlite-vec==" /build/requirements.lock \
    && pip install --require-hashes --prefix=/install -r /build/requirements.lock \
    && SITE_PACKAGES="$(find /install/lib -type d -name site-packages -print -quit)" \
    && test "$(PYTHONPATH="$SITE_PACKAGES" python -c 'import importlib.metadata; print(importlib.metadata.version("gnosis-mcp"))')" = "$GNOSIS_VERSION"

# The public 0.23.1/0.23.2 wheels remain affected by CVE-2026-85670.
# Build a visibly versioned downstream wheel from the checksum-pinned sdist.
# Rust/maturin and all source/build dependencies stay in the builder only.
ARG TOKENIZERS_SOURCE_SHA256=1feeeadf865a7915adc25445dea30e9933e593c31bb96c277cee36de227c8bfa
COPY patches/tokenizers/ /tmp/tokenizers-patches/
RUN curl -fsSL https://files.pythonhosted.org/packages/c1/60/21f715d9faba5f5407ff759472ade058ec4a507ad62bcea47cb847239a73/tokenizers-0.23.1.tar.gz -o /tmp/tokenizers.tar.gz \
    && echo "${TOKENIZERS_SOURCE_SHA256}  /tmp/tokenizers.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/tokenizers.tar.gz -C /tmp \
    && cd /tmp/tokenizers-0.23.1 \
    && patch -p1 < /tmp/tokenizers-patches/0001-bpe-reject-invalid-merges-CVE-2026-85670.patch \
    && python -c "from pathlib import Path; p=Path('bindings/python/Cargo.toml'); s=p.read_text(); assert s.count('version = \"0.23.1\"') == 1; p.write_text(s.replace('version = \"0.23.1\"', 'version = \"0.23.1+rcamarda1\"')); p=Path('bindings/python/Cargo.lock'); s=p.read_text(); old='name = \"tokenizers-python\"\\nversion = \"0.23.1\"'; assert s.count(old) == 1; p.write_text(s.replace(old, old.replace('0.23.1', '0.23.1+rcamarda1')))" \
    && pip install maturin==1.9.6 \
    && maturin build --release --locked --out /tmp/tokenizers-wheel --interpreter python \
    && SITE_PACKAGES="$(find /install/lib -type d -name site-packages -print -quit)" \
    && rm -rf "$SITE_PACKAGES/tokenizers" "$SITE_PACKAGES/tokenizers-0.23.1.dist-info" \
    && pip install --no-deps --prefix=/install /tmp/tokenizers-wheel/*.whl \
    && test "$(PYTHONPATH="$SITE_PACKAGES" python -c 'from importlib.metadata import version; print(version("tokenizers"))')" = '0.23.1+rcamarda1'

# Download exactly the files local_embed.py needs.
ARG EMBED_MODEL="MongoDB/mdbr-leaf-ir"
ENV XDG_DATA_HOME=/gnosis-model-cache

RUN set -e; \
    BASE="https://huggingface.co/${EMBED_MODEL}/resolve/main"; \
    DIR="/gnosis-model-cache/gnosis-mcp/models/MongoDB--mdbr-leaf-ir"; \
    mkdir -p "${DIR}/onnx"; \
    curl -fsSL "${BASE}/tokenizer.json"           -o "${DIR}/tokenizer.json"; \
    curl -fsSL "${BASE}/tokenizer_config.json"    -o "${DIR}/tokenizer_config.json"; \
    curl -fsSL "${BASE}/special_tokens_map.json"  -o "${DIR}/special_tokens_map.json"; \
    if curl -fsSL "${BASE}/onnx/model_quantized.onnx" -o "${DIR}/onnx/model_quantized.onnx"; then \
        echo "Downloaded model_quantized.onnx"; \
        curl -fsSL "${BASE}/onnx/model_quantized.onnx_data" -o "${DIR}/onnx/model_quantized.onnx_data" 2>/dev/null || echo "No onnx_data sidecar (ok)"; \
    else \
        curl -fsSL "${BASE}/onnx/model.onnx" -o "${DIR}/onnx/model.onnx"; \
        curl -fsSL "${BASE}/onnx/model.onnx_data" -o "${DIR}/onnx/model.onnx_data" 2>/dev/null || echo "No onnx_data sidecar (ok)"; \
        echo "Downloaded model.onnx (fallback)"; \
    fi; \
    echo "Model cache:"; \
    find /gnosis-model-cache -type f -ls

# ---------------------------------------------------------------------------
# Stage 2 — verified runtime root filesystem
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_SUITE} AS runtime_rootfs

ARG SQLITE_VERSION=3.53.4
ARG ZLIB_VERSION=1.3.2
ARG GLIBC_BACKPORT_VERSION
ARG DASH_BACKPORT_VERSION
COPY --from=builder /opt/sqlite/lib/libsqlite3.so* /usr/local/lib/
COPY --from=builder /opt/zlib/lib/libz.so* /usr/local/lib/
COPY --from=glibc_patched /out/ /tmp/glibc/

# Xray's fixed floor for CVE-2026-63072, CVE-2026-54874,
# CVE-2026-18798, CVE-2026-63076, CVE-2026-63075, CVE-2026-14457,
# CVE-2026-14456, CVE-2026-63074, CVE-2026-63073, and CVE-2026-75803.
# Keep this as a minimum rather than an exact pin so later Debian security
# revisions remain eligible. The build fails closed if the mirror is stale.
ARG OPENSSL_MIN_VERSION=3.5.7-1~deb13u2
ARG LIBPCRE2_MIN_VERSION=10.46-1~deb13u2
ARG GZIP_MIN_VERSION=1.13-1+deb13u1

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends /tmp/glibc/libc6_*_*.deb /tmp/glibc/libc-bin_*_*.deb /tmp/glibc/dash_*_*.deb \
    && apt-get install -y --no-install-recommends \
        libgomp1 \
        libssl3t64 \
        openssl \
        openssl-provider-legacy \
        libpcre2-8-0 \
        gzip \
    && for package in libssl3t64 openssl openssl-provider-legacy; do \
        installed_version="$(dpkg-query -W -f='${Version}' "$package")"; \
        echo "$package=$installed_version"; \
        dpkg --compare-versions "$installed_version" ge "$OPENSSL_MIN_VERSION" \
            || { echo "$package is below required version $OPENSSL_MIN_VERSION" >&2; exit 1; }; \
       done \
    && for package_and_floor in \
        "libpcre2-8-0:$LIBPCRE2_MIN_VERSION" \
        "gzip:$GZIP_MIN_VERSION"; do \
        package="${package_and_floor%%:*}"; \
        floor="${package_and_floor#*:}"; \
        installed_version="$(dpkg-query -W -f='${Version}' "$package")"; \
        echo "$package=$installed_version"; \
        dpkg --compare-versions "$installed_version" ge "$floor" \
            || { echo "$package is below required version $floor" >&2; exit 1; }; \
       done \
    && test "$(dpkg-query -W -f='${Version}' libc6)" = "${GLIBC_BACKPORT_VERSION}" \
    && test "$(dpkg-query -W -f='${Version}' libc-bin)" = "${GLIBC_BACKPORT_VERSION}" \
    && test "$(dpkg-query -W -f='${Version}' dash)" = "${DASH_BACKPORT_VERSION}" \
    && useradd --system --create-home --home-dir /home/gnosis --shell /bin/false gnosis \
    && rm -rf /tmp/glibc /var/lib/apt/lists/* \
    && ldconfig \
    && python -c "import zlib; assert zlib.ZLIB_RUNTIME_VERSION == '${ZLIB_VERSION}'"

COPY --from=builder /install             /usr/local
COPY --from=builder /gnosis-model-cache  /gnosis-model-cache
COPY verify-native-runtime.py /usr/local/share/gnosis/verify-native-runtime.py
COPY runtime-smoke.py /usr/local/share/gnosis/runtime-smoke.py

# Remove pip and its vendored vulnerable dependencies from the runtime.
# CVE-2026-23949, CVE-2025-47273 (setuptools); CVE-2026-57585 (msgpack)
# pip vendors its own dependency tree; pip's vendored pinned versions are:
#   setuptools==70.3.0
#   msgpack==1.1.2
# Bumping PIP_VERSION cannot fix these because the vendored pins travel with
# whatever pip release is installed; only removing pip removes the files.
# The ensurepip bundled wheel carries the same vendored tree, so it goes too.
# Nothing in this image invokes pip at runtime: gnosis-mcp has all deps from
# requirements.lock pre-installed, and there is no entrypoint that needs pip.
RUN rm -rf /usr/local/lib/python*/site-packages/pip \
           /usr/local/lib/python*/site-packages/pip-*.dist-info \
           /usr/local/lib/python*/ensurepip/_bundled \
           /usr/lib/python*/dist-packages/pip* \
           /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip* \
           /usr/bin/pip /usr/bin/pip3 /usr/bin/pip* \
           /root/.cache 2>/dev/null || true

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GNOSIS_MCP_HOST=0.0.0.0 \
    GNOSIS_MCP_PORT=8000 \
    GNOSIS_MCP_DATABASE_URL=sqlite:////data/docs.db \
    GNOSIS_MCP_EMBED_PROVIDER=local \
    GNOSIS_MCP_ACCESS_LOG=true \
    GNOSIS_MCP_WRITABLE=false \
    XDG_DATA_HOME=/gnosis-model-cache

RUN mkdir -p /data /docs \
    && chown -R gnosis:gnosis /data /home/gnosis /gnosis-model-cache

# Remove optional Python extensions first, then purge the native packages that
# only supported those extensions or image construction. The running service
# uses Python for compression, file operations, and UUID generation, so the
# corresponding command-line packages are not runtime requirements. dpkg's
# helper programs are purged in the final invocation; dpkg may exit 2 after
# successfully removing tar and diff, so every target is verified afterward.
# --no-triggers on that invocation stops dpkg from running debianutils'
# deferred update-shells trigger (queued by removing bash) after coreutils
# is gone: dirname/basename would otherwise be missing and the trigger's
# non-zero exit would fail the whole purge. The trigger only maintains
# /etc/shells, which this login-less final image does not use.
RUN rm -f \
        /usr/local/lib/python*/lib-dynload/_bz2*.so \
        /usr/local/lib/python*/lib-dynload/_curses*.so \
        /usr/local/lib/python*/lib-dynload/_uuid*.so \
        /usr/local/lib/python*/lib-dynload/readline*.so \
    && mkdir -p /usr/share/debconf \
    && printf '#!/bin/sh\nexit 0\n' > /usr/share/debconf/frontend \
    && chmod 0755 /usr/share/debconf/frontend \
    && dpkg --purge --force-depends --force-remove-essential --force-remove-protected \
        apt libapt-pkg7.0 \
        util-linux mount libmount1 libblkid1 libsmartcols1 libuuid1 \
        libudev1 libsystemd0 \
        ncurses-bin ncurses-base libncursesw6 readline-common libreadline8t64 \
        libpam-modules-bin libpam-modules libpam-runtime libpam0g libsqlite3-0 \
        liblastlog2-2 perl-base login login.defs passwd \
    && rm -rf /usr/share/debconf /var/cache/apt /var/lib/apt/lists \
    && purge_status=0 \
    && { dpkg --purge --no-triggers --force-depends --force-remove-essential --force-remove-protected \
            libacl1 libattr1 libbz2-1.0 libtinfo6 zlib1g libc-bin \
            bash bsdutils gzip sed coreutils diffutils tar \
            || purge_status="$?"; } \
    && { test "$purge_status" -eq 0 || test "$purge_status" -eq 2; } \
    && for package in \
        libacl1 libattr1 libbz2-1.0 libtinfo6 zlib1g libc-bin \
        bash bsdutils gzip sed coreutils diffutils tar; do \
        package_state="$(dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null || true)"; \
        test "$package_state" != "installed" \
            || { echo "$package is still installed after purge" >&2; exit 1; }; \
       done

USER gnosis
WORKDIR /home/gnosis

EXPOSE 8000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % __import__('os').environ['GNOSIS_MCP_PORT'])" || exit 1

# Verify that security removals and runtime functionality both succeeded.
RUN ! command -v pip \
    && ! python -c "import pip" 2>/dev/null \
    && test -z "$(find /usr/local /usr/lib -type f -path '*/pip/_vendor/*' -print -quit)" \
    && test -z "$(find /usr/local /usr/lib -type f -path '*/ensurepip/_bundled/*' -print -quit)" \
    && for package in \
        apt libapt-pkg7.0 bash bsdutils coreutils diffutils gzip sed tar \
        libacl1 libattr1 libbz2-1.0 libc-bin libmount1 libncursesw6 libsystemd0 \
        libudev1 libuuid1 liblastlog2-2 login.defs ncurses-base util-linux zlib1g \
        libpam0g libpam-modules libpam-modules-bin libpam-runtime libsqlite3-0 perl-base; do \
        package_state="$(dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null || true)"; \
        test "$package_state" != "installed" || { echo "$package is still installed" >&2; exit 1; }; \
       done \
    && python /usr/local/share/gnosis/verify-native-runtime.py \
    && test "$(dpkg-query -W -f='${Version}' libc6)" = "${GLIBC_BACKPORT_VERSION}" \
    && python -c "import sqlite3, sqlite_vec; assert sqlite3.sqlite_version == '${SQLITE_VERSION}'; db=sqlite3.connect(':memory:'); db.execute('create virtual table docs using fts5(body)'); db.execute(\"insert into docs values ('security fixed')\"); assert db.execute(\"select count(*) from docs where docs match 'fixed'\").fetchone()[0] == 1; db.enable_load_extension(True); db.load_extension(sqlite_vec.loadable_path()); db.execute('create virtual table vectors using vec0(embedding float[2])')" \
    && python -c "from importlib.metadata import version; from packaging.version import Version; assert Version(version('setuptools')) >= Version('80.10.0'); assert Version(version('msgpack')) >= Version('1.2.1'); assert Version('2.15.0') <= Version(version('PyJWT')) < Version('3'); assert Version('1.30.0') <= Version(version('mcp')) < Version('2')" \
    && python -c "import gnosis_mcp; print('Verification: gnosis-mcp OK')"

# Publish one root filesystem layer so Xray inspects the same minimized final
# state that runs in production. The dpkg database remains available for SBOM
# generation even though package-management commands are not supported.
FROM scratch AS runtime
COPY --from=runtime_rootfs / /

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GNOSIS_MCP_HOST=0.0.0.0 \
    GNOSIS_MCP_PORT=8000 \
    GNOSIS_MCP_DATABASE_URL=sqlite:////data/docs.db \
    GNOSIS_MCP_EMBED_PROVIDER=local \
    GNOSIS_MCP_ACCESS_LOG=true \
    GNOSIS_MCP_WRITABLE=false \
    XDG_DATA_HOME=/gnosis-model-cache

USER gnosis
WORKDIR /home/gnosis

EXPOSE 8000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % __import__('os').environ['GNOSIS_MCP_PORT'])" || exit 1

ARG GNOSIS_VERSION=0.17.5
ARG EMBED_MODEL="MongoDB/mdbr-leaf-ir"
# Supplied by the reusable workflow as the revision in the immutable image tag.
ARG GNOSIS_IMAGE_VERSION
LABEL org.opencontainers.image.title="gnosis-mcp" \
      org.opencontainers.image.description="Self-hosted MCP docs server — air-gap variant, ONNX model pre-bundled." \
      org.opencontainers.image.source="https://github.com/nicholasglazer/gnosis-mcp" \
      org.opencontainers.image.licenses="MIT" \
      gnosis.airgap="true" \
      gnosis.embed-model="${EMBED_MODEL}" \
      gnosis.gnosis-version="${GNOSIS_VERSION}" \
      gnosis.patch="upstream-rest-combined-lifespan" \
      gnosis.image-version="${GNOSIS_IMAGE_VERSION}"

ENTRYPOINT ["gnosis-mcp"]
CMD ["serve", "--transport", "streamable-http", "--rest"]
