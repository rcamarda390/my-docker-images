# File: images/slim-docker-vsix-upgrades/verify.py
"""Build-time acceptance checks over /slim. usage: verify.py extensions.json /slim 1.98.2"""
import hashlib
import json
import re
import sys
from pathlib import Path

config, dest, vscode = sys.argv[1:4]
root = Path(dest)
cfg = json.loads(Path(config).read_text(encoding="utf-8"))
manifest = json.loads((root / "manifest.json").read_text())
want = {(e["id"], e["version"]) for e in cfg["extensions"]}
got = {(e["id"], e["version"]) for e in manifest["extensions"]}
assert want == got, f"manifest mismatch: missing={want - got} unexpected={got - want}"
assert not any("claude-dev" in i or i.startswith("saoudrizwan.") for i, _ in got), "custom Cline present"
assert vscode == manifest["target_vscode"] == cfg["vscode_version"]

vsix_files = sorted(p.name for p in (root / "payload/vsix").iterdir())
assert vsix_files == sorted(f"{i}-{v}.vsix" for i, v in want), f"unexpected vsix set {vsix_files}"
unpacked = sorted(p.name for p in (root / "payload/unpacked").iterdir())
assert unpacked == sorted(f"{i}-{v}" for i, v in want), f"unexpected unpacked set {unpacked}"

for e in manifest["extensions"]:
    key = e["key"]
    vsix = root / "payload/vsix" / f"{key}.vsix"
    assert hashlib.sha256(vsix.read_bytes()).hexdigest() == e["sha256"], f"{key}: sha mismatch"
    meta = root / "metadata/extensions" / key
    for f in ("SHA256SUMS", "files.json", "coverage.json", "compatibility.json", "extension.cdx.json"):
        assert (meta / f).is_file(), f"{key}: missing {f}"
    comp = json.loads((meta / "compatibility.json").read_text())
    assert comp["compatible"] and comp["version"] == e["version"]
    cov = json.loads((meta / "coverage.json").read_text())
    assert cov["extraction_validation"] == "pass" and cov["uncompressed_bytes"] == cov["extracted_bytes"]
    for f in json.loads((meta / "files.json").read_text()):
        raw = (root / "payload/unpacked" / key / f["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == f["sha256"], f"{key}: {f['path']} altered"
    for sb in (meta / "extension.cdx.json", root / "sbom/extensions" / f"{key}.cdx.json"):
        assert json.loads(sb.read_text())["bomFormat"] == "CycloneDX"
assert json.loads((root / "sbom/combined.cdx.json").read_text())["bomFormat"] == "CycloneDX"

# secret scan of metadata only (payload is third-party content, preserved untouched)
pat = re.compile(r"AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----")
for p in list((root / "metadata").rglob("*")) + [root / "manifest.json", root / "AGENT.md"]:
    if p.is_file() and p.exists():
        assert not pat.search(p.read_text(errors="ignore")), f"secret-like string in {p}"
print(f"verify ok: {len(got)} extensions for VS Code {vscode}")
