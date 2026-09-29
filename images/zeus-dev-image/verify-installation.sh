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
check "node 22" 1 bash -c '[[ "$(node --version)" == v22.* ]]'
check "npm" 1 command -v npm
check "git" 1 command -v git
check "docker CLI" 0 command -v docker
check "aws CLI" 1 command -v aws
check "jira python package" 1 python3 -c "import jira"
check "apache-airflow 3.3.2" 1 python3 -c "import airflow; assert airflow.__version__ == \"3.3.2\""
check "Python package dependencies" 1 pip3 check
check "sqlfluff" 1 command -v sqlfluff
check "ruff" 0 command -v ruff
check "pyright" 0 command -v pyright
check "cline CLI" 1 command -v cline
check "claude CLI" 1 command -v claude
check "AgentMemory MCP entry point" 1 test -f /opt/agentmemory/node_modules/@agentmemory/agentmemory/dist/index.mjs
check "AgentMemory CLI" 1 command -v agentmemory
check "AgentMemory MCP" 1 command -v agentmemory-mcp
check "Archify CLI" 1 command -v archify
check "xdg-user-dir" 1 command -v xdg-user-dir
check "GitLab MCP dependencies" 1 test -x /opt/gitlab-mcp-server/node_modules/.bin/tsc

log ""
if [ "$failures" -gt 0 ]; then
    log "$failures required item(s) missing."
    exit 1
fi

log "All required software present."
