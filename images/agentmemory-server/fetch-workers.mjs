// fetch-workers.mjs: bake pinned iii registry workers for AGENTMEMORY_WORKER_BIN_DIR.
// Runs only in the connected build stage. Each named worker is resolved at its
// exact version, downloaded, and checked against the registry SHA-256 before it
// is installed as an executable named after the worker.
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { chmodSync, copyFileSync, mkdirSync, mkdtempSync, readdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const registry = 'https://api.workers.iii.dev';
const target = 'x86_64-unknown-linux-gnu';
const [out, ...specs] = process.argv.slice(2);

async function download(url, sha256) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`download ${url}: HTTP ${response.status}`);
  const bytes = Buffer.from(await response.arrayBuffer());
  const digest = createHash('sha256').update(bytes).digest('hex');
  if (digest !== sha256.toLowerCase()) throw new Error(`sha256 mismatch for ${url}: ${digest}`);
  return bytes;
}

function findFile(dir, name) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      const found = findFile(path, name);
      if (found) return found;
    } else if (entry.name === name) return path;
  }
  return null;
}

mkdirSync(out, { recursive: true });
for (const spec of specs) {
  const [name, version] = spec.split('=');
  const response = await fetch(`${registry}/resolve`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ worker: name, version, target }),
  });
  if (!response.ok) throw new Error(`resolve ${spec}: HTTP ${response.status}`);
  const worker = (await response.json()).graph.find(item => item.name === name);
  if (worker?.version !== version) throw new Error(`registry did not resolve ${spec}`);

  const destination = join(out, name);
  const binary = worker.binaries?.[target];
  if (binary) {
    writeFileSync(destination, await download(binary.url, binary.sha256), { mode: 0o755 });
  } else if (worker.archive_url) {
    // ponytail: bundles are read with tar; zip-only archives would need unzip.
    const archive = join(mkdtempSync(join(tmpdir(), name)), 'bundle');
    writeFileSync(archive, await download(worker.archive_url, worker.sha256));
    const extracted = mkdtempSync(join(tmpdir(), `${name}-x`));
    execFileSync('tar', ['-xf', archive, '-C', extracted]);
    const found = findFile(extracted, name);
    if (!found) throw new Error(`bundle for ${spec} has no ${name} executable`);
    copyFileSync(found, destination);
    chmodSync(destination, 0o755);
  } else {
    throw new Error(`registry has no ${target} artifact for ${spec}`);
  }
}
