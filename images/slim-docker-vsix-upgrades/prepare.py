# File: images/slim-docker-vsix-upgrades/prepare.py
"""Download pinned Marketplace VSIX files, validate, unpack, inventory, SBOM.

usage: prepare.py extensions.json /slim 1.98.2
Any failure aborts the build. Nothing is silently substituted or skipped.
"""
import gzip
import hashlib
import io
import json
import re
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree

URL = ("https://marketplace.visualstudio.com/_apis/public/gallery/publishers/"
       "{p}/vsextensions/{n}/{v}/vspackage")
PLATFORMS = ("linux-x64", None)  # prefer Amazon Linux 2 x86_64 build, else universal


# ---- npm-style semver subset: ^ ~ >= <= > < = x-ranges * and || ----
def _ver(text):
    nums = [int(x) for x in re.match(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", text).groups(default="0")]
    return tuple(nums)


def _comparator(op, text):
    parts = text.lstrip("v").split("-")[0].split(".")
    wild = [p in ("x", "X", "*", "") for p in parts] + [True] * (3 - len(parts))
    nums = [0 if w else int(p) for w, p in zip(wild, parts + ["0"] * 3)]
    lo = tuple(nums[:3])
    first_wild = wild.index(True) if True in wild else 3
    if first_wild == 0:
        return lambda v: True
    if op in ("", "="):
        hi = list(lo[:first_wild]); hi[-1] += 1
        return lambda v: lo <= v < tuple(hi + [0] * (3 - len(hi)))
    if op == "^":
        idx = next((i for i in range(3) if lo[i] != 0), 2) if first_wild == 3 else 0
        hi = list(lo[:idx + 1]); hi[-1] += 1
        return lambda v: lo <= v < tuple(hi + [0] * (3 - len(hi)))
    if op == "~":
        idx = 1 if first_wild >= 2 else 0
        hi = list(lo[:idx + 1]); hi[-1] += 1
        return lambda v: lo <= v < tuple(hi + [0] * (3 - len(hi)))
    return {">=": lambda v: v >= lo, "<=": lambda v: v <= lo,
            ">": lambda v: v > lo, "<": lambda v: v < lo}[op]


def satisfies(version, rng):
    v = _ver(version)
    for alt in rng.split("||"):
        tokens = re.findall(r"(\^|~|>=|<=|>|<|=)?\s*([vV]?[\dxX*][\w.*+-]*)", alt.strip())
        if tokens and all(_comparator(op, t)(v) for op, t in tokens):
            return True
    return False


# ---- download / extraction ----
def download(publisher, name, version):
    last = None
    for platform in PLATFORMS:
        url = URL.format(p=quote(publisher), n=quote(name), v=quote(version))
        if platform:
            url += f"?targetPlatform={platform}"
        req = urllib.request.Request(url, headers={"Accept-Encoding": "identity"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
        except urllib.error.HTTPError as e:
            last = f"{url}: HTTP {e.code}"
            continue
        if data[:2] == b"\x1f\x8b":  # Marketplace may gzip despite identity
            data = gzip.decompress(data)
        if data[:2] != b"PK":
            raise ValueError(f"{url}: not a ZIP/VSIX (HTML error page?)")
        return url, platform, data
    raise ValueError(f"download failed for {publisher}.{name}@{version}: {last}")


def safe_extract(archive, dest):
    """Extract every member; reject traversal, absolute, links, duplicates."""
    dest = dest.resolve()
    seen, files = set(), []
    for info in archive.infolist():
        n = info.filename
        if n.startswith("/") or "\\" in n or ".." in Path(n).parts or re.match(r"^[A-Za-z]:", n):
            raise ValueError(f"unsafe ZIP member: {n}")
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError(f"symlink ZIP member: {n}")
        if n in seen:
            raise ValueError(f"duplicate ZIP member: {n}")
        seen.add(n)
        target = (dest / n).resolve()
        if not target.is_relative_to(dest):
            raise ValueError(f"unsafe ZIP member: {n}")
        if n.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        data = archive.read(info)
        target.write_bytes(data)
        mode = (info.external_attr >> 16) & 0o777
        if mode:
            target.chmod(mode | 0o600)
        files.append((n, len(data), hashlib.sha256(data).hexdigest()))
    return files


def vsixmanifest_facts(raw):
    ns = {"v": "http://schemas.microsoft.com/developer/vsx-schema/2011"}
    root = ElementTree.fromstring(raw)
    ident = root.find("./v:Metadata/v:Identity", ns)
    prerelease = any(
        p.get("Id") == "Microsoft.VisualStudio.Code.PreRelease" and p.get("Value", "").lower() == "true"
        for p in root.findall(".//v:Property", ns))
    return {"identity": dict(ident.attrib), "prerelease": prerelease}


def process(ext, vscode, root, now):
    ext_id, version = ext["id"], ext["version"]
    publisher, name = ext_id.split(".", 1)
    key = f"{ext_id}-{version}"
    url, platform, data = download(publisher, name, version)
    digest = hashlib.sha256(data).hexdigest()
    vsix = root / "payload/vsix" / f"{key}.vsix"
    vsix.parent.mkdir(parents=True, exist_ok=True)
    vsix.write_bytes(data)
    out = root / "payload/unpacked" / key
    meta = root / "metadata/extensions" / key
    out.mkdir(parents=True); meta.mkdir(parents=True)

    with zipfile.ZipFile(io.BytesIO(data)) as z:
        bad = z.testzip()
        if bad:
            raise ValueError(f"{key}: corrupt member {bad}")
        members = [i for i in z.infolist() if not i.filename.endswith("/")]
        uncompressed = sum(i.file_size for i in members)
        extracted = safe_extract(z, out)
    pkg = json.loads((out / "extension/package.json").read_text(encoding="utf-8"))
    facts = vsixmanifest_facts((out / "extension.vsixmanifest").read_bytes())
    if (pkg.get("publisher", "").lower(), pkg.get("name", "").lower(), pkg.get("version")) != (
            publisher.lower(), name.lower(), version):
        raise ValueError(f"{key}: identity mismatch {pkg.get('publisher')}.{pkg.get('name')}@{pkg.get('version')}")
    if facts["prerelease"]:
        raise ValueError(f"{key}: pre-release package; not approved")
    engine = pkg.get("engines", {}).get("vscode")
    if not engine:
        raise ValueError(f"{key}: no engines.vscode")
    if not satisfies(vscode, engine):
        raise ValueError(f"{key}: engines.vscode {engine} excludes VS Code {vscode}")

    # completeness: every archive member present, byte-identical
    on_disk = {str(p.relative_to(out)) for p in out.rglob("*") if p.is_file()}
    if on_disk != {n for n, _, _ in extracted} or len(extracted) != len(members):
        raise ValueError(f"{key}: extracted file set differs from archive")
    for n, size, sha in extracted:
        raw = (out / n).read_bytes()
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError(f"{key}: altered member {n}")
    extracted_bytes = sum(s for _, s, _ in extracted)
    if extracted_bytes != uncompressed:
        raise ValueError(f"{key}: byte count mismatch")

    components, seen = [], set()
    for n, _, _ in extracted:
        if not n.endswith("package.json") or n == "extension/package.json":
            continue
        try:
            p = json.loads((out / n).read_bytes().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(p, dict) or not p.get("name") or not p.get("version"):
            continue
        k = (p["name"], str(p["version"]))
        if k in seen:
            continue
        seen.add(k)
        purl = f"pkg:npm/{quote(p['name'], safe='/@')}@{quote(str(p['version']), safe='')}"
        lic = p.get("license")
        comp = {"type": "library", "name": p["name"], "version": str(p["version"]),
                "purl": purl, "bom-ref": f"{key}:{purl}:{n}",
                "properties": [{"name": "vsix:path", "value": n}]}
        if isinstance(lic, str):
            comp["licenses"] = [{"license": {"name": lic}}]
        components.append(comp)

    elf = [n for n, _, _ in extracted if (out / n).read_bytes()[:4] == b"\x7fELF"]
    sbom = {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {
            "timestamp": now,
            "component": {"type": "application", "name": ext_id, "version": version,
                          "bom-ref": key, "hashes": [{"alg": "SHA-256", "content": digest}]},
            "properties": [
                {"name": "vsix:source", "value": "Microsoft Visual Studio Marketplace"},
                {"name": "vsix:downloadUrl", "value": url},
                {"name": "vsix:downloadTimestamp", "value": now},
                {"name": "vsix:vscodeEngine", "value": engine},
                {"name": "vsix:targetPlatform", "value": platform or "universal"},
                {"name": "vsix:unpacked", "value": f"/slim/payload/unpacked/{key}"}]},
        "components": components}
    coverage = {
        "files": len(extracted), "package_manifests_as_components": len(components),
        "native_elf_files": elf,
        "limitations": [
            "Components come only from package.json files physically present in the VSIX.",
            "Minified/bundled dependencies without manifests are NOT enumerated; Xray content analysis is authoritative.",
            "No Syft run; SBOM is not an independent dependency resolution."]}
    compat = {"extension": ext_id, "version": version, "installed": ext.get("installed"),
              "engines.vscode": engine, "target_vscode": vscode, "compatible": True,
              "prerelease": False, "marketplace_identity": facts["identity"]}

    def wj(path, value):
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    wj(meta / "files.json", [{"path": n, "size": s, "sha256": h} for n, s, h in sorted(extracted)])
    wj(meta / "coverage.json", {**coverage, "archive_members": len(members),
                                "uncompressed_bytes": uncompressed, "extracted_bytes": extracted_bytes,
                                "extraction_validation": "pass"})
    wj(meta / "compatibility.json", compat)
    wj(meta / "extension.cdx.json", sbom)
    (meta / "SHA256SUMS").write_text(f"{digest}  {key}.vsix\n", encoding="utf-8")
    sbom_dir = root / "sbom/extensions"; sbom_dir.mkdir(parents=True, exist_ok=True)
    wj(sbom_dir / f"{key}.cdx.json", sbom)
    return ({"id": ext_id, "version": version, "installed": ext.get("installed"), "key": key,
             "sha256": digest, "size": len(data), "target_platform": platform or "universal",
             "download_url": url, "engines.vscode": engine, "files": len(extracted)}, sbom)


def main(config, dest, vscode):
    cfg = json.loads(Path(config).read_text(encoding="utf-8"))
    if cfg["vscode_version"] != vscode:
        raise ValueError(f"extensions.json targets {cfg['vscode_version']}, build asked {vscode}")
    root = Path(dest)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    inventory, sboms = [], []
    for ext in cfg["extensions"]:
        rec, sbom = process(ext, vscode, root, now)
        inventory.append(rec); sboms.append(sbom)
        print(json.dumps(rec))
    wj = lambda p, v: (root / p).parent.mkdir(parents=True, exist_ok=True) or (root / p).write_text(
        json.dumps(v, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    wj("metadata/inventory.json", inventory)
    wj("metadata/compatibility.json", [{"id": r["id"], "version": r["version"],
                                        "engines.vscode": r["engines.vscode"], "vscode": vscode,
                                        "compatible": True} for r in inventory])
    wj("manifest.json", {"target_vscode": vscode, "count": len(inventory), "extensions": inventory})
    wj("metadata/build-provenance.json", {
        "built_at": now, "source": cfg["source"], "target_vscode": vscode,
        "config_sha256": hashlib.sha256(Path(config).read_bytes()).hexdigest(),
        "hash_pinning": "none: SHA-256 recorded at build time from Marketplace download",
        "builder": "python:3.12-slim"})
    wj("sbom/combined.cdx.json", {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {"timestamp": now, "component": {
            "type": "application", "name": "slim-docker-vsix-upgrades", "version": vscode}},
        "components": [dict(s["metadata"]["component"], type="application",
                            components=s["components"]) for s in sboms]})
    # checksum file over metadata + sbom + manifest, written last
    lines = []
    for p in sorted(list((root / "metadata").rglob("*")) + list((root / "sbom").rglob("*")) + [root / "manifest.json"]):
        if p.is_file() and p != root / "metadata/SHA256SUMS":
            lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root)}")
    (root / "metadata/SHA256SUMS").write_text("\n".join(sorted(lines)) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:4])
