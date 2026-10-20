"""Prepare pinned Hugging Face cache files and Xray metadata before image build."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

from huggingface_hub import HfApi, __version__ as HF_HUB_VERSION, snapshot_download


ROOT = pathlib.Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
TAG = "0.41.0-ext-v1"
ARTIFACTS = REPO_ROOT / f"headroom-model-hf-{TAG}-manifests"
LICENSE = "Apache-2.0"
LICENSE_URL = "https://www.apache.org/licenses/LICENSE-2.0.txt"
MODELS = {
    "chopratejas/kompress-v2-base": {
        "revision": "b1563631b35bfdcee37587ad530147497d820d4c",
        "files": [
            "config.json",
            "special_tokens_map.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "onnx/kompress-int8-wo.onnx",
        ],
        "primary_file": "onnx/kompress-int8-wo.onnx",
    },
    "answerdotai/ModernBERT-base": {
        "revision": "8949b909ec900327062f0ebf497f51aef5e6f0c8",
        "files": [
            "config.json",
            "special_tokens_map.json",
            "tokenizer.json",
            "tokenizer_config.json",
        ],
        "primary_file": "tokenizer.json",
    },
}
FORBIDDEN_SUFFIXES = (".bin", ".pt", ".pth", ".pkl", ".ckpt", ".pickle")


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_wheel_pins() -> dict[str, tuple[int, str]]:
    with tempfile.TemporaryDirectory(prefix="headroom-wheel-") as temp:
        subprocess.run(
            [sys.executable, "-m", "pip", "download", "--no-deps", "headroom-ai==0.41.0", "-d", temp],
            check=True,
        )
        wheels = list(pathlib.Path(temp).glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"Expected one headroom-ai 0.41.0 wheel; found {len(wheels)}")
        with zipfile.ZipFile(wheels[0]) as wheel:
            source = wheel.read("headroom/onnx_runtime.py").decode("utf-8")
    lines = source.splitlines()
    evidence = {}
    for repo, info in MODELS.items():
        matches = [
            (number, line)
            for number, line in enumerate(lines, start=1)
            if re.search(rf'"{re.escape(repo)}"\s*:\s*"([0-9a-f]{{40}})"', line)
        ]
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly one wheel pin for {repo}; found {len(matches)}")
        number, line = matches[0]
        if info["revision"] not in line:
            raise RuntimeError(f"Wheel pin mismatch for {repo}: {number}: {line}")
        evidence[repo] = (number, line)
    return evidence


def remove_extra_cache_metadata(hub: pathlib.Path) -> None:
    for path in list(hub.rglob(".locks")) + list(hub.rglob(".no_exist")) + list(hub.rglob("trees")):
        shutil.rmtree(path)
    for path in hub.rglob("CACHEDIR.TAG"):
        path.unlink()


def prepare_verification_venv() -> tuple[str, str]:
    """Install test packages online into a Python 3.12 venv for later offline use."""
    image = "python:3.12-slim"
    venv = pathlib.Path(tempfile.gettempdir()) / "headroom-model-verifier-0.41.0-ext-v1"
    if venv.exists():
        shutil.rmtree(venv)
    venv.mkdir(parents=True)
    subprocess.run(["docker", "pull", image], check=True)
    subprocess.run(
        ["docker", "run", "--rm", "-v", f"{venv}:/venv", image, "python", "-m", "venv", "/venv"],
        check=True,
    )
    subprocess.run(
        [
            "docker", "run", "--rm", "-v", f"{venv}:/venv", image, "/venv/bin/pip", "install",
            "--disable-pip-version-check", "onnxruntime==1.31.0", "tokenizers==0.23.3",
            "headroom-ai[proxy]==0.41.0",
        ],
        check=True,
    )
    versions = subprocess.check_output(
        [
            "docker", "run", "--rm", "-v", f"{venv}:/venv", image, "/venv/bin/python", "-c",
            "import importlib.metadata as m; print('onnxruntime='+m.version('onnxruntime')); "
            "print('tokenizers='+m.version('tokenizers')); print('headroom-ai='+m.version('headroom-ai'))",
        ],
        text=True,
    ).strip()
    return str(venv), versions


def main() -> None:
    evidence = check_wheel_pins()
    download_date = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    hub = ROOT / "huggingface" / "hub"
    if hub.exists():
        shutil.rmtree(hub)
    hub.mkdir(parents=True)
    if ARTIFACTS.exists():
        shutil.rmtree(ARTIFACTS)
    ARTIFACTS.mkdir(parents=True)

    api = HfApi()
    source_records = {}
    inventory = []
    for repo, info in MODELS.items():
        owner, _ = repo.split("/", 1)
        pinned = api.model_info(repo_id=repo, revision=info["revision"], files_metadata=True)
        main = api.model_info(repo_id=repo, revision="main", files_metadata=False)
        if pinned.id.lower() != repo.lower() or main.id.lower() != repo.lower():
            raise RuntimeError(f"Hugging Face repo owner/name mismatch for {repo}")
        if not re.fullmatch(r"[0-9a-f]{40}", pinned.sha) or not re.fullmatch(r"[0-9a-f]{40}", main.sha):
            raise RuntimeError(f"Unexpected Hugging Face commit SHA for {repo}")
        if pinned.sha != info["revision"]:
            raise RuntimeError(f"Pinned SHA did not resolve exactly for {repo}: {pinned.sha}")
        license_id = getattr(pinned.card_data, "license", None) if pinned.card_data else None
        if str(license_id).lower() != "apache-2.0":
            raise RuntimeError(f"Expected Apache-2.0 metadata for {repo}; got {license_id!r}")
        allowed = set(info["files"])
        hub_repo = hub / f"models--{owner}--{repo.split('/', 1)[1]}"
        snapshot_download(
            repo_id=repo,
            revision=info["revision"],
            cache_dir=str(hub),
            allow_patterns=info["files"],
        )
        snapshot = hub_repo / "snapshots" / info["revision"]
        found = {p.relative_to(snapshot).as_posix() for p in snapshot.rglob("*") if p.is_file() or p.is_symlink()}
        if found != allowed:
            raise RuntimeError(f"Snapshot file set mismatch for {repo}: got {sorted(found)}, expected {sorted(allowed)}")
        refs = hub_repo / "refs" / "main"
        refs.parent.mkdir(parents=True, exist_ok=True)
        refs.write_text(info["revision"], encoding="ascii")
        source_records[repo] = {
            "revision": info["revision"],
            "main_sha": main.sha,
            "license": LICENSE,
            "gated": bool(pinned.gated),
            "owner": owner,
            "primary_sha256": None,
        }
        for name in info["files"]:
            path = snapshot / name
            if not path.is_file():
                raise RuntimeError(f"Missing expected file: {repo}/{name}")
            if path.suffix.lower() in FORBIDDEN_SUFFIXES:
                raise RuntimeError(f"Forbidden pickle-based file present: {repo}/{name}")
            size = path.stat().st_size
            digest = sha256(path)
            if name == info["primary_file"]:
                source_records[repo]["primary_sha256"] = digest
            inventory.append({
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": size,
                "sha256": digest,
                "source_repo": repo,
                "source_revision": info["revision"],
                "source_url": f"https://huggingface.co/{repo}/resolve/{info['revision']}/{name}",
                "license": LICENSE,
            })

    remove_extra_cache_metadata(hub)
    for path in hub.rglob("*"):
        if path.is_dir():
            path.chmod(0o755)
        elif not path.is_symlink():
            path.chmod(0o644)
    for repo, info in MODELS.items():
        snapshot = hub / f"models--{repo.replace('/', '--')}" / "snapshots" / info["revision"]
        for name in info["files"]:
            (snapshot / name).chmod(0o644)

    subprocess.run(
        ["bash", "-euo", "pipefail", "-c", "find huggingface \\( -type f -o -type l \\) -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS"],
        cwd=ROOT,
        check=True,
    )
    shutil.copy2(ROOT / "Dockerfile", ARTIFACTS / "Dockerfile")
    shutil.copy2(ROOT / "SHA256SUMS", ARTIFACTS / "SHA256SUMS")
    with (ARTIFACTS / "file-inventory.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["path", "size_bytes", "sha256", "source_repo", "source_revision", "source_url", "license"])
        writer.writeheader()
        writer.writerows(inventory)

    lines = [f"Download date (UTC): {download_date}", f"Download tool: huggingface_hub {HF_HUB_VERSION}", ""]
    for repo, record in source_records.items():
        number, pin_line = evidence[repo]
        lines.extend([
            f"## {repo}",
            f"- Repository: https://huggingface.co/{repo}",
            f"- Owner: {record['owner']}",
            f"- Pinned commit: `{record['revision']}`",
            f"- Current main commit at download: `{record['main_sha']}`",
            f"- Pinned commit equals main: {'yes' if record['revision'] == record['main_sha'] else 'no'}",
            f"- License: {record['license']} ([license text]({LICENSE_URL}))",
            f"- Gated: {'yes' if record['gated'] else 'no'}",
            f"- Model card: https://huggingface.co/{repo}/blob/{record['revision']}/README.md",
            f"- headroom-ai 0.41.0 wheel pin evidence: `headroom/onnx_runtime.py:{number}`: `{pin_line.strip()}`",
            f"- Main/pin difference: {'main is newer/different; pinned commit was used' if record['revision'] != record['main_sha'] else 'pin matches main'}",
            "",
        ])
    (ARTIFACTS / "sources.md").write_text("\n".join(lines), encoding="utf-8")

    timestamp = download_date.replace("+00:00", "Z")
    model_components = []
    for repo, record in source_records.items():
        component = {
            "type": "data",
            "bom-ref": repo,
            "name": repo,
            "version": record["revision"],
            "hashes": [{"alg": "SHA-256", "content": record["primary_sha256"]}],
            "licenses": [{"license": {"id": LICENSE, "url": LICENSE_URL}}],
            "externalReferences": [{"type": "distribution", "url": f"https://huggingface.co/{repo}/tree/{record['revision']}"}],
            "properties": [
                {"name": "source.main.sha", "value": record["main_sha"]},
                {"name": "source.gated", "value": str(record["gated"]).lower()},
                *[{"name": f"file.{item['path']}.sha256", "value": item["sha256"]} for item in inventory if item["source_repo"] == repo],
                *[{"name": f"file.{item['path']}.size_bytes", "value": str(item["size_bytes"])} for item in inventory if item["source_repo"] == repo],
            ],
        }
        model_components.append(component)
    (ARTIFACTS / "sbom.cdx.json").write_text(json.dumps({
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {"timestamp": timestamp, "component": {"type": "container", "name": "headroom-model-hf", "version": TAG}},
        "components": model_components,
    }, indent=2) + "\n", encoding="utf-8")
    (ARTIFACTS / "XRAY-NOTES.md").write_text(
        "The image is `FROM scratch`; Xray should find no OS packages. It contains only the pinned ONNX model and tokenizer/configuration data; no executable code or pickle files are included. Both model cards declare Apache-2.0, which permits internal redistribution subject to the license terms. The large Kompress ONNX file is expected data and may be reported as a binary blob. Xray clearance must be established by scanning the imported image digest.\n",
        encoding="utf-8",
    )
    verifier, versions = prepare_verification_venv()
    tool_versions = [
        f"python: {subprocess.check_output(['python3', '--version'], text=True).strip()}",
        f"huggingface_hub: {HF_HUB_VERSION}",
        *versions.splitlines(),
        f"syft: {'available' if shutil.which('syft') else 'not installed; CycloneDX SBOM generated from pinned model metadata'}",
        f"docker: {subprocess.check_output(['docker', 'version', '--format', '{{.Client.Version}} / {{.Server.Version}}'], text=True).strip()}",
        f"verification venv: {verifier}",
    ]
    (ARTIFACTS / "tool-versions.txt").write_text("\n".join(tool_versions) + "\n", encoding="utf-8")
    print(f"Prepared {len(inventory)} pinned model files in {ROOT}")
    print(f"Manifest directory: {ARTIFACTS}")


if __name__ == "__main__":
    main()
