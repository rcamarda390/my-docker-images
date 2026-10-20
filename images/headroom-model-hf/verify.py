"""Verify and export the scratch model-cache image without starting it."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile


TAG = "0.41.0-ext-v1"
IMAGE = f"headroom-model-hf:{TAG}"
CANDIDATE_IMAGE = sys.argv[1]
ROOT = pathlib.Path(__file__).resolve().parent
ARTIFACTS = ROOT.parents[1] / f"headroom-model-hf-{TAG}-manifests"
VERIFIER_IMAGE = "python:3.12-slim"
VERIFIER_VENV = pathlib.Path(tempfile.gettempdir()) / "headroom-model-verifier-0.41.0-ext-v1"
FORBIDDEN_SUFFIXES = (".bin", ".pt", ".pth", ".pkl", ".ckpt", ".pickle")


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def offline_test(cache: pathlib.Path, pin_setting: str | None = None) -> str:
    command = [
        "docker", "run", "--rm", "--network", "none",
        "--mount", f"type=bind,src={cache},dst=/opt/headroom-cache,readonly",
        "--mount", f"type=bind,src={VERIFIER_VENV},dst=/venv,readonly",
        "-e", "HF_HOME=/opt/headroom-cache/huggingface",
        "-e", "HF_HUB_OFFLINE=1",
        "-e", "TRANSFORMERS_OFFLINE=1",
    ]
    if pin_setting is not None:
        command.extend(["-e", f"HEADROOM_HF_PIN={pin_setting}"])
    code = r'''
from pathlib import Path
import onnxruntime as ort
from tokenizers import Tokenizer
base = Path("/opt/headroom-cache/huggingface/hub")
model = (base / "models--chopratejas--kompress-v2-base/snapshots/b1563631b35bfdcee37587ad530147497d820d4c/onnx/kompress-int8-wo.onnx").resolve()
session = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])
print("ONNX_PATH", model)
print("ONNX_INPUTS", [x.name for x in session.get_inputs()])
print("ONNX_OUTPUTS", [x.name for x in session.get_outputs()])
tokenizer_path = (base / "models--answerdotai--ModernBERT-base/snapshots/8949b909ec900327062f0ebf497f51aef5e6f0c8/tokenizer.json").resolve()
tokenizer = Tokenizer.from_file(str(tokenizer_path))
print("TOKENIZER_PATH", tokenizer_path)
print("ENCODE_HELLO_WORLD", tokenizer.encode("hello world").ids)
from headroom.onnx_runtime import hf_hub_download_local_first
print("HEADROOM_LOADER_PATH", hf_hub_download_local_first("chopratejas/kompress-v2-base", "onnx/kompress-int8-wo.onnx", allow_network=False))
'''
    command.extend([VERIFIER_IMAGE, "/venv/bin/python", "-c", code])
    return subprocess.check_output(command, text=True).strip()


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    subprocess.run(["docker", "tag", CANDIDATE_IMAGE, IMAGE], check=True)
    verify_dir = pathlib.Path(tempfile.mkdtemp(prefix="headroom-cache-verify-"))
    cid = run("docker", "create", "--network", "none", IMAGE, "/nonexistent")
    try:
        subprocess.run(["docker", "cp", f"{cid}:/opt/headroom-cache/.", str(verify_dir)], check=True)
    finally:
        subprocess.run(["docker", "rm", cid], check=True, stdout=subprocess.DEVNULL)

    report = []
    report.append("V1: image integrity")
    checksum = subprocess.check_output(["sha256sum", "-c", "SHA256SUMS"], cwd=verify_dir, text=True)
    report.append(checksum.rstrip())
    for path in verify_dir.rglob("*"):
        if path.is_symlink():
            continue
        mode = stat.S_IMODE(path.stat().st_mode)
        expected_mode = 0o755 if path.is_dir() else 0o644
        if mode != expected_mode:
            raise RuntimeError(f"Wrong mode for {path}: {mode:o}, expected {expected_mode:o}")
    report.append("World-readable file and directory modes: PASS")
    report.append("V1: PASS")

    report.append("V2a/b/c: Python 3.12 offline load tests (--network none)")
    output = offline_test(verify_dir)
    report.append("HEADROOM_HF_PIN unset:\n" + output)
    output_off = offline_test(verify_dir, "off")
    report.append("HEADROOM_HF_PIN=off:\n" + output_off)
    report.append("V2a/b/c: PASS")

    inspect_raw = run("docker", "image", "inspect", IMAGE)
    inspect = json.loads(inspect_raw)[0]
    (ARTIFACTS / "docker-inspect.json").write_text(json.dumps(json.loads(inspect_raw), indent=2) + "\n", encoding="utf-8")
    history = run("docker", "history", "--no-trunc", IMAGE)
    (ARTIFACTS / "docker-history.txt").write_text(history + "\n", encoding="utf-8")
    config = inspect["Config"]
    labels = config.get("Labels") or {}
    assert inspect["Os"] == "linux" and inspect["Architecture"] == "amd64"
    assert not config.get("Env") and not config.get("Cmd") and not config.get("Entrypoint")
    assert not config.get("User")
    assert labels.get("headroom.kompress.revision") == "b1563631b35bfdcee37587ad530147497d820d4c"
    assert labels.get("headroom.modernbert.revision") == "8949b909ec900327062f0ebf497f51aef5e6f0c8"
    assert len(inspect["RootFS"]["Layers"]) == 2, inspect["RootFS"]["Layers"]
    copy_rows = [line for line in history.splitlines() if "COPY " in line]
    assert len(copy_rows) == 2, copy_rows
    report.extend([
        "V3: image hygiene",
        f"Image ID: {inspect['Id']}",
        f"Image size bytes: {inspect['Size']}",
        f"Platform: {inspect['Os']}/{inspect['Architecture']}",
        f"RootFS layer count: {len(inspect['RootFS']['Layers'])}",
        f"Environment/entrypoint/command/user: {config.get('Env')!r}/{config.get('Entrypoint')!r}/{config.get('Cmd')!r}/{config.get('User')!r}",
        "Docker history:\n" + history,
        "V3: PASS",
    ])

    report.append("V4: pickle check and image file inventory")
    names = []
    for path in sorted(verify_dir.rglob("*")):
        if path.is_file() or path.is_symlink():
            rel = path.relative_to(verify_dir).as_posix()
            names.append(rel)
            if path.name.lower().endswith(FORBIDDEN_SUFFIXES):
                raise RuntimeError(f"Forbidden pickle-based file found: {rel}")
    report.append("\n".join(names))
    report.append("No pickle-based files found: PASS")
    report.append("V4: PASS")

    shutil.copy2(ROOT / "Dockerfile", ARTIFACTS / "Dockerfile")
    shutil.copy2(ROOT / "SHA256SUMS", ARTIFACTS / "SHA256SUMS")
    archive = ARTIFACTS / "image.tar.gz"
    with archive.open("wb") as output_file:
        saved = subprocess.Popen(["docker", "save", IMAGE], stdout=subprocess.PIPE)
        assert saved.stdout is not None
        compressed = subprocess.Popen(["gzip", "-n"], stdin=saved.stdout, stdout=output_file)
        saved.stdout.close()
        gzip_status = compressed.wait()
        save_status = saved.wait()
        if save_status != 0 or gzip_status != 0:
            raise subprocess.CalledProcessError(save_status or gzip_status, "docker save | gzip -n")
    with tarfile.open(archive, "r:gz") as saved_archive:
        members = saved_archive.getnames()
        assert "manifest.json" in members
        manifest = json.load(saved_archive.extractfile("manifest.json"))
        layers = manifest[0]["Layers"]
        assert len(layers) == 2, layers
        assert all(layer in members for layer in layers), layers
    digest = sha256(archive)
    (ARTIFACTS / "image.tar.gz.sha256").write_text(f"{digest}  image.tar.gz\n", encoding="ascii")
    report.append(f"Docker archive: {archive.name}, {archive.stat().st_size} bytes, SHA-256 {digest}")
    report.append(f"Saved archive includes manifest.json and {len(layers)} image layers: PASS")
    report.append("Registry publication: disabled")
    (ARTIFACTS / "verification-output.txt").write_text("\n\n".join(report) + "\n", encoding="utf-8")
    print((ARTIFACTS / "verification-output.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
