// ONNX's proxy/logger chain is needed only by script/install.js, after npm
// has installed the native binaries. Keep inference code and binaries intact.
import { existsSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import assert from 'node:assert/strict';

const root = process.env.AGENTMEMORY_ROOT || '/opt/agentmemory';
const load = path => JSON.parse(readFileSync(path, 'utf8'));
const save = (path, value) => writeFileSync(path, JSON.stringify(value, null, 2) + '\n');
const lockPath = join(root, 'package-lock.json');
const lock = load(lockPath);
const removed = new Set(['global-agent', 'roarr', 'sprintf-js']);
const expectedConsumers = new Map([
  ['global-agent', 'node_modules/onnxruntime-node'],
  ['roarr', 'node_modules/global-agent'],
  ['sprintf-js', 'node_modules/roarr'],
]);
const seen = new Set();
const nameOf = (path, entry) => entry.name || path.split('node_modules/').at(-1);

// Prove installed reverse dependencies, not just the top-level npm manifest.
// Floating dependency changes must fail rather than remove a new runtime use.
for (const [path, entry] of Object.entries(lock.packages)) {
  if (!path) continue;
  const manifestPath = join(root, path, 'package.json');
  if (!existsSync(manifestPath)) assert(entry.optional, `${path}: required package missing`);
  const actual = existsSync(manifestPath) ? load(manifestPath) : entry;
  assert.equal(actual.version, entry.version, `${path}: installed/lock mismatch`);
  for (const field of ['dependencies', 'optionalDependencies', 'peerDependencies']) {
    for (const name of removed) {
      if (entry[field]?.[name] || actual[field]?.[name]) {
        assert.equal(path, expectedConsumers.get(name), `${path} requires ${name}`);
        seen.add(name);
      }
    }
  }
  if (removed.has(nameOf(path, entry))) {
    assert.equal(path, `node_modules/${nameOf(path, entry)}`, 'unexpected nested installer copy');
  }
}
assert.deepEqual([...seen].sort(), [...removed].sort(), 'installer dependency graph changed');

const onnxPath = join(root, 'node_modules/onnxruntime-node');
const onnx = load(join(onnxPath, 'package.json'));
assert.equal(onnx.version, '1.24.3', 're-review installer usage after ONNX upgrade');
assert.equal(onnx.main, 'dist/index.js');
assert.equal(onnx.scripts.postinstall, 'node ./script/install');
assert.match(readFileSync(join(onnxPath, 'script/install.js'), 'utf8'), /require\('global-agent'\)/);
assert(existsSync(join(onnxPath, 'bin/napi-v6/linux/x64/onnxruntime_binding.node')));

// This deployment has no npm at runtime. Remove the installer together with
// its now-unused helpers and describe the resulting graph truthfully.
delete onnx.dependencies['global-agent'];
delete onnx.scripts;
save(join(onnxPath, 'package.json'), onnx);
rmSync(join(onnxPath, 'script'), { recursive: true });
for (const name of removed) rmSync(join(root, 'node_modules', name), { recursive: true });

for (const path of [lockPath, join(root, 'node_modules/.package-lock.json')]) {
  const manifest = load(path);
  for (const [packagePath, entry] of Object.entries(manifest.packages)) {
    if (removed.has(nameOf(packagePath, entry))) delete manifest.packages[packagePath];
  }
  delete manifest.packages['node_modules/onnxruntime-node'].dependencies['global-agent'];
  manifest.packages['node_modules/onnxruntime-node'].hasInstallScript = false;
  save(path, manifest);
}
for (const name of removed) {
  assert(!existsSync(join(root, 'node_modules', name)), `${name} still installed`);
  assert(!Object.values(load(lockPath).packages).some(entry => entry.dependencies?.[name]));
}
await import(join(onnxPath, 'dist/index.js'));
console.log('ONNX installer removed; native inference import OK');
