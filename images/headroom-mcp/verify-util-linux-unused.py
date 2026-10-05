# verify-util-linux-unused.py
"""Audit the installed Headroom runtime before removing util-linux packages."""

import re
import subprocess
from pathlib import Path

removed = {"util-linux", "mount", "bsdutils", "libmount1", "libblkid1",
           "libsmartcols1", "libuuid1"}
libraries = ("libmount.so", "libblkid.so", "libsmartcols.so", "libuuid.so")
packages = subprocess.check_output(
    ["dpkg-query", "-W", "-f=${binary:Package}\t${db:Status-Status}\t${Depends}\t${Pre-Depends}\n"],
    text=True,
)
for row in packages.splitlines():
    name, status, depends, predepends = row.split("\t")
    name = name.split(":")[0]
    if status != "installed" or name in removed:
        continue
    for dependency in removed:
        assert not re.search(
            rf"(?<![\w-]){re.escape(dependency)}(?=[:\s,(|]|$)",
            depends + " " + predepends,
        ), (name, depends, predepends)

checked = 0
paths = {Path("/bin/dash"), Path("/usr/local/bin/python3.13")}
for root in (Path("/usr/local"), Path("/opt/venv")):
    paths.update(root.rglob("*.so*"))
for path in sorted(paths):
    if not path.is_file():
        continue
    with path.open("rb") as stream:
        if stream.read(4) != b"\x7fELF":
            continue
    result = subprocess.run(["ldd", str(path)], capture_output=True, text=True, check=True)
    output = result.stdout + result.stderr
    assert not any(library in output for library in libraries), (path, output)
    checked += 1
assert checked > 0, "Native dependency audit checked no ELF files"
print(f"No retained Debian dependency or {checked} native ELF closures require util-linux")
