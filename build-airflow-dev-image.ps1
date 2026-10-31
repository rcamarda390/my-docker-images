# build-airflow-dev-image.ps1
# ------------------------------------------------------------
# Builds a custom Airflow development image using Docker Desktop.
#
# Summary of what gets installed:
#
# Base:
#   - apache/airflow:2.9.3-python3.11
#
# OS packages:
#   - git
#   - curl, wget, unzip, jq, less, vim, nano
#   - openssh-client, ca-certificates, gnupg, lsb-release, tzdata
#   - procps, iputils-ping, netcat-openbsd
#   - build-essential, gcc, g++, make
#   - libpq-dev
#   - postgresql-client (psql for Redshift)
#   - docker.io (Docker CLI inside container)
#
# AWS:
#   - awscli v2
#
# Python dev tools:
#   - ruff, black, isort, pytest, mypy, ipython
#
# Redshift drivers:
#   - redshift-connector
#   - psycopg2-binary
#   - sqlalchemy
#   - sqlalchemy-redshift
#
# Output image:
#   - airflow-dev:2.9.3
# Build from power shell
# docker run --rm airflow-dev:2.9.3 cat /etc/os-release
# ------------------------------------------------------------

param (
    [string]$ImageTag = "airflow-dev:2.9.3",
    [string]$AirflowBase = "apache/airflow:2.9.3-python3.11"
)

$ErrorActionPreference = "Stop"

# Verify Docker is available
docker version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker is not available (docker version exited $LASTEXITCODE)."
    exit 1
}

# Dockerfile.airflow-dev is checked in next to this script; anchor paths to it
$dockerfilePath = Join-Path $PSScriptRoot "Dockerfile.airflow-dev"

# Build image
docker build `
    --build-arg "AIRFLOW_BASE=$AirflowBase" `
    -f $dockerfilePath `
    -t $ImageTag `
    $PSScriptRoot
if ($LASTEXITCODE -ne 0) {
    Write-Error "docker build failed (exit $LASTEXITCODE)."
    exit 1
}

Write-Host ""
Write-Host "Built image: $ImageTag"
