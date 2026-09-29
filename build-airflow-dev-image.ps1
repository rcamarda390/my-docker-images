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
    [string]$AirflowBase = "apache/airflow:latest"
)

$ErrorActionPreference = "Stop"

# Verify Docker is available
docker version | Out-Null

# Create Dockerfile
$dockerfilePath = "Dockerfile.airflow-dev"

@"
FROM $AirflowBase

USER root

RUN apt-get update && apt-get install -y --no-install-recommends `
    git `
    curl `
    wget `
    unzip `
    jq `
    less `
    vim `
    nano `
    openssh-client `
    ca-certificates `
    gnupg `
    lsb-release `
    tzdata `
    procps `
    iputils-ping `
    netcat-openbsd `
    build-essential `
    gcc `
    g++ `
    make `
    libpq-dev `
    postgresql-client `
    docker.io `
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# AWS CLI v2
RUN curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip `
    && unzip -q /tmp/awscliv2.zip -d /tmp `
    && /tmp/aws/install `
    && rm -rf /tmp/aws /tmp/awscliv2.zip

# Python dev + Redshift tooling
RUN pip install --no-cache-dir `
    ruff `
    black `
    isort `
    pytest `
    mypy `
    ipython `
    redshift-connector `
    psycopg2-binary `
    sqlalchemy `
    sqlalchemy-redshift

RUN usermod -aG docker airflow || true

USER airflow
"@ | Set-Content -Encoding UTF8 $dockerfilePath

# Build image
docker build `
    -f $dockerfilePath `
    -t $ImageTag `
    .

Write-Host ""
Write-Host "Built image: $ImageTag"
