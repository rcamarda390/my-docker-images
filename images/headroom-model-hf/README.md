# Headroom model cache image

Data-only Hugging Face cache for `headroom-ai==0.41.0`. The final image is
`FROM scratch`, targets `linux/amd64`, and has no executable, shell, entrypoint,
or command. The PR workflow builds and scans a candidate without publishing it
to GHCR on the main branch. PR builds remain unpublished and attach an
importable Docker archive and Xray support manifests to the workflow run.

The build downloads only the pinned Kompress ONNX model and the required
Kompress and ModernBERT tokenizer/configuration files. It also places the
OpenAI `cl100k_base` vocabulary in tiktoken's URL-hash cache layout, so it can
load offline when `TIKTOKEN_CACHE_DIR` points to `/opt/headroom-cache/tiktoken`.
`prepare.py` checks the model pins against the 0.41.0 wheel, records current
`main` revisions, repo license and gated status, and generates checksums, a
file manifest, a CycloneDX SBOM, and source/Xray notes. The manifest and SBOM
are included in the image. `verify.py` checks the image contents and actual
offline loading of the ONNX model, ModernBERT tokenizer, and cl100k tokenizer.

## Import and use

On a connected host, pull the published image:

```sh
docker pull docker.io/rcamarda390/headroom-model-hf:0.41.0-ext-v3
# GHCR mirror
docker pull ghcr.io/rcamarda390/headroom-model-hf:0.41.0-ext-v3
```

For an air-gapped host, download the `headroom-model-hf-0.41.0-ext-v3`
workflow artifact, extract it, verify the archive, and load it:

```sh
sha256sum -c image.tar.gz.sha256
gzip -dc image.tar.gz | docker load
```

Then copy the cache contents out of the image:

```sh
# This local tag is present after `docker load` or `docker pull`.
IMAGE=headroom-model-hf:0.41.0-ext-v3
cid=$(docker create --network none "$IMAGE" /nonexistent)
mkdir -p ./headroom-cache
docker cp "$cid:/opt/headroom-cache/." ./headroom-cache/
docker rm "$cid"
```

The image itself has no command to run. Copy `/opt/headroom-cache` into the
Headroom runtime image or configured cache volume. Set
`TIKTOKEN_CACHE_DIR=/opt/headroom-cache/tiktoken` in that runtime so tiktoken
uses the bundled vocabulary. Verify the assets with:

```sh
(cd ./headroom-cache && sha256sum -c SHA256SUMS)
```

The downloadable Docker archive is a transfer file generated from the image;
it is not stored inside the image.
