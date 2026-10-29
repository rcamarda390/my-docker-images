// patch-compose-http-bind.mjs: publish the REST worker on the container interfaces.
// AgentMemory 0.9.31 renders the http worker host as 127.0.0.1, which published
// container ports cannot reach. Only that renderer line changes; the engine's
// internal worker-manager host stays on loopback.
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.env.AGENTMEMORY_ROOT || '/opt/agentmemory';
const file = join(root, 'node_modules/@agentmemory/agentmemory/dist/cli.mjs');
const before = '"    config_override:", "      host: 127.0.0.1", `      port: ${restPort}`';
const after = '"    config_override:", "      host: 0.0.0.0", `      port: ${restPort}`';
const source = readFileSync(file, 'utf8');
assert.equal(source.split(before).length - 1, 1, 'http bind renderer changed');
writeFileSync(file, source.replace(before, after));
console.log('compose http worker bind patched to 0.0.0.0');
