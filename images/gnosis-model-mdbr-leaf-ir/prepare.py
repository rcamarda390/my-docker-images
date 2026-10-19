"""Download only the approved model data; fail closed on upstream changes."""
import datetime
import hashlib
import json
import pathlib
import sys
import urllib.request

COMMIT = "4262131b32c3182bd06e67e92ae69d7bd66e0c5c"
SOURCE = "https://huggingface.co/MongoDB/mdbr-leaf-ir"
PREFIX = "gnosis-mcp/models/MongoDB--mdbr-leaf-ir/"
FILES = {
    "tokenizer.json": (711661, "da0e79933b9ed51798a3ae27893d3c5fa4a201126cef75586296df9b4d2c62a0"),
    "tokenizer_config.json": (1529, "46ac231e9b955a8af80fc7f23a0ecc65b524f1df84a02c2c82cbca354fb207b4"),
    "special_tokens_map.json": (732, "5aa43c2f985a25296d5a5ce621c2f77376ca8091a47993c492fd5460b895b140"),
    "onnx/model_quantized.onnx": (220597, "8c08cb4ecc00bad721b117a85738c537ceb9b85b3eedc52d9c6906fddaa55718"),
    "onnx/model_quantized.onnx_data": (22954752, "e77ea96a124230e23e5bac8e26c3ffe5410154973d8635673fa0220b06c13f8b"),
}
CARD_SHA256 = "c96977f87a734d0d784c6959b56d297f62a8bfda9bc35d0ec086081ad990a6e8"
LICENSE_URL = "https://www.apache.org/licenses/LICENSE-2.0.txt"
LICENSE_SHA256 = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def download(url, sha256, size=None):
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    if size is not None and len(data) != size:
        raise ValueError(f"{url}: expected {size} bytes, got {len(data)}")
    if digest(data) != sha256:
        raise ValueError(f"{url}: SHA256 mismatch: {digest(data)}")
    return data


def write(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_json(root, name, data):
    write(root, name, (json.dumps(data, indent=2) + "\n").encode())


def validate_sbom(sbom):
    from jsonschema import Draft7Validator
    from referencing import Registry, Resource

    schemas = {}
    for name, sha256 in {
        "bom-1.6.schema.json": "3e92dddbc30cf7f6a02b80f0942b1a4cfd4fb1c26f1dfc4310afa9d613cafb93",
        "spdx.schema.json": "baa9d3bd1ed57b6751b0887edead6b5063ff53ff7429cf85d476c6c94af0166e",
        "jsf-0.82.schema.json": "8bae002c25e723db7ee1f26afde680ae1a2b1a8f6b4b4b0fd65dc3becb090aae",
    }.items():
        url = f"https://raw.githubusercontent.com/CycloneDX/specification/1.6/schema/{name}"
        schemas[name] = json.loads(download(url, sha256))
    registry = Registry().with_resources([
        (f"http://cyclonedx.org/schema/{name}", Resource.from_contents(schema))
        for name, schema in schemas.items()
    ])
    Draft7Validator(schemas["bom-1.6.schema.json"], registry=registry).validate(sbom)


def prepare(root, version):
    root.mkdir(parents=True, exist_ok=False)
    records = []
    for name, (size, sha256) in FILES.items():
        url = f"{SOURCE}/resolve/{COMMIT}/{name}"
        destination = PREFIX + name
        write(root, destination, download(url, sha256, size))
        records.append({"path": destination, "source_url": url, "size_bytes": size, "sha256": sha256})
    card_url = f"{SOURCE}/resolve/{COMMIT}/README.md"
    card = download(card_url, CARD_SHA256)
    if b"license: apache-2.0" not in card:
        raise ValueError("Pinned model card no longer declares Apache-2.0")
    write(root, "MODEL_CARD.md", card)
    write(root, "LICENSE", download(LICENSE_URL, LICENSE_SHA256))
    for name, url in (("MODEL_CARD.md", card_url), ("LICENSE", LICENSE_URL)):
        data = (root / name).read_bytes()
        records.append({"path": name, "source_url": url, "size_bytes": len(data), "sha256": digest(data)})
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    write_json(root, "MANIFEST.json", {
        "source_url": SOURCE, "hf_commit": COMMIT, "version": version,
        "download_date": timestamp, "license": "Apache-2.0", "files": records,
        "license_provenance": "Upstream declares Apache-2.0 but has no LICENSE or NOTICE file. LICENSE is the unmodified official Apache text.",
        "model_card_provenance": "Unmodified upstream README.md, renamed MODEL_CARD.md.",
        "checksum_scope": "SHA256SUMS covers every file except itself. MANIFEST and SBOM describe upstream payload files to avoid circular hashes.",
    })
    write_json(root, "SBOM.json", {
        "bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
        "metadata": {"timestamp": timestamp, "component": {
            "type": "data", "name": "MongoDB/mdbr-leaf-ir", "version": COMMIT,
            "licenses": [{"license": {"id": "Apache-2.0"}}],
            "externalReferences": [{"type": "distribution", "url": f"{SOURCE}/tree/{COMMIT}"}],
        }},
        "components": [{
            "type": "data", "bom-ref": record["path"], "name": record["path"], "version": COMMIT,
            "hashes": [{"alg": "SHA-256", "content": record["sha256"]}],
            "licenses": [{"license": {"id": "Apache-2.0"}}],
            "properties": [{"name": "size_bytes", "value": str(record["size_bytes"])}],
        } for record in records],
    })
    validate_sbom(json.loads((root / "SBOM.json").read_text()))
    sums = "".join(f"{digest(p.read_bytes())}  {p.relative_to(root).as_posix()}\n"
                   for p in sorted(root.rglob("*")) if p.is_file())
    write(root, "SHA256SUMS", sums.encode())
    for path in [root, *root.rglob("*")]:
        path.chmod(0o755 if path.is_dir() else 0o644)


if __name__ == "__main__":
    prepare(pathlib.Path(sys.argv[1]), sys.argv[2])
