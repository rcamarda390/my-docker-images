FROM scratch
ARG MODEL_VERSION
ARG MODEL_REVISION
LABEL org.opencontainers.image.title="headroom-model-hf" \
      org.opencontainers.image.description="HF cache: Kompress ONNX + ModernBERT tokenizer for headroom-ai 0.41.0" \
      org.opencontainers.image.version="${MODEL_VERSION}-${MODEL_REVISION}" \
      headroom.kompress.repo="chopratejas/kompress-v2-base" \
      headroom.kompress.revision="b1563631b35bfdcee37587ad530147497d820d4c" \
      headroom.modernbert.repo="answerdotai/ModernBERT-base" \
      headroom.modernbert.revision="8949b909ec900327062f0ebf497f51aef5e6f0c8"
COPY huggingface /opt/headroom-cache/huggingface
COPY SHA256SUMS /opt/headroom-cache/SHA256SUMS
