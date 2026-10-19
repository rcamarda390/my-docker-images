"""Verify a built or freshly pulled data image without starting a container."""
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import tarfile
import tempfile

from prepare import CARD_SHA256, COMMIT, FILES, LICENSE_SHA256, PREFIX


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def verify_directory(root):
    expected = {PREFIX + name for name in FILES} | {
        "LICENSE", "MODEL_CARD.md", "MANIFEST.json", "SBOM.json", "SHA256SUMS"}
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    assert actual == expected, (actual, expected)
    for name, (size, sha256) in FILES.items():
        data = (root / PREFIX / name).read_bytes()
        assert len(data) == size, name
        assert hashlib.sha256(data).hexdigest() == sha256, name
    for name, sha256 in (("LICENSE", LICENSE_SHA256), ("MODEL_CARD.md", CARD_SHA256)):
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == sha256, name
    subprocess.run(["sha256sum", "-c", "SHA256SUMS"], cwd=root, check=True)
    sums = (root / "SHA256SUMS").read_text().splitlines()
    assert {line.split("  ", 1)[1] for line in sums} == expected - {"SHA256SUMS"}
    assert len(sums) == len(expected) - 1
    manifest = json.loads((root / "MANIFEST.json").read_text())
    assert manifest["hf_commit"] == COMMIT
    assert manifest["license"] == "Apache-2.0"
    assert {r["path"] for r in manifest["files"]} == expected - {"MANIFEST.json", "SBOM.json", "SHA256SUMS"}
    for record in manifest["files"]:
        data = (root / record["path"]).read_bytes()
        assert len(data) == record["size_bytes"]
        assert hashlib.sha256(data).hexdigest() == record["sha256"]
    sbom = json.loads((root / "SBOM.json").read_text())
    assert sbom["bomFormat"] == "CycloneDX" and sbom["specVersion"] == "1.6"
    assert {c["name"] for c in sbom["components"]} == {r["path"] for r in manifest["files"]}
    for component in sbom["components"]:
        assert component["type"] == "data"
        assert component["hashes"] == [{"alg": "SHA-256", "content": hashlib.sha256((root / component["name"]).read_bytes()).hexdigest()}]
    return expected


def verify_image(image):
    inspect = json.loads(run("docker", "image", "inspect", image))[0]
    assert inspect["Os"] == "linux" and inspect["Architecture"] == "amd64"
    config = inspect["Config"]
    assert not config.get("Entrypoint") and not config.get("Cmd")
    assert config["Labels"]["gnosis.data-only"] == "true"
    assert config["Labels"]["org.opencontainers.image.revision"] == COMMIT
    assert config["Labels"]["org.opencontainers.image.licenses"] == "Apache-2.0"
    assert len(inspect["RootFS"]["Layers"]) == 1
    with tempfile.TemporaryDirectory() as directory:
        work = pathlib.Path(directory)
        # Docker requires a command for create. This nonexistent path is never executed.
        cid = run("docker", "create", "--network", "none", image, "/unused-data-only")
        try:
            subprocess.run(["docker", "cp", f"{cid}:/gnosis-model-cache", str(work / "cache")], check=True)
        finally:
            subprocess.run(["docker", "rm", cid], check=True)
        expected = verify_directory(work / "cache")
        manifest = json.loads((work / "cache/MANIFEST.json").read_text())
        assert config["Labels"]["org.opencontainers.image.version"] == manifest["version"]
        archive = work / "image.tar"
        subprocess.run(["docker", "image", "save", "-o", str(archive), image], check=True)
        with tarfile.open(archive) as saved:
            docker_manifest = json.load(saved.extractfile("manifest.json"))
            layers = docker_manifest[0]["Layers"]
            assert len(layers) == 1
            with tarfile.open(fileobj=io.BytesIO(saved.extractfile(layers[0]).read()), mode="r:*") as layer:
                members = layer.getmembers()
                actual = set()
                for member in members:
                    name = member.name.removeprefix("./").rstrip("/")
                    assert name == "gnosis-model-cache" or name.startswith("gnosis-model-cache/"), name
                    assert member.isdir() or member.isfile(), name
                    assert (member.uid, member.gid) == (999, 999), (name, member.uid, member.gid)
                    assert member.mode == (0o755 if member.isdir() else 0o644), (name, oct(member.mode))
                    if member.isfile():
                        actual.add(name.removeprefix("gnosis-model-cache/"))
                assert actual == expected
        print(json.dumps({"image": image, "repo_digests": inspect.get("RepoDigests"), "manifest": manifest}, indent=2))


if __name__ == "__main__":
    verify_image(sys.argv[1])
