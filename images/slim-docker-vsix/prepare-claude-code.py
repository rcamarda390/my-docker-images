# File: images/slim-docker-vsix/prepare-claude-code.py
"""Download and unpack the pinned Anthropic Claude Code VSIX for Xray inspection."""
import hashlib
import json
import sys
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import quote

version, destination = sys.argv[1:]
root = Path(destination)
identity = f"anthropic.claude-code-{version}-linux-x64"
url = (
    "https://marketplace.visualstudio.com/_apis/public/gallery/"
    f"publishers/anthropic/vsextensions/claude-code/{version}/vspackage"
    "?targetPlatform=linux-x64"
)
original = root / "payload/vsix" / identity
extracted = root / "payload/unpacked" / identity
metadata = root / "metadata" / identity
for directory in (original, extracted, metadata):
    directory.mkdir(parents=True, exist_ok=True)

request = urllib.request.Request(url, headers={"Accept-Encoding": "identity"})
with urllib.request.urlopen(request, timeout=120) as response:
    data = response.read()

digest = hashlib.sha256(data).hexdigest()
archive = original / f"{identity}.vsix"
archive.write_bytes(data)

with zipfile.ZipFile(archive) as package:
    extracted_root = extracted.resolve()
    for entry in package.infolist():
        target = (extracted / entry.filename).resolve()
        mode = entry.external_attr >> 16
        if not target.is_relative_to(extracted_root) or mode & 0o170000 == 0o120000:
            raise ValueError(f"Unsafe ZIP member: {entry.filename}")
    package.extractall(extracted)

manifest_path = extracted / "extension/package.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
if (manifest.get("publisher"), manifest.get("name"), manifest.get("version")) != (
    "anthropic",
    "claude-code",
    version,
):
    raise ValueError("Unexpected extension identity")

vscode_engine = manifest.get("engines", {}).get("vscode")
if not vscode_engine:
    raise ValueError("VSIX package.json does not declare engines.vscode")

file_inventory = []
native_binaries = []
package_manifests = []
components = []
seen_components = set()

for path in sorted(extracted.rglob("*")):
    if not path.is_file():
        continue
    raw = path.read_bytes()
    relative = str(path.relative_to(extracted))
    sha256 = hashlib.sha256(raw).hexdigest()
    file_inventory.append({"path": relative, "size": len(raw), "sha256": sha256})

    if raw.startswith(b"\x7fELF"):
        native_binaries.append(
            {"path": relative, "size": len(raw), "sha256": sha256, "format": "ELF"}
        )

    if path.name != "package.json":
        continue
    try:
        package_data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        continue
    package_name = package_data.get("name")
    package_version = package_data.get("version")
    package_manifests.append(
        {
            "path": relative,
            "name": package_name,
            "version": package_version,
            "dependencies": package_data.get("dependencies", {}),
            "optionalDependencies": package_data.get("optionalDependencies", {}),
        }
    )
    if not package_name or not package_version:
        continue
    key = (package_name, package_version)
    if key in seen_components:
        continue
    seen_components.add(key)
    purl = f"pkg:npm/{quote(package_name, safe='/')}@{quote(str(package_version), safe='')}"
    components.append(
        {
            "type": "library",
            "name": package_name,
            "version": str(package_version),
            "purl": purl,
            "bom-ref": purl,
            "properties": [{"name": "vsix:path", "value": relative}],
        }
    )

if not native_binaries:
    raise ValueError("Expected at least one ELF native binary in linux-x64 VSIX")

sbom = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.5",
    "version": 1,
    "metadata": {
        "component": {
            "type": "application",
            "name": "anthropic.claude-code",
            "version": version,
            "hashes": [{"alg": "SHA-256", "content": digest}],
        },
        "properties": [
            {"name": "vsix:source", "value": "Microsoft Visual Studio Marketplace"},
            {"name": "vsix:targetPlatform", "value": "linux-x64"},
            {"name": "vsix:vscodeEngine", "value": vscode_engine},
            {"name": "vsix:artifact", "value": f"/slim/payload/vsix/{identity}/{identity}.vsix"},
            {"name": "vsix:unpacked", "value": f"/slim/payload/unpacked/{identity}"},
        ],
    },
    "components": components,
}

def write_json(name, value):
    (metadata / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

write_json("claude-code.cdx.json", sbom)
write_json("files.json", file_inventory)
write_json("package-manifests.json", package_manifests)
write_json("native-binaries.json", native_binaries)
write_json(
    "coverage.json",
    {
        "source_url": url,
        "vsix_sha256": digest,
        "vscode_engine": vscode_engine,
        "target_platform": "linux-x64",
        "files": len(file_inventory),
        "package_manifests": len(package_manifests),
        "sbom_components": len(components),
        "native_binaries": len(native_binaries),
        "custom_rebuild": False,
        "limitations": [
            "Official Marketplace VSIX is preserved byte-for-byte; no source rebuild is performed.",
            "CycloneDX components come from package.json manifests physically present in the extracted VSIX.",
            "Bundled/minified dependencies without package manifests may require Xray binary/content analysis.",
            "Xray detection and embedded SBOM aggregation must be verified in the deployed JFrog instance.",
        ],
    },
)
write_json(
    "manifest.json",
    {
        "software": "anthropic.claude-code",
        "version": version,
        "target_platform": "linux-x64",
        "method": "official-marketplace-vsix",
        "source_url": url,
        "install_step": "VS Code: Install from VSIX",
        "vsix": f"/slim/payload/vsix/{identity}/{identity}.vsix",
        "unpacked": f"/slim/payload/unpacked/{identity}",
        "metadata": f"/slim/metadata/{identity}",
        "sha256": digest,
    },
)
(metadata / "SHA256SUMS").write_text(f"{digest}  {identity}.vsix\n", encoding="utf-8")

print(
    json.dumps(
        {
            "software": "anthropic.claude-code",
            "version": version,
            "sha256": digest,
            "vscode_engine": vscode_engine,
            "files": len(file_inventory),
            "package_manifests": len(package_manifests),
            "native_binaries": len(native_binaries),
        }
    )
)
