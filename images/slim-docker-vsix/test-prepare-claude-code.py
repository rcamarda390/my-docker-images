"""Offline regression checks: python test-prepare-claude-code.py."""
import gzip
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
                'name': 'claude-code', 'publisher': 'Anthropic',
                'version': '2.1.291', 'engines': {'vscode': '^1.98.0'}}))
            z.writestr('extension/node_modules/example/package.json',
                       json.dumps({'name': 'example', 'version': '1.2.3'}))
            z.writestr('extension/native/claude', b'\x7fELFfixture')
        self.data = archive.getvalue()
        self.digest = hashlib.sha256(self.data).hexdigest()

    def prepare(self, data, digest, root):
        script = Path(__file__).with_name('prepare-claude-code.py')
        with patch.object(sys, 'argv', [str(script), '2.1.291', digest, str(root)]), \
                patch('urllib.request.urlopen', return_value=io.BytesIO(data)):
            runpy.run_path(str(script), run_name='__main__')

    def test_plain_and_gzip_preserve_archive_and_dependency_identity(self):
        for data in (self.data, gzip.compress(self.data)):
            with self.subTest(gzip=data != self.data), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(data, self.digest, root)
                self.assertEqual(next(root.rglob('*.vsix')).read_bytes(), self.data)
                sbom = json.loads(next(root.rglob('*.cdx.json')).read_text())
                self.assertEqual(sbom['metadata']['component']['name'], 'anthropic.claude-code')
                self.assertEqual([c['purl'] for c in sbom['components']], ['pkg:npm/example@1.2.3'])
                inventory = json.loads(next(root.rglob('package-manifests.json')).read_text())
                self.assertEqual(len(inventory), 2)

    def test_digest_mismatch_rejects_before_writing_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                self.prepare(gzip.compress(self.data), '0' * 64, root)
            self.assertEqual(list(root.rglob('*.vsix')), [])


if __name__ == '__main__':
    unittest.main()
