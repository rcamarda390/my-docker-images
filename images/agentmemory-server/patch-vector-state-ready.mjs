// patch-vector-state-ready.mjs: wait for the state worker before loading the vector checkpoint.
// AgentMemory 0.9.31 starts the agentmemory worker once the state worker process is up, not once
// state::get is registered. The first vector-metadata read can lose that race by ~100 ms, which
// reports the checkpoint as unavailable and pauses vector recovery and saves until restart.
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const root = process.env.AGENTMEMORY_ROOT || '/opt/agentmemory';
const pkg = join(root, 'node_modules/@agentmemory/agentmemory');
assert.equal(JSON.parse(readFileSync(join(pkg, 'package.json'), 'utf8')).version, '0.9.31', 'revalidate vector state-ready patch on upstream upgrades');
const dist = join(pkg, 'dist');
const before = 'meta = await this.kv.get(KV.bm25Index, VECTOR_META_KEY);';
// ponytail: retries only this one boot read, 60 x 500 ms. Upgrade path: upstream retry in
// StateKV.get or a real worker readiness wait; drop this patch when upstream fixes the race.
const after = 'for (let attempt = 0;; attempt++) { try { meta = await this.kv.get(KV.bm25Index, VECTOR_META_KEY); break; } catch (err) { if (attempt >= 60 || !/function_not_found/.test(String(err?.message ?? err))) throw err; await new Promise((resolve) => setTimeout(resolve, 500)); } }';

// The retry must wait on function_not_found only and rethrow everything else.
const AsyncFunction = Object.getPrototypeOf(async () => {}).constructor;
const run = new AsyncFunction('KV', 'VECTOR_META_KEY', 'setTimeout', `let meta; ${after} return meta;`);
const stub = (failures, message) => ({ kv: { calls: 0, async get() { if (this.calls++ < failures) throw new Error(message); return 'meta'; } } });
const fast = (fn) => fn();
const raced = stub(3, 'function_not_found: Function state::get not found');
assert.equal(await run.call(raced, { bm25Index: 'k' }, 'm', fast), 'meta');
assert.equal(raced.kv.calls, 4, 'retry must wait out function_not_found');
await assert.rejects(run.call(stub(1, 'disk read error'), { bm25Index: 'k' }, 'm', fast), /disk read error/);
await assert.rejects(run.call(stub(99, 'function_not_found: x'), { bm25Index: 'k' }, 'm', fast), /function_not_found/);

let patched = 0;
for (const name of readdirSync(dist).filter((f) => f.endsWith('.mjs'))) {
  const file = join(dist, name);
  const source = readFileSync(file, 'utf8');
  const count = source.split(before).length - 1;
  if (count === 0) continue;
  assert.ok(!source.includes(after), `already patched: ${name}`);
  assert.equal(count, 1, `vector metadata read changed: ${name}`);
  writeFileSync(file, source.replace(before, () => after));
  assert.ok(readFileSync(file, 'utf8').includes(after), `patch did not apply: ${name}`);
  patched++;
}
assert.ok(patched >= 1, 'vector metadata read not found in any bundle');
console.log(`vector metadata read patched in ${patched} bundle(s)`);
