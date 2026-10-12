"""Offline regression checks: python test-prepare.py."""
import hashlib
import io
import json
import runpy
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


class PrepareTests(unittest.TestCase):
    def setUp(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('extension/package.json', json.dumps({
                'name': 'codeburn', 'publisher': 'codeburn',
                'version': '1.0.2', 'engines': {'vscode': '^1.98.0'}}))
            z.writestr('extension/node_modules/example/package.json',
                       json.dumps({'name': 'example', 'version': '1.2.3'}))
            z.writestr('extension/native/example', b'\x7fELFfixture')
        self.data = archive.getvalue()
        self.digest = hashlib.sha256(self.data).hexdigest()

    def prepare(self, data, digest, root):
        script = Path(__file__).with_name('prepare.py')
        source = root / 'input.zip'
        source.write_bytes(data)
        with patch.object(sys, 'argv', [str(script), '1.0.2', digest, str(source), str(root)]):
            runpy.run_path(str(script), run_name='__main__')

    def test_preserve_archive_and_dependency_identity(self):
        for data in (self.data,):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(data, self.digest, root)
                self.assertEqual(next(root.rglob('*.vsix')).read_bytes(), self.data)
                sbom = json.loads(next(root.rglob('*.cdx.json')).read_text())
                self.assertEqual(sbom['metadata']['component']['name'], 'codeburn.codeburn')
                self.assertEqual([c['purl'] for c in sbom['components']], ['pkg:npm/example@1.2.3'])
                inventory = json.loads(next(root.rglob('package-manifests.json')).read_text())
                self.assertEqual(len(inventory), 2)

    def test_digest_mismatch_rejects_before_writing_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                self.prepare(self.data, '0' * 64, root)
            self.assertEqual(list(root.rglob('*.vsix')), [])

    def test_path_traversal_rejected(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('../escape', 'unsafe')
        data = archive.getvalue()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'Unsafe ZIP member'):
                self.prepare(data, hashlib.sha256(data).hexdigest(), Path(tmp))


if __name__ == '__main__':
    unittest.main()
