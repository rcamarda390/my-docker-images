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
# Preserve the published Cline launcher as well as its platform payload. The
# launcher is not in package-lock.json, so its bytes are checked against the
# registry's dist.integrity for that exact version instead.
cline_version=$(node -p "require('./package.json').dependencies['@cline/cli-linux-x64']")
cline_launcher=$(npm pack "cline@$cline_version" --ignore-scripts --json --pack-destination "$out" \
  | node -p 'JSON.parse(require("fs").readFileSync(0, "utf8"))[0].filename')
node - "$out/$cline_launcher" "cline@$cline_version" <<'NODE'
const fs = require('node:fs');
const crypto = require('node:crypto');
const {execFileSync} = require('node:child_process');
const [file, spec] = process.argv.slice(2);
const expected = execFileSync('npm', ['view', spec, 'dist.integrity'], {encoding: 'utf8'}).trim();
const actual = 'sha512-' + crypto.createHash('sha512').update(fs.readFileSync(file)).digest('base64');
if (actual !== expected) throw new Error(`Cline launcher integrity mismatch: ${spec}`);
NODE
# Sidecars for transfer; verify them on the receiving side. Not a self-check.
(
  cd "$out"
  for archive in *.tgz *.tar.gz; do
    sha256sum "$archive" > "$archive.sha256"
  done
)
