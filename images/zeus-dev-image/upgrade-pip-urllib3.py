#!/usr/bin/env python3
"""upgrade-pip-urllib3.py: vendor urllib3 2.8.0 into pip 26.2.1, retaining pip patches."""
import base64
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import shutil

import pip
import urllib3

assert pip.__version__ == "26.2.1"
assert urllib3.__version__ == "2.8.0"
vendor = Path(pip.__file__).parent / "_vendor"
target = vendor / "urllib3"
assert "'2.7.0'" in (target / "_version.py").read_text()
licenses = {p.name: p.read_bytes() for p in target.glob("LICENSE*")}
shutil.rmtree(target)
shutil.copytree(Path(urllib3.__file__).parent, target, ignore=shutil.ignore_patterns("__pycache__"))
for name, content in licenses.items():
    (target / name).write_bytes(content)

# Preserve the three urllib3 vendoring patches from pip's 26.2.1 release.
# https://github.com/pypa/pip/tree/26.2.1/tools/vendoring/patches
def replace(file, before, after):
    content = file.read_text()
    assert content.count(before) == 1, (file, "upstream patch context changed")
    file.write_text(content.replace(before, after))

response = target / "response.py"
content = response.read_text()
content, count = re.subn(r"try:\n    try:\n        import brotlicffi as brotli.*?\nexcept ImportError:\n    brotli = None", "brotli = None", content, count=1, flags=re.S)
assert count == 1
response.write_text(content)
request = target / "util/request.py"
content = request.read_text()
content, count = re.subn(r"try:\n    try:\n        import brotlicffi as _unused_module_brotli.*?\nelse:\n    ACCEPT_ENCODING \+= \",br\"\n", "", content, count=1, flags=re.S)
assert count == 1
request.write_text(content)
emscripten = target / "contrib/emscripten/__init__.py"
replace(emscripten, "import urllib3.connection", "import pip._vendor.urllib3.connection as urllib3_connection")
content = emscripten.read_text().replace("urllib3.connection.", "urllib3_connection.")
emscripten.write_text(content)
replace(target / "contrib/pyopenssl.py", "        import urllib3.contrib.pyopenssl\n        urllib3.contrib.pyopenssl.inject_into_urllib3()", "        import pip._vendor.urllib3.contrib.pyopenssl as pyopenssl\n        pyopenssl.inject_into_urllib3()")

# Record the version of the actual replacement code, including SBOM references.
bom_file = vendor / "bom.cdx.json"
bom = json.loads(bom_file.read_text().replace("pkg:pypi/urllib3@2.7.0", "pkg:pypi/urllib3@2.8.0"))
components = [c for c in bom["components"] if c["name"] == "urllib3"]
assert len(components) == 1 and components[0]["version"] == "2.7.0"
components[0]["version"] = "2.8.0"
bom_file.write_text(json.dumps(bom, indent=2) + "\n")
replace(vendor / "vendor.txt", "urllib3==2.7.0", "urllib3==2.8.0")

# Keep pip's installation record accurate so a later pip upgrade can uninstall it.
dist = importlib.metadata.distribution("pip")
record = Path(dist.locate_file(next(p for p in dist.files if str(p).endswith(".dist-info/RECORD"))))
site = Path(dist.locate_file(""))
with record.open(newline="") as stream:
    rows = list(csv.reader(stream))
changed = list(target.rglob("*")) + [bom_file, vendor / "vendor.txt"]
changed = [p for p in changed if p.is_file()]
names = {p.relative_to(site).as_posix() for p in changed}
rows = [r for r in rows if not r[0].startswith("pip/_vendor/urllib3/") and r[0] not in names]
for file in changed:
    data = file.read_bytes()
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    rows.append([file.relative_to(site).as_posix(), "sha256=" + digest, str(len(data))])
with record.open("w", newline="") as stream:
    csv.writer(stream).writerows(rows)
print("pip 26.2.1 now vendors urllib3 2.8.0 with upstream pip compatibility patches")
