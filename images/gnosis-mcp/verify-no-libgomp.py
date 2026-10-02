# verify-no-libgomp.py
"""Record native dependency closure before deleting build-time tools."""

import subprocess
from pathlib import Path

# The runtime installs no libgomp1 now. Record Debian's installed reverse
# dependencies while apt-cache/ldd still exist, then inspect every installed
# Python/native shared object, including NumPy's bundled BLAS libraries.
reverse = subprocess.run(
    ["apt-cache", "rdepends", "--installed", "libgomp1"],
    capture_output=True, text=True,
)
print(reverse.stdout, reverse.stderr)
state = subprocess.run(
    ["dpkg-query", "-W", "-f=${db:Status-Status}", "libgomp1"],
    capture_output=True, text=True,
)
assert state.stdout != "installed", "libgomp1 remains installed"
assert not list(Path("/usr/lib/x86_64-linux-gnu").glob("libgomp.so*"))
for path in sorted(Path("/usr/local").rglob("*.so*")):
    if not path.is_file() or path.open("rb").read(4) != b"\x7fELF":
        continue
    result = subprocess.run(["ldd", str(path)], capture_output=True, text=True)
    output = result.stdout + result.stderr
    assert "libgomp" not in output, (path, output)
    assert "not found" not in output, (path, output)
    assert result.returncode == 0, (path, output)
    print(path, output)
print("Installed native dependency closure does not require libgomp")
