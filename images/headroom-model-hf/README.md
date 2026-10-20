# Headroom model cache image

Data-only Hugging Face cache for `headroom-ai==0.41.0`. The final image is
`FROM scratch`, targets `linux/amd64`, and has no executable, shell, entrypoint,
or command. The PR workflow builds and scans a candidate without publishing it
to a registry, then attaches an importable Docker archive and Xray support
manifests to the workflow run.

The build downloads only the pinned Kompress ONNX model and the required
Kompress and ModernBERT tokenizer/configuration files. `prepare.py` checks the
pins against the 0.41.0 wheel, records current `main` revisions, repo license
and gated status, and generates the standard Hugging Face cache layout and
checksums. `verify.py` checks the image contents, offline loading, metadata,
and Docker archive.

## Import and use

Download the `headroom-model-hf-0.41.0-ext-v1` artifact from the successful
GitHub Actions run, extract the artifact ZIP, then load the image archive:

```sh
gunzip -c image.tar.gz | docker load
cid=$(docker create --network none headroom-model-hf:0.41.0-ext-v1 /nonexistent)
mkdir -p ./headroom-cache
docker cp "$cid:/opt/headroom-cache/." ./headroom-cache/
docker rm "$cid"
```

The image itself has no command to run. Copy `/opt/headroom-cache` into the
Headroom runtime's configured cache mount or volume. Verify it with:

```sh
(cd ./headroom-cache && sha256sum -c SHA256SUMS)
```

The downloadable Docker archive is a transfer file generated from the image;
it is not stored inside the image.
