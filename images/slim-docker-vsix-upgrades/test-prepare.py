# File: images/slim-docker-vsix-upgrades/test-prepare.py
"""Offline checks: python -I test-prepare.py"""
import io
import runpy
import tempfile
import unittest
import zipfile
from pathlib import Path

P = runpy.run_path(str(Path(__file__).with_name("prepare.py")))


class Semver(unittest.TestCase):
    def test_ranges(self):
        ok = lambda r: P["satisfies"]("1.98.2", r)
        for r in ("^1.80.0", "^1.98.0", "^1.98.2", "~1.98.0", ">=1.74.0", "1.x", "*", "1.98.x",
                  ">=1.90.0 <2.0.0", "^1.200.0 || ^1.98.0", "1.98.2"):
            self.assertTrue(ok(r), r)
        for r in ("^1.99.0", "^1.100.0", "~1.97.0", ">=2.0.0", "<1.98.2", "^2.0.0", "1.99.x"):
            self.assertFalse(ok(r), r)


class Extract(unittest.TestCase):
    def zip(self, names):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            for n in names:
                z.writestr(n, b"x")
        return zipfile.ZipFile(io.BytesIO(b.getvalue()))

    def test_unsafe_rejected(self):
        for bad in ("../evil", "/abs", "a/../../b", "a\\b"):
            with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError, msg=bad):
                P["safe_extract"](self.zip([bad]), Path(d))

    def test_good_extracts_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            files = P["safe_extract"](self.zip(["[Content_Types].xml", "extension/.hidden", "extension/a/b.js"]), Path(d))
            self.assertEqual(len(files), 3)
            self.assertTrue((Path(d) / "extension/.hidden").is_file())


if __name__ == "__main__":
    unittest.main()
