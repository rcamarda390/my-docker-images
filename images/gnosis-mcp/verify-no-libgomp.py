# verify-no-libgomp.py
"""Fail closed if the installed native runtime still requires OpenMP."""

import re
import subprocess
from pathlib import Path

# Query the installed database directly: apt lists have already been deleted.
# Include Pre-Depends and alternatives; reject even an optional libgomp arm.
packages = subprocess.run(
    ["dpkg-query", "-W", "-f=${binary:Package}\t${db:Status-Status}\t${Depends}\t${Pre-Depends}\n"],
    capture_output=True, text=True, check=True,
)
for row in packages.stdout.splitlines():
    package, status, depends, pre_depends = row.split("\t")
    if status != "installed":
        continue
    assert package.split(":")[0] != "libgomp1", "libgomp1 remains installed"
    assert not re.search(
        r"(?<![\w-])libgomp1(?=[:\s,(|]|$)", depends + " " + pre_depends,
    ), (package, depends, pre_depends)
print("Installed Debian packages have no libgomp1 dependency")
assert not list(Path("/usr/lib/x86_64-linux-gnu").glob("libgomp.so*"))
for path in sorted(Path("/usr/local").rglob("*.so*")):
    if not path.is_file():
        continue
    with path.open("rb") as stream:
        if stream.read(4) != b"\x7fELF":
            continue
    result = subprocess.run(["ldd", str(path)], capture_output=True, text=True)
    output = result.stdout + result.stderr
    assert "libgomp" not in output, (path, output)
    assert "not found" not in output, (path, output)
    assert result.returncode == 0, (path, output)
    print(path, output)
print("Installed native dependency closure does not require libgomp")
