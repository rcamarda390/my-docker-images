// patch-worker-offline-embeddings.mjs: load the offline model loader in the compose-launched worker.
// AgentMemory 0.9.31 renders the worker as `node dist/index.mjs` and forwards only an
// allowlisted environment, so the image NODE_OPTIONS never reaches it. Without the loader
// Transformers.js tries Hugging Face and local embeddings fail with "fetch failed" offline.
// transformers-offline.mjs defaults to the baked model paths, so no env vars are needed.
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.env.AGENTMEMORY_ROOT || '/opt/agentmemory';
const pkg = join(root, 'node_modules/@agentmemory/agentmemory');
assert.equal(JSON.parse(readFileSync(join(pkg, 'package.json'), 'utf8')).version, '0.9.31', 'revalidate worker launch patch on upstream upgrades');
const file = join(pkg, 'dist/cli.mjs');
const before = 'shellCommand(options.nodeBin, ["dist/index.mjs"], options.windows';
const after = 'shellCommand(options.nodeBin, ["--import", "/opt/agentmemory/transformers-offline.mjs", "dist/index.mjs"], options.windows';
const source = readFileSync(file, 'utf8');
assert.equal(source.split(before).length - 1, 1, 'worker launch renderer changed');
writeFileSync(file, source.replace(before, after));
assert.ok(readFileSync(file, 'utf8').includes(after), 'worker launch patch did not apply');
console.log('compose worker launch patched to load transformers-offline.mjs');
