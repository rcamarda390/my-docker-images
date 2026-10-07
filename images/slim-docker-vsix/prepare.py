# File: images/slim-docker-vsix/prepare.py
"""Rebuild pinned VSIX payload with corrected bundle and webpack runtime SBOM."""
import gzip
import hashlib
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import quote

version, expected, destination, source_directory = sys.argv[1:]
source = Path(source_directory)
root = Path(destination)
identity = f'ms-vscode.live-server-{version}'
url = f'https://marketplace.visualstudio.com/_apis/public/gallery/publishers//ms-vscode/vsextensions/live-server/{version}/vspackage'
original = root / 'payload/vsix' / identity
extracted = root / 'payload/unpacked' / identity
metadata = root / 'metadata' / identity
for directory in (original, extracted, metadata):
    directory.mkdir(parents=True, exist_ok=True)
with urllib.request.urlopen(url, timeout=60) as response:
    data = response.read()
# Marketplace may return a gzip Content-Encoding even without negotiation.
if data[:2] == b'\x1f\x8b':
    data = gzip.decompress(data)
digest = hashlib.sha256(data).hexdigest()
if digest != expected:
    raise ValueError(f'VSIX checksum mismatch: {digest}')
archive = original / f'{identity}.vsix'
archive.write_bytes(data)
with zipfile.ZipFile(archive) as package:
    for entry in package.infolist():
        target = (extracted / entry.filename).resolve()
        if not target.is_relative_to(extracted.resolve()) or (entry.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError(f'Unsafe ZIP member: {entry.filename}')
    package.extractall(extracted)
manifest = json.loads((extracted / 'extension/package.json').read_text())
if (manifest['publisher'], manifest['name'], manifest['version']) != ('ms-vscode', 'live-server', version):
    raise ValueError('Unexpected extension identity')
# Replace the actual bundled implementation, not just scanner metadata.
manifest['dependencies']['ws'] = '8.21.0'
manifest['displayName'] += ' (rcamarda security rebuild)'
(extracted / 'extension/package.json').write_text(json.dumps(manifest, indent=2) + '\n')
(extracted / 'extension/out/extension.js').write_bytes((source / 'out/extension.js').read_bytes())
notices_path = extracted / 'extension/ThirdPartyNotices.txt'
notices = notices_path.read_text(encoding='utf-8-sig')
if 'ws 8.17.1 - MIT' not in notices:
    raise ValueError('Expected original ws notice not found')
notices_path.write_text(notices.replace('ws 8.17.1 - MIT', 'ws 8.21.0 - MIT'))
(extracted / 'extension/SECURITY-REBUILD.json').write_text(json.dumps({
    'custom_build': True, 'upstream_commit': '79e9df2ffed927625988dfeb6876f84b087f12dd',
    'original_vsix_sha256': digest, 'ws': '8.21.0',
    'fixes': ['CVE-2026-48779', 'CVE-2026-45736'],
    'note': 'Locally rebuilt extension bundle; not the Microsoft Marketplace artifact.'}, indent=2))
# Never ship the original vulnerable VSIX in the remediated image.
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as package:
    for file in sorted(extracted.rglob('*')):
        if file.is_file():
            entry = zipfile.ZipInfo(str(file.relative_to(extracted)), (2025, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            package.writestr(entry, file.read_bytes())
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
components = []
for package in json.loads((source / 'runtime-packages.json').read_text()):
    name, exact = package['name'], package['version']
    purl = f'pkg:npm/{quote(name, safe="/")}@{exact}'
    components.append({'type': 'library', 'name': name, 'version': exact,
                       'bom-ref': purl, 'purl': purl,
                       'properties': [{'name': 'vsix:evidence', 'value': 'webpack compilation module resources; codicons preserved from original media'}]})
if not any(c['name'] == 'ws' and c['version'] == '8.21.0' for c in components):
    raise ValueError('Missing corrected ws in runtime inventory')
known = {c['name'] for c in components}
missing = {n: v for n, v in manifest.get('dependencies', {}).items() if n not in known and not n.startswith('@types/')}
sbom = {'bomFormat': 'CycloneDX', 'specVersion': '1.5', 'version': 1,
        'metadata': {'component': {'type': 'application', 'name': 'ms-vscode.live-server', 'version': version,
                                  'hashes': [{'alg': 'SHA-256', 'content': digest}]},
                     'properties': [{'name': 'vsix:coverage', 'value': 'webpack module inventory; original codicons media; custom source rebuild'}]},
        'components': components}
def write(name, value):
    (metadata / name).write_text(json.dumps(value, indent=2) + '\n')
write('live-preview.cdx.json', sbom)
write('coverage.json', {'source_url': url, 'vsix_sha256': digest, 'vscode_engine': manifest['engines']['vscode'],
                       'sbom_components': len(components), 'unresolved_runtime_dependencies': missing,
                       'custom_rebuild': True, 'original_vsix_sha256': expected,
                       'limitations': ['Runtime inventory derived from webpack module resources, not full functional VS Code testing.',
                                       'Dependencies already bundled within dependency packages may remain unidentified.',
                                       'Build-only packages excluded from runtime SBOM.',
                                       'Xray recognition and SBOM aggregation must be verified in the deployed instance.']})
write('files.json', [{'path': str(p.relative_to(extracted)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in sorted(extracted.rglob('*')) if p.is_file()])
write_manifest = {'software': 'ms-vscode.live-server', 'version': version, 'method': 'vsix-custom-rebuild',
                  'install_step': 'VS Code: Install from VSIX', 'payload': '/slim/payload',
                  'sha256': digest, 'metadata': f'/slim/metadata/{identity}'}
(root / 'manifest.json').write_text(json.dumps(write_manifest, indent=2) + '\n')
(metadata / 'SHA256SUMS').write_text(f'{digest}  {identity}.vsix\n')
print(json.dumps({'sha256': digest, 'components': len(components), 'unresolved': missing}))
