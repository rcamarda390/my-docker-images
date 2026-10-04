# syntax=docker/dockerfile:1.7

ARG III_VERSION=0.11.2
ARG DEBIAN_SUITE=trixie
ARG GLIBC_DEBIAN_VERSION=2.41-12+deb13u4
ARG GLIBC_BACKPORT_VERSION=2.41-12+deb13u4+rcamarda3

FROM iiidev/iii:${III_VERSION} AS iii-image

FROM debian:${DEBIAN_SUITE}-slim AS glibc_patched
ARG DEBIAN_SUITE
ARG GLIBC_DEBIAN_VERSION
ARG GLIBC_BACKPORT_VERSION
COPY patches/glibc/ /tmp/glibc-patches/
COPY verify-glibc-normalize.c /tmp/verify-glibc-normalize.c
RUN set -eux; \
    sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/debian.sources; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl devscripts dpkg-dev git quilt; \
    apt-get build-dep -y --no-install-recommends "glibc=${GLIBC_DEBIAN_VERSION}"; \
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
      "Backport the repository-tested resolver, stdio and secure-loader fixes for AgentMemory."; \
    DEB_BUILD_OPTIONS="nocheck" dpkg-buildpackage -B -uc -us -j"$(nproc)"; \
    cp ../libc6_*_*.deb ../libc-bin_*_*.deb /out/; \
    dpkg-deb -f /out/libc6_*_*.deb Version | grep -Fx "${GLIBC_BACKPORT_VERSION}"; \
    dpkg-deb -f /out/libc-bin_*_*.deb Version | grep -Fx "${GLIBC_BACKPORT_VERSION}"

