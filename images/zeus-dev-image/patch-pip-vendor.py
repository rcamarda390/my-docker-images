#!/usr/bin/env python3
"""patch-pip-vendor.py SRC: vendor msgpack 1.2.3 into pip 26.2.1, drop its pkg_resources.

SRC is an installed msgpack 1.2.3 package directory. Only its pure-Python
modules are copied, matching pip's own vendoring (no C extension).
"""
import base64
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys

import pip

assert pip.__version__ == "26.2.1"
src = Path(sys.argv[1])
assert '"1.2.3"' in (src / "__init__.py").read_text()
vendor = Path(pip.__file__).parent / "_vendor"
target = vendor / "msgpack"
assert '"1.1.2"' in (target / "__init__.py").read_text()

# pip's msgpack 1.1.2 is byte-identical to upstream's pure-Python modules.
for name in ("__init__.py", "exceptions.py", "ext.py", "fallback.py"):
    shutil.copyfile(src / name, target / name)
shutil.rmtree(target / "__pycache__", ignore_errors=True)

# pkg_resources (setuptools 70.3.0) is only used by pip's opt-in legacy
# metadata backend, which Python 3.12 never selects by default.
removed = vendor / "pkg_resources"
removed_files = [p for p in removed.rglob("*") if p.is_file()]
assert removed_files
shutil.rmtree(removed)

bom_file = vendor / "bom.cdx.json"
bom = json.loads(bom_file.read_text().replace("pkg:pypi/msgpack@1.1.2", "pkg:pypi/msgpack@1.2.3"))
bom["components"] = [c for c in bom["components"] if c["name"] != "setuptools"]
msgpack = [c for c in bom["components"] if c["name"] == "msgpack"]
assert len(msgpack) == 1
msgpack[0]["version"] = "1.2.3"
bom_file.write_text(json.dumps(bom, indent=2) + "\n")
vendor_txt = vendor / "vendor.txt"
text = vendor_txt.read_text()
assert "msgpack==1.1.2" in text and "setuptools==70.3.0" in text
vendor_txt.write_text(text.replace("msgpack==1.1.2", "msgpack==1.2.3").replace("setuptools==70.3.0\n", ""))

# Keep pip's installation record accurate so a later pip upgrade can uninstall it.
dist = importlib.metadata.distribution("pip")
record = Path(dist.locate_file(next(p for p in dist.files if str(p).endswith(".dist-info/RECORD"))))
site = Path(dist.locate_file(""))
with record.open(newline="") as stream:
    rows = list(csv.reader(stream))
changed = [p for p in target.rglob("*") if p.is_file()] + [bom_file, vendor_txt]
names = {p.relative_to(site).as_posix() for p in changed}
dropped = {p.relative_to(site).as_posix() for p in removed_files}
rows = [r for r in rows if r[0] not in names and r[0] not in dropped
        and not r[0].startswith("pip/_vendor/pkg_resources/")
        and not r[0].startswith("pip/_vendor/msgpack/__pycache__/")]
for file in changed:
    data = file.read_bytes()
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    rows.append([file.relative_to(site).as_posix(), "sha256=" + digest, str(len(data))])
with record.open("w", newline="") as stream:
    csv.writer(stream).writerows(rows)
print("pip 26.2.1 now vendors msgpack 1.2.3 and no pkg_resources/setuptools")
