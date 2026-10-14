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
        missing, = module.review([finding], {})
        self.assertEqual(missing['status'], 'UNKNOWN')
        finding['images']['b']['scan_status'] = 'cleared'
        self.assertEqual(list(module.review([finding], tracker)), [])


if __name__ == '__main__':
    unittest.main()
