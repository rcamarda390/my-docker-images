import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('image_removals', Path(__file__).with_name('image_removals.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

PACKAGES = {
    # name: (depends, provides, files)
    'libc6': ('', '', ['/usr/lib/libc.so.6']),
    'libacl1': ('libc6', '', ['/usr/lib/libacl.so.1']),
    'coreutils': ('libc6, libacl1', '', ['/usr/bin/env', '/usr/bin/cat', '/usr/share/doc/coreutils']),
    'tar': ('libc6, libacl1', '', ['/usr/bin/tar']),
    'dpkg': ('libc6, tar', '', ['/usr/bin/dpkg']),
    'base-tool': ('coreutils', '', ['/usr/bin/base-tool']),
    'either': ('coreutils | busybox', '', ['/usr/bin/either']),
    'busybox': ('libc6', '', ['/usr/bin/busybox']),
    'app': ('libc6', '', ['/usr/bin/app', '/usr/share/shared']),
    'pager': ('libc6', '', ['/usr/bin/pager']),
}


def build_root(root, packages=PACKAGES):
    dpkg = Path(root, 'var/lib/dpkg')
    (dpkg / 'info').mkdir(parents=True)
    stanzas = []
    for name, (depends, provides, files) in packages.items():
        fields = [f'Package: {name}', 'Status: install ok installed', 'Version: 1', 'Architecture: amd64']
        if depends:
            fields.append(f'Depends: {depends}')
        if provides:
            fields.append(f'Provides: {provides}')
        stanzas.append('\n'.join(fields))
        (dpkg / 'info' / f'{name}.list').write_text('\n'.join(['/.'] + files) + '\n')
        (dpkg / 'info' / f'{name}.md5sums').write_text('')
        for path in files:
            target = Path(root, path.lstrip('/'))
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text(name)
    (dpkg / 'status').write_text('\n\n'.join(stanzas) + '\n\n')


def write_manifest(root, packages, paths=()):
    manifest = Path(root, 'removals.yaml')
    lines = ['schema_version: 1', 'image: test', 'packages:']
    for name, extra in packages:
        lines += [f'  - name: {name}', '    category: unused-runtime', '    reason: unused', '    evidence: [e]'] + extra
    lines.append('paths:' if paths else 'paths: []')
    for path in paths:
        lines += [f'  - path: {path}', '    category: unused-runtime', '    reason: unused', '    evidence: [e]']
    manifest.write_text('\n'.join(lines) + '\n')
    return str(manifest)


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        build_root(self.root)
        self.packages, _ = module.parse_status(os.path.join(self.root, 'var/lib/dpkg/status'))

    def tearDown(self):
        self.tmp.cleanup()

    def test_closure_pulls_dependents_but_keeps_satisfied_alternatives(self):
        doomed = module.closure(self.packages, {'coreutils'})
        self.assertEqual(doomed, {'coreutils', 'base-tool'})  # either still has busybox

    def test_closure_is_transitive(self):
        self.assertEqual(module.closure(self.packages, {'tar'}), {'tar', 'dpkg'})

    def test_undeclared_dependents_fail_with_names(self):
        manifest = write_manifest(self.root, [('coreutils', [])])
        with self.assertRaises(SystemExit):
            module.apply(manifest, self.root, '/etc/image-removals.json', 'full', False, check_elf=False)
        self.assertTrue(Path(self.root, 'usr/bin/cat').exists())

    def test_apply_removes_files_records_and_audits(self):
        manifest = write_manifest(self.root, [('coreutils', []), ('base-tool', [])],
                                  paths=['/usr/share/shared'])
        report = module.apply(manifest, self.root, '/etc/image-removals.json', 'full', False, check_elf=False)
        self.assertEqual([p['name'] for p in report['removed_packages']], ['base-tool', 'coreutils'])
        self.assertFalse(Path(self.root, 'usr/bin/cat').exists())
        self.assertFalse(Path(self.root, 'var/lib/dpkg/info/coreutils.list').exists())
        self.assertTrue(Path(self.root, 'usr/bin/either').exists())
        remaining, _ = module.parse_status(os.path.join(self.root, 'var/lib/dpkg/status'))
        self.assertNotIn('coreutils', remaining)
        self.assertEqual(module.unsatisfied(remaining, set()), [])
        self.assertFalse(Path(self.root, 'usr/share/shared').exists())
        written = json.loads(Path(self.root, 'etc/image-removals.json').read_text())
        self.assertEqual(written['audit']['unsatisfied_after'], 0)
        module.verify(self.root, '/etc/image-removals.json')

    def test_baseline_keeps_packages_that_require_a_carry(self):
        manifest = write_manifest(self.root, [('pager', ['    requires_carry: true'])])
        report = module.apply(manifest, self.root, '/etc/image-removals.json', 'baseline', False, check_elf=False)
        self.assertEqual(report['removed_packages'], [])
        self.assertEqual(report['kept_for_baseline'][0]['name'], 'pager')
        self.assertTrue(Path(self.root, 'usr/bin/pager').exists())

    def test_removal_needs_no_external_commands_and_removes_directories(self):
        manifest = write_manifest(self.root, [('coreutils', []), ('base-tool', [])],
                                  paths=['/usr/share/dir-to-drop'])
        directory = Path(self.root, 'usr/share/dir-to-drop/nested')
        directory.mkdir(parents=True)
        (directory / 'file').write_text('x')

        def forbidden(*args, **kwargs):
            raise AssertionError(f'external command used during removal: {args}')

        original = module.subprocess.run
        module.subprocess.run = forbidden
        try:
            module.apply(manifest, self.root, '/etc/image-removals.json', 'full', False, check_elf=False)
        finally:
            module.subprocess.run = original
        self.assertFalse(Path(self.root, 'usr/share/dir-to-drop').exists())

    def test_runtime_library_in_closure_blocks_removal(self):
        manifest = write_manifest(self.root, [('coreutils', []), ('base-tool', [])])
        elf = Path(self.root, 'opt/venv/lib/native.so')
        elf.parent.mkdir(parents=True)
        elf.write_bytes(b'\x7fELF')
        # Stand in for ldd: the native module resolves a library coreutils would delete.
        fake = lambda path: ({'/usr/bin/cat'}, [])
        manifest_data = Path(manifest).read_text() + 'runtime_roots: [/opt/venv]\n'
        Path(manifest).write_text(manifest_data)
        with self.assertRaises(SystemExit):
            module.apply(manifest, self.root, '/etc/image-removals.json', 'full', False, ldd=fake)
        self.assertTrue(Path(self.root, 'usr/bin/cat').exists())

    def test_entrypoint_using_a_removed_command_blocks_removal(self):
        script = Path(self.root, 'usr/local/bin/entry')
        script.parent.mkdir(parents=True)
        script.write_text('#!/bin/sh\n# env is only a comment word\nexec cat /etc/hosts\n')
        manifest = write_manifest(self.root, [('coreutils', []), ('base-tool', [])])
        Path(manifest).write_text(Path(manifest).read_text() + 'entrypoints: [/usr/local/bin/entry]\n')
        with self.assertRaises(SystemExit):
            module.apply(manifest, self.root, '/etc/image-removals.json', 'full', False, ldd=lambda p: (set(), []))

    def test_manifest_requires_reason_and_evidence(self):
        bad = Path(self.root, 'bad.yaml')
        bad.write_text('schema_version: 1\npackages:\n  - name: x\n    category: unused-runtime\n')
        with self.assertRaises(SystemExit):
            module.load_manifest(str(bad))


if __name__ == '__main__':
    unittest.main()
