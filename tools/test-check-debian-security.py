import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('security_check', Path(__file__).with_name('check-debian-security.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReviewTests(unittest.TestCase):
    def test_suite_status_missing_record_and_pending_sibling(self):
        finding = {'source_package': 'glibc', 'cve': 'CVE-example', 'suite': 'trixie',
                   'images': {'a': {'scan_status': 'cleared'}, 'b': {'scan_status': 'pending'}}}
        tracker = {'glibc': {'CVE-example': {'releases': {
            'sid': {'status': 'resolved', 'fixed_version': '3'},
            'trixie': {'status': 'open', 'nodsa': 'Minor issue'}}}}}
        row, = module.review([finding], tracker)
        self.assertEqual(row['status'], 'open')
        self.assertIsNone(row['fixed_version'])
        self.assertEqual(row['no_dsa'], 'Minor issue')
        self.assertEqual(row['replacement_candidates'], [{'suite': 'sid', 'fixed_version': '3'}])
        missing, = module.review([finding], {})
        self.assertEqual(missing['status'], 'UNKNOWN')
        self.assertEqual(missing['replacement_candidates'], [])
        finding['suite'] = None
        upstream, = module.review([finding], tracker)
        self.assertEqual(upstream['status'], 'UPSTREAM_REVIEW')
        self.assertEqual(upstream['replacement_candidates'], [])
        finding['images']['b']['scan_status'] = 'cleared'
        self.assertEqual(list(module.review([finding], tracker)), [])

    def test_replacement_requires_an_actual_fixed_release(self):
        finding = {'source_package': 'pkg', 'cve': 'CVE-example', 'suite': 'trixie',
                   'images': {'a': {'scan_status': 'pending'}}}
        for status, version in [('open', '3'), ('resolved', '0'),
                                ('resolved', None), ('resolved', '')]:
            with self.subTest(status=status, version=version):
                tracker = {'pkg': {'CVE-example': {'releases': {
                    'sid': {'status': status, 'fixed_version': version}}}}}
                row, = module.review([finding], tracker)
                self.assertEqual(row['replacement_candidates'], [])


if __name__ == '__main__':
    unittest.main()
