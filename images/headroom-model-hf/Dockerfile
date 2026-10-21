FROM scratch
ARG MODEL_VERSION
ARG MODEL_REVISION
LABEL org.opencontainers.image.title="headroom-model-hf" \
      org.opencontainers.image.description="Offline Headroom 0.41.0 model, tokenizer, tiktoken cache, and Xray SBOM payload" \
      org.opencontainers.image.version="${MODEL_VERSION}-${MODEL_REVISION}" \
      headroom.kompress.repo="chopratejas/kompress-v2-base" \
      headroom.kompress.revision="b1563631b35bfdcee37587ad530147497d820d4c" \
      headroom.modernbert.repo="answerdotai/ModernBERT-base" \
      headroom.modernbert.revision="8949b909ec900327062f0ebf497f51aef5e6f0c8" \
      headroom.tiktoken.url="https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken" \
      headroom.tiktoken.sha256="223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7" \
      headroom.tiktoken.cache-dir="/opt/headroom-cache/tiktoken"
COPY huggingface /opt/headroom-cache/huggingface
COPY tiktoken /opt/headroom-cache/tiktoken
COPY SHA256SUMS manifest.json sbom.cdx.json sources.md XRAY-NOTES.md /opt/headroom-cache/
