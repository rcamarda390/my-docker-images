#!/usr/bin/env python3
"""verify-security.py: check fixed Python and npm versions in the final image."""
import importlib.metadata
import json
from pathlib import Path
import subprocess

from packaging.version import Version

from pip._vendor import urllib3 as pip_urllib3
from pip._vendor.requests.adapters import PoolManager
from pip._internal.network.session import PipSession

assert pip_urllib3.__version__ == "2.8.0"
assert PoolManager is pip_urllib3.PoolManager
with PipSession() as session:
    assert session.adapters["https://"].poolmanager.__class__ is PoolManager
print("Main pip vendored urllib3 2.8.0 transport OK")

python_fixes = {"msgpack": "1.2.3", "setuptools": "80.10.0", "urllib3": "2.8.0",
                "PyJWT": "2.15.0", "Mako": "1.4.2", "Werkzeug": "3.1.9"}
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
             "@simple-git/argv-parser": "2.0.1", "@modelcontextprotocol/sdk": "1.31.0",
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
