"""Replace four external CLI dependencies, then repack the installable VSIX."""
import base64
import hashlib
import io
import json
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

base = Path(__file__).resolve().parent
fixes = json.loads((base / 'security-fixes.json').read_text())
source = base / 'codeburn.codeburn-1.0.2.vsix'
assert hashlib.sha256(source.read_bytes()).hexdigest() == '2ba28c0750433108639fe5af698f3e00ec23d494ac4cb39d67d56382e4f364ee'
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    with zipfile.ZipFile(source) as archive:
        for entry in archive.infolist():
            assert (root / entry.filename).resolve().is_relative_to(root.resolve())
            assert entry.external_attr >> 16 & 0o170000 != 0o120000
        archive.extractall(root)
    modules = root / 'extension/cli/node_modules'
    for fix in fixes:
        with urllib.request.urlopen(fix['url'], timeout=60) as response:
            data = response.read()
        assert 'sha512-' + base64.b64encode(hashlib.sha512(data).digest()).decode() == fix['integrity'], fix['name']
        target = modules / fix['name']
        assert target.is_dir(), fix['name']
        shutil.rmtree(target)
        target.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            archive.extractall(target, filter='data')
        package = target / 'package'
        for child in package.iterdir():
            shutil.move(str(child), target / child.name)
        package.rmdir()
        manifest = json.loads((target / 'package.json').read_text())
        assert (manifest['name'], manifest['version']) == (fix['name'], fix['version'])
    # Dependency versions are external imports in the unchanged CLI bundle.
    # Keep all other VSIX files byte-identical, including license/notices.
    with zipfile.ZipFile(base / 'fixed.vsix', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob('*')):
            if path.is_file():
                info = zipfile.ZipInfo(str(path.relative_to(root)), (2026, 10, 12, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
