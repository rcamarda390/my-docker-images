# Gnosis mdbr-leaf-ir model data

Data-only model cache for an independently installed internal PyPI Gnosis
consumer. This does not change the repository's existing Gnosis server image.

Final image: `FROM scratch`, one COPY layer, linux/amd64, no startup command,
shell, interpreter, package manager or executable. Files belong to 999:999;
files are 0644 and directories 0755. Python is builder-only.

The five requested files are pinned by Hugging Face commit, byte size and
SHA-256 in `prepare.py`. Mismatches fail the build. Model files are unchanged.
The upstream README is preserved byte-for-byte as MODEL_CARD.md.

Upstream declares Apache-2.0 but has no LICENSE or NOTICE at the pinned commit.
LICENSE contains the unmodified, SHA-256-pinned official Apache license text
from https://www.apache.org/licenses/LICENSE-2.0.txt. MANIFEST.json records
that provenance; it does not claim LICENSE was copied from Hugging Face.

SHA256SUMS covers all payload and metadata files except itself. MANIFEST.json
and the CycloneDX 1.6 SBOM describe the upstream payload files, avoiding circular
metadata hashes. The SBOM describes model artifacts as data components; it is
not proof that Artifactory/Xray ingested it or cleared the image.

The existing shared workflow performs candidate extraction/metadata/layer
checks before publication and scans with Trivy. The caller then pulls the
published Docker Hub image and repeats verification against its immutable
digest. Verification output is retained as a workflow artifact.

Tags start at `1.0.0-v1`. Serialized publications choose the next revision
from published Docker Hub tags; no latest tag is published. Download dates
record actual preparation time, so rebuilds can have different digests.

Extraction (container is created, never started):

```sh
docker pull rcamarda390/gnosis-model-mdbr-leaf-ir:1.0.0-v1
cid=$(docker create --network none rcamarda390/gnosis-model-mdbr-leaf-ir:1.0.0-v1 /unused-data-only)
docker cp "$cid:/gnosis-model-cache" ./gnosis-model-cache
docker rm "$cid"
cd gnosis-model-cache
sha256sum -c SHA256SUMS
```

The consumer cache starts at `gnosis-model-cache/gnosis-mcp/models/`.
No model inference is performed by this data image. Full integration and
Artifactory Xray validation happen in the internal consumer environment.
