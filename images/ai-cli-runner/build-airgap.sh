#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
out="$(pwd)/dist"
mkdir -p "$out"
# Use the same integrity-checked packages as the runtime image.
npm ci --ignore-scripts --no-audit --no-fund
cp package.json package-lock.json "$out/"
node <<'NODE'
const fs = require('node:fs');
const crypto = require('node:crypto');
const {execFileSync} = require('node:child_process');
const lock = require('./package-lock.json');
for (const [name, label] of [
  ['@anthropic-ai/claude-code-linux-x64', 'claude-code'],
  ['@cline/cli-linux-x64', 'cline'],
]) {
  const pkg = lock.packages[`node_modules/${name}`];
  const packed = JSON.parse(execFileSync('npm', ['pack', pkg.resolved,
    '--ignore-scripts', '--json', '--pack-destination', 'dist'], {encoding:'utf8'}))[0];
  const bytes = fs.readFileSync(`dist/${packed.filename}`);
  const [algorithm, expected] = pkg.integrity.split('-');
  if (crypto.createHash(algorithm).update(bytes).digest('base64') !== expected)
    throw new Error(`Registry integrity mismatch: ${name}`);
  execFileSync('tar', ['-czf', `dist/${label}-${pkg.version}-linux-x64.tar.gz`,
    '-C', `node_modules/${name}`, '.']);
}
NODE
# Preserve the published Cline launcher as well as its platform payload.
cline_version=$(node -p "require('./package.json').dependencies['@cline/cli-linux-x64']")
npm pack "cline@$cline_version" --ignore-scripts --pack-destination "$out"
(
  cd "$out"
  for archive in *.tgz *.tar.gz; do
    sha256sum "$archive" > "$archive.sha256"
    sha256sum -c "$archive.sha256"
  done
)
