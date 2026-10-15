# File: images/slim-docker-vsix-upgrades/test-prepare.py
"""Regression checks for archive safety and lossless extraction."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('prepare', Path(__file__).with_name('prepare.py'))
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class Extraction(unittest.TestCase):
    def archive(self, entries):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z:
            for name, content in entries:
                z.writestr(name, content)
        data.seek(0)
        return zipfile.ZipFile(data)

    def test_preserves_all_files_and_empty_directories(self):
        with tempfile.TemporaryDirectory() as directory, self.archive([
                ('extension/.hidden', b'hello'), ('extension/node_modules/pkg/a.js', b'world'),
                ('empty/', b'')]) as z:
            root = Path(directory)
            records = prepare.extract(z, root)
            self.assertEqual(len(records), 2)
            self.assertEqual((root / 'extension/.hidden').read_bytes(), b'hello')
            self.assertEqual((root / 'extension/node_modules/pkg/a.js').read_bytes(), b'world')
            self.assertTrue((root / 'empty').is_dir())

    def test_rejects_unsafe_or_conflicting_paths_before_writing(self):
        cases = [[('../escape', b'bad')], [('/absolute', b'bad')], [('a\\b', b'bad')],
                 [('a/./b', b'bad')], [('a', b'1'), ('a', b'2')],
                 [('a', b'file'), ('a/b', b'bad')], [('C:/a', b'bad')]]
        link = zipfile.ZipInfo('link')
        link.create_system = 3
        link.external_attr = 0o120777 << 16
        cases.append([(link, b'../escape')])
        for entries in cases:
            with self.subTest(entries=entries), tempfile.TemporaryDirectory() as directory, self.archive(entries) as z:
                root = Path(directory)
                with self.assertRaises(ValueError):
                    prepare.extract(z, root)
                self.assertEqual(list(root.iterdir()), [])


class Configs(unittest.TestCase):
    def test_every_pin_has_matching_config(self):
        here = Path(__file__).parent
        if not (here / 'configs').is_dir():  # Docker builder context omits configs
            self.skipTest('configs not present')
        pins = json.loads((here / 'extensions.json').read_text())['extensions']
        self.assertEqual(len(list((here / 'configs').glob('*.yaml'))), len(pins))
        for pin in pins:
            i = pin['id'].lower()
            text = (here / 'configs' / f'{i}.yaml').read_text()
            for line in (f'name: slim-docker-vsix-{i}', f"upstream_version: {pin['version']}",
                         f'  EXTENSION_ID: {i}', f'  IMAGE_NAME: slim-docker-vsix-{i}'):
                self.assertIn(line + '\n', text)


if __name__ == '__main__':
    unittest.main()
