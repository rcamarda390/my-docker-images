#!/bin/bash
# Verify the public software layer; fail if a required tool is missing.
set -u

failures=0

log() {
    printf '%s\n' "$1"
}

# check NAME REQUIRED(0|1) COMMAND...
check() {
    name=$1
    required=$2
    shift 2
    output=$("$@" 2>&1)
    status=$?
    if [ "$status" -eq 0 ]; then
        log "OK   $name"
        return 0
    fi
    if [ "$required" = "1" ]; then
        log "FAIL $name (required)"
        failures=$((failures + 1))
    else
        log "WARN $name (optional, not installed)"
    fi
    [ -z "$output" ] || log "$output"
    return 1
}

log "=== zeus-dev-image installation verification ==="

check "python3 3.12" 1 python3 -c "import sys; assert sys.version_info[:2] == (3, 12)"
check "pip3" 1 command -v pip3
check "pip 26.2.1 vendored assessment" 1 python3 -c '
import json
from pathlib import Path
import pip
assert pip.__version__ == "26.2.1"
vendor = Path(pip.__file__).parent / "_vendor"
components = {item["name"]: item.get("version") for item in json.loads((vendor / "bom.cdx.json").read_text())["components"]}
assert components["msgpack"] == "1.1.2"
assert components["setuptools"] == "70.3.0"
assert not (vendor / "setuptools" / "package_index.py").exists()
assert not list((vendor / "msgpack").glob("*cmsgpack*"))
'
check "node 22" 1 bash -c '[[ "$(node --version)" == v22.* ]]'
check "npm" 1 command -v npm
check "git" 1 command -v git
check "docker CLI" 1 docker --version
check "docker exec command" 1 docker exec --help
check "Buildx plugin absent" 1 test ! -e /usr/libexec/docker/cli-plugins/docker-buildx
check "aws CLI" 1 command -v aws
check "jira python package" 1 python3 -c "import jira"
check "apache-airflow 3.3.2" 1 python3 -c "import airflow; assert airflow.__version__ == \"3.3.2\""
check "Python package dependencies" 1 pip3 check
check "msgpack 1.2.2" 1 python3 -c "import msgpack; assert msgpack.__version__ == \"1.2.2\""
check "setuptools security version" 1 python3 -c "import setuptools; assert tuple(map(int, setuptools.__version__.split(\".\")[:2])) >= (78, 1)"
check "sqlfluff" 1 command -v sqlfluff
check "ruff" 0 command -v ruff
check "pyright" 0 command -v pyright
check "cline CLI" 1 command -v cline
check "Cline undici 6.28.1" 1 node -e 'const p=require("/opt/cline/package-lock.json").packages; const f=Object.entries(p).filter(([k])=>k.endsWith("node_modules/undici")); if (!f.length || f.some(([,v])=>v.version !== "6.28.1")) process.exit(1)'
check "claude CLI" 1 command -v claude
check "Bifrost update checks disabled" 1 test "${BIFROST_NO_UPDATE_CHECK:-}" = 1
check "Bifrost CLI help" 1 bifrost --help
check "Bifrost CLI 0.10.6 checksum" 1 bash -c 'printf "%s  %s\n" 0f162f1e1de7148251e722bcfaddd981e4798d5391b24808cacc08d0b5a4c886 /usr/local/bin/bifrost | sha256sum -c -'
check "AgentMemory MCP entry point" 1 test -f /opt/agentmemory/node_modules/@agentmemory/agentmemory/dist/index.mjs
check "AgentMemory CLI" 1 command -v agentmemory
check "AgentMemory MCP" 1 command -v agentmemory-mcp
check "Archify CLI" 1 command -v archify
check "xdg-user-dir" 1 command -v xdg-user-dir
check "GitLab MCP dependencies" 1 test -x /opt/gitlab-mcp-server/node_modules/.bin/tsc
check "TypeScript 6.0.3" 1 node -e 'if (require("/opt/gitlab-mcp-server/node_modules/typescript/package.json").version !== "6.0.3") process.exit(1)'

log ""
if [ "$failures" -gt 0 ]; then
    log "$failures required item(s) missing."
    exit 1
fi

log "All required software present."