# Rebuild the exact Trixie package families reported by Xray and Trivy from
# fixed upstream sources. This keeps the Trixie ABI while moving ACL, attr,
# ncurses, and util-linux beyond their vulnerable releases.
FROM debian:${DEBIAN_SUITE}-slim AS native_patched
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git dpkg-dev build-essential zlib1g-dev
WORKDIR /build
COPY prepare-native-sources.sh /tmp/prepare-native-sources.sh
COPY verify-native-runtime.c /tmp/verify-native-runtime.c
RUN sh /tmp/prepare-native-sources.sh \
 && mkdir /out \
 && for package in attr acl ncurses util-linux zlib; do \
      apt-get build-dep -y --no-install-recommends "./$package" || exit 1; \
      if [ "$package" = acl ]; then \
        (cd "$package" && DEB_BUILD_OPTIONS=nocheck dpkg-buildpackage -b -uc -us -j"$(nproc)") || exit 1; \
      else \
        (cd "$package" && dpkg-buildpackage -b -uc -us -j"$(nproc)") || exit 1; \
      fi; \
    done \
 && cp ./*.deb /out/ \
 && gcc -Wall -Wextra -Werror -O2 /tmp/verify-native-runtime.c -o /out/verify-native-runtime -lz -lresolv

# PCRE2 10.49 fixes CVE-2026-103111 and retains the prior 10.48 fixes.
# Build the checksum-pinned upstream release and retain only the
# ABI-compatible 8-bit shared library needed by libselinux/coreutils.
FROM debian:${DEBIAN_SUITE}-slim AS pcre2_patched
ARG PCRE2_VERSION=10.49
ARG PCRE2_SHA256=929f0b20e62879252a15886b06c89f1edef61a363cbd5826fb041080a5e557ae
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends build-essential ca-certificates curl; \
    curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
      "https://github.com/PCRE2Project/pcre2/releases/download/pcre2-${PCRE2_VERSION}/pcre2-${PCRE2_VERSION}.tar.gz" \
      --output /tmp/pcre2.tar.gz; \
    echo "${PCRE2_SHA256}  /tmp/pcre2.tar.gz" | sha256sum --check --status; \
    tar -xzf /tmp/pcre2.tar.gz -C /tmp; \
    cd "/tmp/pcre2-${PCRE2_VERSION}"; \
    ./configure --prefix=/opt/pcre2 --disable-static --enable-shared \
      --disable-pcre2-16 --disable-pcre2-32 --disable-jit; \
    make -j"$(nproc)"; \
    make check; \
    make install; \
    /opt/pcre2/bin/pcre2grep -V | grep -F "version ${PCRE2_VERSION}"

FROM node:26-slim AS runtime_rootfs

ARG AGENTMEMORY_VERSION=0.9.29
ARG AGENTMEMORY_IMAGE_VERSION=v1
ARG III_VERSION=0.11.2
ARG III_SDK_VERSION=0.11.2
ARG GLIBC_BACKPORT_VERSION
ARG TRANSFORMERS_VERSION=4.2.0
ARG TRANSFORMERS_MODEL_REVISION=751bff37182d3f1213fa05d7196b954e230abad9
ARG TRANSFORMERS_MODEL_ID=Xenova/all-MiniLM-L6-v2

LABEL org.opencontainers.image.title="agentmemory" \
      org.opencontainers.image.version="${AGENTMEMORY_VERSION}-${AGENTMEMORY_IMAGE_VERSION}" \
      org.opencontainers.image.description="Combined AgentMemory and iii runtime with offline local embeddings" \
      agentmemory.version="${AGENTMEMORY_VERSION}" \
      agentmemory.iii-version="${III_VERSION}" \
      agentmemory.embedding-provider="local" \
      agentmemory.embedding-model="${TRANSFORMERS_MODEL_ID}" \
      agentmemory.embedding-dimensions="384" \
      agentmemory.transformers-version="${TRANSFORMERS_VERSION}" \
      agentmemory.model-revision="${TRANSFORMERS_MODEL_REVISION}"

# The AgentMemory runtime uses sh, node, openssl, gosu, and coreutils; it
# never invokes Perl. Debian Trixie currently ships perl-base 5.40.1-6 with
# the Xray-reported CVEs and no Trixie fix version. Remove the unused package
# after all apt work, then fail the build if it remains installed.
COPY --from=native_patched /out/ /tmp/native/
COPY --from=glibc_patched /out/ /tmp/glibc/
RUN apt-get update \
 && apt-get install -y --no-install-recommends openssl ca-certificates tini gosu curl \
 && apt-get upgrade -y --no-install-recommends \
 && set -- \
 && for archive in /tmp/native/*.deb; do \
      package="$(dpkg-deb -f "$archive" Package)"; \
      state="$(dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null || true)"; \
      if [ "$state" = installed ]; then set -- "$@" "$archive"; fi; \
    done \
 && test "$#" -gt 0 \
 && apt-get install -y --no-install-recommends "$@" \
 && apt-get install -y --no-install-recommends /tmp/glibc/*.deb \
 && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' zlib1g)" ge "1:1.3.dfsg+really1.3.2-3+rcamarda1" \
 && for package in openssl libssl3t64 openssl-provider-legacy; do \
      dpkg --compare-versions "$(dpkg-query -W -f='${Version}' "$package")" ge "3.5.7-1~deb13u3" || exit 1; \
    done \
 && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' libacl1)" ge "2.4.0-1+rcamarda1" \
 && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' libattr1)" ge "1:2.6.0-1+rcamarda1" \
 && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' libtinfo6)" ge "6.6+20260608-2+rcamarda1" \
 && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' libuuid1)" ge "2.41.6-0+rcamarda3" \
 && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' libc6)" ge "${GLIBC_BACKPORT_VERSION}" \
 && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' libc-bin)" ge "${GLIBC_BACKPORT_VERSION}" \
 && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' libsqlite3-0)" ge "3.46.1-7+deb13u2" \
 && apt-get purge -y --auto-remove --allow-remove-essential perl-base perl-modules-5.40 \
 && test "$(dpkg-query -W -f='${Status}' perl-base 2>/dev/null || true)" != "install ok installed" \
 && ! command -v perl \
 && install -m 0755 /tmp/native/verify-native-runtime /usr/local/bin/verify-native-runtime \
 && /usr/local/bin/verify-native-runtime \
 && rm -rf /tmp/native /tmp/glibc /var/lib/apt/lists/*

COPY --from=iii-image /app/iii /usr/local/bin/iii

# Match the upstream AgentMemory deployment: install into a local prefix so
# npm overrides can pin iii-sdk to the same version as the bundled iii engine.
# The Xray v3 scan found these transitive npm versions:
# brace-expansion 5.0.7, sharp 0.34.5, tar 7.5.19, ip-address 10.2.0,
# adm-zip 0.5.18, undici 6.27.0, and OpenTelemetry 1.30.1. The OpenTelemetry
# fix is a coordinated 2.x migration; iii-sdk 0.11.2 needs its Resource API
# call patched after the dependency graph is upgraded.
WORKDIR /opt/agentmemory
COPY --chmod=0755 patch-iii-otel2.mjs /tmp/patch-iii-otel2.mjs
RUN printf '{"name":"agentmemory-deploy","version":"1.0.0","private":true,"overrides":{"iii-sdk":"%s","adm-zip":"0.6.1","proxy-addr":"2.0.8","@modelcontextprotocol/sdk":"1.31.0","hono":"4.13.11","@hono/node-server":"2.1.3","fast-uri":"3.1.8","brace-expansion":"5.0.9","ip-address":"10.7.1","sharp":"0.35.5","tar":"7.5.21","undici":"6.28.0","@opentelemetry/api-logs":"0.200.0","@opentelemetry/core":"2.9.0","@opentelemetry/context-async-hooks":"2.9.0","@opentelemetry/instrumentation":"0.200.0","@opentelemetry/otlp-transformer":"0.200.0","@opentelemetry/propagator-b3":"2.9.0","@opentelemetry/propagator-jaeger":"2.9.0","@opentelemetry/resources":"2.9.0","@opentelemetry/sdk-logs":"0.200.0","@opentelemetry/sdk-metrics":"2.9.0","@opentelemetry/sdk-trace-base":"2.9.0","@opentelemetry/sdk-trace-node":"2.9.0"}}\n' "${III_SDK_VERSION}" > package.json \
 && npm install "@agentmemory/agentmemory@${AGENTMEMORY_VERSION}" "@huggingface/transformers@${TRANSFORMERS_VERSION}" --include=optional --no-fund --no-audit \
 && test "$(node -p "require('./node_modules/@huggingface/transformers/package.json').version")" = "${TRANSFORMERS_VERSION}" \
 && node /tmp/patch-iii-otel2.mjs \
 && node --input-type=module -e "await import('iii-sdk'); console.log('iii-sdk OpenTelemetry compatibility smoke OK')" \
 && rm /tmp/patch-iii-otel2.mjs \
 && ln -s /opt/agentmemory/node_modules/.bin/agentmemory /usr/local/bin/agentmemory

# npm, npx, and corepack are build-time tools only. They bring their own
# bundled dependency tree into the runtime image (including the Xray-reported
# brace-expansion, ip-address, and tar versions), while AgentMemory runs
# directly under node and never invokes a package manager.
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack /root/.npm \
 && rm -f /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack \
 && ! command -v npm \
 && ! command -v npx \
 && ! command -v corepack

ENV AGENTMEMORY_III_VERSION=${III_VERSION} \
    EMBEDDING_PROVIDER=local \
    AGENTMEMORY_AUTO_COMPRESS=false \
    AGENTMEMORY_INJECT_CONTEXT=false \
    GRAPH_EXTRACTION_ENABLED=false \
    CONSOLIDATION_ENABLED=false \
    TRANSFORMERS_MODEL_PATH=/opt/agentmemory/models \
    TRANSFORMERS_CACHE_DIR=/opt/agentmemory/transformers-cache \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1 \
    NODE_OPTIONS=--import=/opt/agentmemory/transformers-offline.mjs \
    TINI_SUBREAPER=1

RUN set -eux; \
    model_dir="/opt/agentmemory/models/${TRANSFORMERS_MODEL_ID}"; \
    mkdir -p "${model_dir}/onnx" /opt/agentmemory/transformers-cache; \
    curl --proto '=https' --tlsv1.2 --fail --location --retry 3 --retry-all-errors \
      "https://huggingface.co/${TRANSFORMERS_MODEL_ID}/resolve/${TRANSFORMERS_MODEL_REVISION}/config.json" \
      -o "${model_dir}/config.json"; \
    curl --proto '=https' --tlsv1.2 --fail --location --retry 3 --retry-all-errors \
      "https://huggingface.co/${TRANSFORMERS_MODEL_ID}/resolve/${TRANSFORMERS_MODEL_REVISION}/tokenizer.json" \
      -o "${model_dir}/tokenizer.json"; \
    curl --proto '=https' --tlsv1.2 --fail --location --retry 3 --retry-all-errors \
      "https://huggingface.co/${TRANSFORMERS_MODEL_ID}/resolve/${TRANSFORMERS_MODEL_REVISION}/tokenizer_config.json" \
      -o "${model_dir}/tokenizer_config.json"; \
    curl --proto '=https' --tlsv1.2 --fail --location --retry 3 --retry-all-errors \
      "https://huggingface.co/${TRANSFORMERS_MODEL_ID}/resolve/${TRANSFORMERS_MODEL_REVISION}/special_tokens_map.json" \
      -o "${model_dir}/special_tokens_map.json"; \
    curl --proto '=https' --tlsv1.2 --fail --location --retry 3 --retry-all-errors \
      "https://huggingface.co/${TRANSFORMERS_MODEL_ID}/resolve/${TRANSFORMERS_MODEL_REVISION}/vocab.txt" \
      -o "${model_dir}/vocab.txt"; \
    curl --proto '=https' --tlsv1.2 --fail --location --retry 3 --retry-all-errors \
      "https://huggingface.co/${TRANSFORMERS_MODEL_ID}/resolve/${TRANSFORMERS_MODEL_REVISION}/onnx/model_quantized.onnx" \
      -o "${model_dir}/onnx/model_quantized.onnx"; \
    printf '%s  %s\n' \
      '7135149f7cffa1a573466c6e4d8423ed73b62fd2332c575bf738a0d033f70df7' "${model_dir}/config.json" \
      'da0e79933b9ed51798a3ae27893d3c5fa4a201126cef75586296df9b4d2c62a0' "${model_dir}/tokenizer.json" \
      '9261e7d79b44c8195c1cada2b453e55b00aeb81e907a6664974b4d7776172ab3' "${model_dir}/tokenizer_config.json" \
      'b6d346be366a7d1d48332dbc9fdf3bf8960b5d879522b7799ddba59e76237ee3' "${model_dir}/special_tokens_map.json" \
      '07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3' "${model_dir}/vocab.txt" \
      'afdb6f1a0e45b715d0bb9b11772f032c399babd23bfc31fed1c170afc848bdb1' "${model_dir}/onnx/model_quantized.onnx" \
      | sha256sum -c -; \
    test -s "${model_dir}/config.json"; \
    test -s "${model_dir}/tokenizer.json"; \
    test -s "${model_dir}/tokenizer_config.json"; \
    test -s "${model_dir}/onnx/model_quantized.onnx"; \
    chmod -R a-w /opt/agentmemory/models /opt/agentmemory/transformers-cache

# curl is needed only while the connected GitHub build downloads the pinned
# model. It is not used by AgentMemory at runtime; remove it and its unused
# libraries from the final image.
RUN apt-get purge -y --auto-remove curl \
 && ! command -v curl \
 && rm -rf /var/lib/apt/lists/*

COPY --chmod=0644 transformers-offline.mjs /opt/agentmemory/transformers-offline.mjs
COPY --chmod=0755 offline-embedding-smoke.mjs /opt/agentmemory/offline-embedding-smoke.mjs
COPY --chmod=0644 prune-onnx-installer.mjs /tmp/prune-onnx-installer.mjs

# ONNX's installer proxy/logger is build-only. Remove it after npm and native
# installation, with installed reverse-dependency guards and a native import.
RUN node /tmp/prune-onnx-installer.mjs && rm /tmp/prune-onnx-installer.mjs

# This is deliberately a network-disabled build step. It proves the staged
# model is sufficient before the image can be published.
RUN --network=none node /opt/agentmemory/offline-embedding-smoke.mjs

COPY --chmod=0755 entrypoint.sh /usr/local/bin/agentmemory-entrypoint.sh
COPY --chmod=0755 runtime-smoke.mjs /opt/agentmemory/runtime-smoke.mjs
COPY --chmod=0755 strip-runtime-packages.sh /usr/local/lib/strip-runtime-packages.sh

# Replace PCRE2 with the upstream fixed ABI. Runtime package removal happens
# in a copied root below so the intact build root remains available to prove
# and perform the package-manager-stack removal transaction.
# systemd-homed is not installed or used; libsystemd/libudev are source-package
# siblings that Xray and Trivy still attribute to CVE-2026-16742. zlib1g stays:
# OpenSSL dynamically requires libz.so.1 for runtime secret generation.
COPY --from=pcre2_patched /opt/pcre2/lib/ /usr/local/lib/
COPY --from=pcre2_patched /opt/pcre2/bin/pcre2grep /usr/local/bin/pcre2grep
RUN set -eux; \
    ldconfig; \
    /usr/local/bin/pcre2grep -V | grep -F "pcre2grep version 10.49"; \
    for binary in /bin/sh /usr/bin/openssl /usr/bin/tini /usr/sbin/gosu \
                  /usr/local/bin/node /usr/local/bin/iii /usr/bin/chown \
                  /usr/bin/chmod /usr/bin/mkdir; do \
      test -x "$binary"; \
      ! ldd "$binary" 2>&1 | grep -q 'not found'; \
    done; \
    openssl rand -hex 32 | grep -Eq '^[0-9a-f]{64}$'; \
    gosu node:node node -e "require('node:zlib').gzipSync('runtime dependency check'); console.log('node runtime OK')"; \
    node --input-type=module -e "await import('iii-sdk'); console.log('iii-sdk runtime OK')"

# Build a disposable runtime root, remove the whole package-manager stack
# rather than breaking dpkg by force-removing tar alone, and validate that root
# before it becomes the final image. The source root remains a reversible build
# environment; only /runtime-root is copied into the scratch stage.
RUN set -eux; \
    mkdir /runtime-root; \
    for path in bin etc home lib lib64 opt sbin usr var; do \
      if [ -e "/$path" ]; then cp -a "/$path" /runtime-root/; fi; \
    done; \
    install -d -m 0755 /runtime-root/data /runtime-root/dev /runtime-root/run; \
    install -d -m 1777 /runtime-root/tmp; \
    # dpkg --root runs maintainer scripts inside the copied root. Give those \
    # scripts a temporary null sink; Docker supplies the real /dev at runtime. \
    : > /runtime-root/dev/null; \
    chmod 0666 /runtime-root/dev/null; \
    /usr/local/lib/strip-runtime-packages.sh /runtime-root; \
    rm -f /runtime-root/dev/null; \
    rmdir /runtime-root/dev

FROM scratch AS runtime
COPY --from=runtime_rootfs /runtime-root/ /

ARG AGENTMEMORY_VERSION=0.9.29
ARG AGENTMEMORY_IMAGE_VERSION=v1
ARG III_VERSION=0.11.2
ARG TRANSFORMERS_VERSION=4.2.0
ARG TRANSFORMERS_MODEL_REVISION=751bff37182d3f1213fa05d7196b954e230abad9
ARG TRANSFORMERS_MODEL_ID=Xenova/all-MiniLM-L6-v2

LABEL org.opencontainers.image.title="agentmemory" \
      org.opencontainers.image.version="${AGENTMEMORY_VERSION}-${AGENTMEMORY_IMAGE_VERSION}" \
      org.opencontainers.image.description="Combined AgentMemory and iii runtime with offline local embeddings" \
      agentmemory.version="${AGENTMEMORY_VERSION}" \
      agentmemory.iii-version="${III_VERSION}" \
      agentmemory.embedding-provider="local" \
      agentmemory.embedding-model="${TRANSFORMERS_MODEL_ID}" \
      agentmemory.embedding-dimensions="384" \
      agentmemory.transformers-version="${TRANSFORMERS_VERSION}" \
      agentmemory.model-revision="${TRANSFORMERS_MODEL_REVISION}"

ENV AGENTMEMORY_III_VERSION=${III_VERSION} \
    EMBEDDING_PROVIDER=local \
    AGENTMEMORY_AUTO_COMPRESS=false \
    AGENTMEMORY_INJECT_CONTEXT=false \
    GRAPH_EXTRACTION_ENABLED=false \
    CONSOLIDATION_ENABLED=false \
    TRANSFORMERS_MODEL_PATH=/opt/agentmemory/models \
    TRANSFORMERS_CACHE_DIR=/opt/agentmemory/transformers-cache \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1 \
    NODE_OPTIONS=--import=/opt/agentmemory/transformers-offline.mjs \
    TINI_SUBREAPER=1

WORKDIR /opt/agentmemory
EXPOSE 3111
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/agentmemory-entrypoint.sh"]
