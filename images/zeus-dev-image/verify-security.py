#!/usr/bin/env python3
"""verify-security.py: check fixed Python and npm versions in the final image."""
import ctypes
import importlib.metadata
import json
from pathlib import Path
import subprocess
import tempfile

from packaging.version import Version

# Xray's pcre2-syntax rows refer to the source RPM's actual regex library.
# Check both RPM ownership/version and the loaded runtime bytes.
for package in ("pcre2", "pcre2-syntax"):
    version = subprocess.check_output(["rpm", "-q", "--qf", "%{VERSION}", package], text=True)
    assert version == "10.49", (package, version)
posix = ctypes.CDLL("libpcre2-posix.so.3")
for symbol in ("pcre2_regcomp", "pcre2_regexec", "pcre2_regerror", "pcre2_regfree"):
    assert getattr(posix, symbol)
pcre2 = ctypes.CDLL("libpcre2-8.so.0")
pcre2.pcre2_config_8.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
pcre2.pcre2_config_8.restype = ctypes.c_int
version_buffer = ctypes.create_string_buffer(64)
assert pcre2.pcre2_config_8(11, version_buffer) > 0
assert version_buffer.value.startswith(b"10.49 "), version_buffer.value
for option in (1, 9):  # PCRE2_CONFIG_JIT, PCRE2_CONFIG_UNICODE
    enabled = ctypes.c_uint32()
    assert pcre2.pcre2_config_8(option, ctypes.byref(enabled)) == 0
    assert enabled.value == 1, (option, enabled.value)
subprocess.run(["grep", "-P", "^[a-z]+[0-9]+$"], input="zeus123\n", text=True, check=True)
with tempfile.TemporaryDirectory(prefix="zeus-pcre2-") as directory:
    (Path(directory) / "sample.txt").write_text("zeus123\n")
    subprocess.run(["git", "grep", "--no-index", "-P", "^[a-z]+[0-9]+$", "--", "sample.txt"],
                   cwd=directory, check=True)
with tempfile.TemporaryDirectory(prefix="zeus-dnf-") as directory:
    subprocess.run(["dnf", "--setopt=cachedir=" + directory, "--setopt=logdir=" + directory,
                    "--setopt=persistdir=" + directory, "check"], check=True)
print("PCRE2 10.49: RPMs, loaded ABI, JIT, Unicode, grep, Git and DNF OK")

from pip._vendor import urllib3 as pip_urllib3
from pip._vendor.requests.adapters import PoolManager
from pip._internal.network.session import PipSession

assert pip_urllib3.__version__ == "2.8.0"
assert PoolManager is pip_urllib3.PoolManager
with PipSession() as session:
    assert session.adapters["https://"].poolmanager.__class__ is PoolManager
print("Main pip vendored urllib3 2.8.0 transport OK")

python_fixes = {"msgpack": "1.2.3", "setuptools": "80.10.0", "urllib3": "2.8.0",
                "PyJWT": "2.15.0", "Mako": "1.4.2", "Werkzeug": "3.1.9",
                "fsspec": "2026.6.0", "asyncssh": "2.24.1", "multidict": "6.9.1"}
for name, minimum in python_fixes.items():
    installed = importlib.metadata.version(name)
    assert Version(installed) >= Version(minimum), (name, installed, minimum)
    print(f"Python {name}: {installed}")

# AWS CLI has its own pip and urllib3; global upgrades do not reach this venv.
subprocess.run(["/opt/aws-cli/bin/python", "-c", "import importlib.metadata as m; "
                "assert m.version('pip') == '26.2.1'; "
                "assert m.version('urllib3') == '2.8.0'; "
                "from pip._vendor import urllib3; "
                "assert urllib3.__version__ == '2.8.0'; "
                "from pip._vendor.requests.adapters import PoolManager; "
                "assert PoolManager is urllib3.PoolManager; "
                "print('AWS CLI pip/urllib3 versions OK')"], check=True)
subprocess.run(["/opt/aws-cli/bin/pip", "check"], check=True)

npm_fixes = {"axios": "1.20.0", "simple-git": "4.0.1",
             "@simple-git/argv-parser": "2.0.1", "@modelcontextprotocol/sdk": "1.32.0",
             "@hono/node-server": "2.1.3", "@opentelemetry/core": "2.8.0"}
provider_fixes = {3: "3.0.28", 4: "4.0.33", 5: "5.0.1"}
seen = set()
for root in ["/opt/cline", "/opt/agentmemory", "/opt/agentmemory-mcp", "/opt/gitlab-mcp-server"]:
    packages = json.loads((Path(root) / "package-lock.json").read_text())["packages"]
    for path, package in packages.items():
        name = path.rsplit("node_modules/", 1)[-1]
        minimum = npm_fixes.get(name)
        if name == "@ai-sdk/provider-utils":
            minimum = provider_fixes[Version(package["version"]).major]
        if minimum:
            installed = package["version"]
            assert Version(installed) >= Version(minimum), (root, path, installed, minimum)
            # Check installed bytes as well as the resolver's lockfile.
            actual = json.loads((Path(root) / path / "package.json").read_text())["version"]
            assert actual == installed, (root, path, actual, installed)
            seen.add(name)
            print(f"npm {root}/{path}: {installed}")
assert set(npm_fixes).issubset(seen), set(npm_fixes) - seen
global_root = subprocess.check_output(["npm", "root", "-g"], text=True).strip()
claude = json.loads((Path(global_root) / "@anthropic-ai/claude-code/package.json").read_text())
assert Version(claude["version"]) >= Version("2.1.260"), claude["version"]
print(f"Claude Code CLI: {claude['version']}")
