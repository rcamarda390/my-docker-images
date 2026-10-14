# File: images/slim-docker-vsix-upgrades/prepare.py
"""Preserve pinned Marketplace VSIX bytes and prove complete, safe extraction."""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import quote
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone

LIMITATIONS = [
    'Components derive only from package.json manifests present in the VSIX.',
    'Declared version ranges are recorded, not represented as resolved dependencies.',
    'Bundled JavaScript and native binaries may contain additional dependencies.',
    'Embedded SBOMs do not establish Xray component coverage or security clearance.',
    'VS Code engine compatibility does not prove Amazon Linux 2 native ABI compatibility.',
]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract(package, destination):
    """Reject unsafe/ambiguous paths before writing any archive member."""
    names = set()
    entries = package.infolist()
    for entry in entries:
        name = entry.filename.rstrip('/')
        path = PurePosixPath(name)
        mode = entry.external_attr >> 16
        if (not name or '\\' in name or path.is_absolute() or
                any(part in ('', '.', '..') for part in name.split('/')) or
                ':' in name or name in names or
                stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
            raise ValueError(f'Unsafe or duplicate ZIP member: {entry.filename}')
        names.add(name)
    files = {e.filename for e in entries if not e.is_dir()}
    for name in names:
        if any(str(parent) in files for parent in PurePosixPath(name).parents):
            raise ValueError(f'ZIP file/directory conflict: {name}')
    inventory = []
    for entry in entries:
        target = destination / entry.filename
        if entry.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        data = package.read(entry)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        mode = entry.external_attr >> 16
        if mode & 0o111:
            target.chmod(0o755)
        if target.read_bytes() != data or len(data) != entry.file_size:
            raise ValueError(f'Extraction mismatch: {entry.filename}')
        inventory.append(dict(path=entry.filename, size=len(data), sha256=digest(data)))
    actual = {str(p.relative_to(destination)) for p in destination.rglob('*') if p.is_file()}
    if actual != {x['path'] for x in inventory}:
        raise ValueError('Extracted file inventory differs from ZIP members')
    return sorted(inventory, key=lambda x: x['path'])


def prepare(pin, target_vscode, root, local_source=None):
    if local_source:
        data = local_source.read_bytes()
    else:
        request = urllib.request.Request(pin['source_url'], headers={'Accept-Encoding': 'identity'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    data = response.read()
                break
            except urllib.error.HTTPError as error:
                if error.code not in (429, 502, 503, 504) or attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        if data.startswith(b'\x1f\x8b'):
            data = gzip.decompress(data)
    if digest(data) != pin['sha256']:
        raise ValueError(f"VSIX checksum mismatch: {pin['id']}")
    identity = f"{pin['id']}-{pin['version']}"
    filename = identity + '.vsix'
    archive_path = root / 'payload/vsix' / filename
    unpacked = root / 'payload/unpacked' / identity
    metadata = root / 'metadata/extensions' / identity
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_bytes(data)
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        manifest = json.loads(package.read('extension/package.json'))
        xml = ET.fromstring(package.read('extension.vsixmanifest'))
        xml_identity = next(e for e in xml.iter() if e.tag.endswith('}Identity'))
        expected_id = pin['id'].lower()
        if ((manifest['publisher'] + '.' + manifest['name']).lower() != expected_id or
                (xml_identity.attrib['Publisher'] + '.' + xml_identity.attrib['Id']).lower() != expected_id or
                manifest['version'] != pin['version'] or xml_identity.attrib['Version'] != pin['version']):
            raise ValueError(f'Unexpected extension identity: {identity}')
        platform = xml_identity.attrib.get('TargetPlatform', 'universal')
        if platform != pin['target_platform'] or platform not in ('universal', 'linux-x64'):
            raise ValueError(f'Unexpected target platform: {identity}: {platform}')
        if any(e.attrib.get('Id') == 'Microsoft.VisualStudio.Code.PreRelease' and
               e.attrib.get('Value', '').lower() == 'true' for e in xml.iter()):
            raise ValueError(f'Prerelease rejected: {identity}')
        engine = manifest['engines']['vscode']
        if engine != pin['vscode_engine']:
            raise ValueError(f'Engine differs from verified pin: {identity}')
        subprocess.run(['node', '-e',
                        'if(!require("semver").satisfies(process.argv[1],process.argv[2]))process.exit(1)',
                        target_vscode, engine], check=True)
        inventory = extract(package, unpacked)
        total_size = sum(e.file_size for e in package.infolist() if not e.is_dir())
        member_count = len(package.infolist())
    components = {}
    manifests = []
    for record in inventory:
        if PurePosixPath(record['path']).name != 'package.json':
            continue
        try:
            package = json.loads((unpacked / record['path']).read_text(encoding='utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        manifests.append(dict(path=record['path'], name=package.get('name'), version=package.get('version'),
                              dependencies=package.get('dependencies', {}),
                              optionalDependencies=package.get('optionalDependencies', {})))
        if record['path'] == 'extension/package.json' or not package.get('name') or not package.get('version'):
            continue
        purl = f"pkg:npm/{quote(package['name'], safe='/')}@{quote(str(package['version']), safe='')}"
        component = components.setdefault(purl, dict(type='library', name=package['name'],
                         version=str(package['version']), purl=purl, **{'bom-ref': purl}, properties=[]))
        component['properties'].append(dict(name='vsix:path', value=record['path']))
        if isinstance(package.get('license'), str):
            component['properties'].append(dict(name='vsix:declaredLicense', value=package['license']))
    compatibility = dict(id=pin['id'], version=pin['version'], target_vscode=target_vscode,
                         vscode_engine=engine, compatible=True, stable=True, target_platform=platform)
    write_json(metadata / 'compatibility.json', compatibility)
    write_json(metadata / 'files.json', inventory)
    write_json(metadata / 'package-manifests.json', manifests)
    write_json(metadata / 'coverage.json', dict(archive_members=member_count, extracted_files=len(inventory),
               archive_uncompressed_bytes=total_size, extracted_bytes=sum(x['size'] for x in inventory),
               missing_or_mismatched_members=[], extraction_verified=True, package_manifests=len(manifests),
               sbom_components=len(components), limitations=LIMITATIONS))
    metadata.mkdir(parents=True, exist_ok=True)
    (metadata / 'SHA256SUMS').write_text(''.join(f"{x['sha256']}  payload/unpacked/{identity}/{x['path']}\n" for x in inventory) +
                                       f"{pin['sha256']}  payload/vsix/{filename}\n")
    sbom = dict(bomFormat='CycloneDX', specVersion='1.5', version=1,
                metadata=dict(timestamp=datetime.now(timezone.utc).isoformat(), component=dict(type='application', name=pin['id'], version=pin['version'],
                  hashes=[dict(alg='SHA-256', content=pin['sha256'])]),
                  properties=[dict(name='vsix:'+k, value=str(v)) for k,v in
                              dict(source_url=pin['source_url'], target_platform=platform, vscode_engine=engine, verified_at=pin['verified_at'], sha256=pin['sha256']).items()]),
                components=list(components.values()))
    write_json(metadata / 'extension.cdx.json', sbom)
    write_json(root / 'sbom/extensions' / (identity + '.cdx.json'), sbom)
    return dict(**pin, downloaded_at=datetime.now(timezone.utc).isoformat(),
                vsix='payload/vsix/'+filename, unpacked='payload/unpacked/'+identity,
                extension_dependencies=manifest.get('extensionDependencies', []),
                repository=manifest.get('repository'), license=manifest.get('license'),
                compatibility=compatibility), sbom


def main():
    pins_path, destination, *sources = sys.argv[1:]
    pins = json.loads(Path(pins_path).read_text())
    root = Path(destination)
    if root.exists():
        raise ValueError('Destination must not exist; use a clean build directory')
    ids = [p['id'].lower() for p in pins['extensions']]
    if len(ids) != len(set(ids)) or any(x == 'saoudrizwan.claude-dev' for x in ids):
        raise ValueError('Duplicate or exempt extension selected')
    records, components = [], {}
    for pin in pins['extensions']:
        source = Path(sources[0]) / f"{pin['id']}-{pin['version']}.vsix" if sources else None
        record, sbom = prepare(pin, pins['target_vscode'], root, source)
        records.append(record)
        extension_ref = f"vsix:{pin['id']}@{pin['version']}"
        components[extension_ref] = dict(sbom['metadata']['component'], **{'bom-ref': extension_ref})
        for component in sbom['components']:
            components.setdefault(component['bom-ref'], component)
        print(pin['id'] + ': identity, checksum, compatibility and extraction verified', flush=True)
    write_json(root / 'manifest.json', dict(image='slim-docker-vsix-upgrades', target_vscode=pins['target_vscode'],
               method='official-marketplace-vsix', extensions=records))
    write_json(root / 'metadata/inventory.json', records)
    write_json(root / 'metadata/compatibility.json', [r['compatibility'] for r in records])
    write_json(root / 'metadata/build-provenance.json', dict(created_at=datetime.now(timezone.utc).isoformat(),
               pins_sha256=digest(Path(pins_path).read_bytes()), git_revision=os.environ.get('SOURCE_REVISION'),
               source='Microsoft Visual Studio Marketplace', limitations=LIMITATIONS))
    write_json(root / 'sbom/combined.cdx.json', dict(bomFormat='CycloneDX', specVersion='1.5', version=1,
               metadata=dict(component=dict(type='container', name='slim-docker-vsix-upgrades',
                                            version=os.environ.get('IMAGE_VERSION', '2026.10.14'))),
               components=list(components.values())))
    (root / 'metadata/SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['vsix']}\n" for r in records))


if __name__ == '__main__':
    main()
