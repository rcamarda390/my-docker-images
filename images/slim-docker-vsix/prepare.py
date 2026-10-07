# File: images/slim-docker-vsix/prepare.py
"""Preserve a pinned VSIX and create an explicitly partial, evidence-based SBOM."""
import gzip
import hashlib
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import quote

version, expected, destination = sys.argv[1:]
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
notices = (extracted / 'extension/ThirdPartyNotices.txt').read_text(encoding='utf-8-sig')
notice_packages = re.findall(r'^(@?[\w./-]+) ([0-9]+\.[0-9]+\.[0-9]+[^\s]*) - (.+)$', notices, re.M)
# Do not turn declared semver ranges into invented exact versions. Notices may
# include build tools/types: include only declared, non-type runtime components.
components = []
for name, exact, license_name in notice_packages:
    if name not in manifest.get('dependencies', {}) or name.startswith('@types/'):
        continue
    purl = f'pkg:npm/{quote(name, safe="/")}@{exact}'
    components.append({'type': 'library', 'name': name, 'version': exact,
                       'bom-ref': purl, 'purl': purl,
                       'properties': [{'name': 'vsix:evidence', 'value': 'extension/ThirdPartyNotices.txt; publisher-reported version'}]})
known = {c['name'] for c in components}
missing = {n: v for n, v in manifest.get('dependencies', {}).items() if n not in known and not n.startswith('@types/')}
sbom = {'bomFormat': 'CycloneDX', 'specVersion': '1.5', 'version': 1,
        'metadata': {'component': {'type': 'application', 'name': 'ms-vscode.live-server', 'version': version,
                                  'hashes': [{'alg': 'SHA-256', 'content': digest}]},
                     'properties': [{'name': 'vsix:coverage', 'value': 'partial; publisher notices, not reconstructed full bundle graph'}]},
        'components': components}
def write(name, value):
    (metadata / name).write_text(json.dumps(value, indent=2) + '\n')
write('live-preview.cdx.json', sbom)
write('coverage.json', {'source_url': url, 'vsix_sha256': digest, 'vscode_engine': manifest['engines']['vscode'],
                       'sbom_components': len(components), 'unresolved_runtime_dependencies': missing,
                       'publisher_notice_inventory': notice_packages,
                       'limitations': ['No lockfile or node_modules shipped.', 'Bundled transitive dependencies not fully resolved.',
                                       'Notice versions are publisher assertions, not independent binary verification.',
                                       'Dev/type notice entries excluded from runtime SBOM.',
                                       'Xray recognition and SBOM aggregation must be verified in the deployed instance.']})
write('files.json', [{'path': str(p.relative_to(extracted)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in sorted(extracted.rglob('*')) if p.is_file()])
write_manifest = {'software': 'ms-vscode.live-server', 'version': version, 'method': 'vsix',
                  'install_step': 'VS Code: Install from VSIX', 'payload': '/slim/payload',
                  'sha256': digest, 'metadata': f'/slim/metadata/{identity}'}
(root / 'manifest.json').write_text(json.dumps(write_manifest, indent=2) + '\n')
(metadata / 'SHA256SUMS').write_text(f'{digest}  {identity}.vsix\n')
print(json.dumps({'sha256': digest, 'components': len(components), 'unresolved': missing}))
