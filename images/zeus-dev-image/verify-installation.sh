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
check "Docker Compose 5.6.0" 1 bash -c '[[ "$(docker compose version --short)" == 5.6.0 ]]'
check "Docker Compose checksum" 1 bash -c 'printf "%s  %s\n" 40343e21ca777173e69cff5dbafeb37c6f81f3b0d57d9e597f036e95eb63e76a /usr/libexec/docker/cli-plugins/docker-compose | sha256sum -c -'
check "Compose containerd 2.4.1" 1 grep -Eq 'github.com/containerd/containerd/v2[[:space:]]+v2.4.1' /usr/local/share/zeus/compose-build-info.txt
check "Compose config compatibility" 1 bash -c 'printf "services:\n  smoke:\n    image: busybox\n" | docker compose -f - config --quiet'
check "Buildx plugin absent" 1 test ! -e /usr/libexec/docker/cli-plugins/docker-buildx
check "aws CLI" 1 command -v aws
check "jira python package" 1 python3 -c "import jira"
check "apache-airflow 3.3.2" 1 python3 -c "import airflow; assert airflow.__version__ == \"3.3.2\""
check "Python package dependencies" 1 pip3 check
check "msgpack 1.2.3" 1 python3 -c "import msgpack; assert msgpack.__version__ == \"1.2.3\""
check "setuptools security version" 1 python3 -c "import setuptools; assert tuple(map(int, setuptools.__version__.split(\".\")[:2])) >= (80, 10)"
check "sqlfluff" 1 command -v sqlfluff
check "ruff" 0 command -v ruff
check "pyright" 0 command -v pyright
check "cline CLI" 1 command -v cline
check "Cline undici 6.28.1" 1 node -e 'const p=require("/opt/cline/package-lock.json").packages; const f=Object.entries(p).filter(([k])=>k.endsWith("node_modules/undici")); if (!f.length || f.some(([,v])=>v.version !== "6.28.1")) process.exit(1)'
check "Cline Git clone/status compatibility" 1 node -e 'const {simpleGit:git}=require("/opt/cline/node_modules/simple-git"); const fs=require("node:fs"); const os=require("node:os"); const path=require("node:path"); const dir=fs.mkdtempSync(path.join(os.tmpdir(),"zeus-git-")); (async()=>{try{const src=path.join(dir,"source"); fs.mkdirSync(src); await git(src).init(); await git(dir).clone(src,"clone"); const status=await git(path.join(dir,"clone")).status(); if(status.files.length) throw new Error("unexpected dirty clone");}finally{fs.rmSync(dir,{recursive:true,force:true});}})().catch(e=>{console.error(e);process.exit(1)})'
check "claude CLI" 1 command -v claude
check "Bifrost update checks disabled" 1 test "${BIFROST_NO_UPDATE_CHECK:-}" = 1
check "Bifrost CLI help" 1 bifrost --help
check "Bifrost CLI source-build checksum" 1 bash -c 'cd /usr/local/bin && sha256sum -c /usr/local/share/zeus/bifrost.sha256'
check "Bifrost Go 1.26.6" 1 grep -q go1.26.6 /usr/local/share/zeus/bifrost-build-info.txt
check "AgentMemory MCP entry point" 1 test -f /opt/agentmemory/node_modules/@agentmemory/agentmemory/dist/index.mjs
check "AgentMemory CLI" 1 command -v agentmemory
check "AgentMemory MCP" 1 command -v agentmemory-mcp
check "Archify CLI" 1 command -v archify
check "xdg-user-dir" 1 command -v xdg-user-dir
check "GitLab MCP dependencies" 1 test -x /opt/gitlab-mcp-server/node_modules/.bin/tsc
check "TypeScript 6.0.3" 1 node -e 'if (require("/opt/gitlab-mcp-server/node_modules/typescript/package.json").version !== "6.0.3") process.exit(1)'

check "Xray fixed package versions" 1 python3 /usr/local/bin/verify-security.py

log ""
if [ "$failures" -gt 0 ]; then
    log "$failures required item(s) missing."
    exit 1
fi

log "All required software present."
