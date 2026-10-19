# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS prepare
ARG MODEL_VERSION
ARG MODEL_REVISION
COPY prepare.py /prepare.py
RUN pip install --no-cache-dir jsonschema==4.23.0 \
    && python /prepare.py /gnosis-model-cache "${MODEL_VERSION}-${MODEL_REVISION}"

FROM scratch
ARG MODEL_VERSION
ARG MODEL_REVISION
LABEL org.opencontainers.image.title="gnosis-model-mdbr-leaf-ir" \
      org.opencontainers.image.source="https://huggingface.co/MongoDB/mdbr-leaf-ir" \
      org.opencontainers.image.version="${MODEL_VERSION}-${MODEL_REVISION}" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.revision="4262131b32c3182bd06e67e92ae69d7bd66e0c5c" \
      gnosis.data-only="true" \
      gnosis.payload.path="/gnosis-model-cache"
COPY --from=prepare --chown=999:999 /gnosis-model-cache /gnosis-model-cache
