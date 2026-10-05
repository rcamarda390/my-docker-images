// verify-util-linux-removal.test.mjs: reject unsafe runtime package removal.
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, unlinkSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import assert from 'node:assert/strict';

const audit = fileURLToPath(new URL('./verify-util-linux-removal.mjs', import.meta.url));
const packageRecord = (name, extra = '') =>
  `Package: ${name}\nStatus: install ok installed\nArchitecture: amd64\nVersion: 1\nMaintainer: test\nDescription: fixture\n${extra}\n`;

for (const [family, pkg, soname] of [
  ['util-linux', 'libuuid1', 'libuuid.so.1'],
  ['sqlite', 'libsqlite3-0', 'libsqlite3.so.0'],
]) test(`${family} removal rejects reverse dependencies, ELF imports and leftover files`, () => {
  const temporary = mkdtempSync(path.join(tmpdir(), 'util-removal-'));
  try {
    const root = path.join(temporary, 'root');
    const database = path.join(root, 'var/lib/dpkg');
    mkdirSync(path.join(database, 'info'), { recursive: true });
    mkdirSync(path.join(root, 'usr/lib'), { recursive: true });
    mkdirSync(path.join(root, 'usr/bin'), { recursive: true });
    const status = path.join(database, 'status');
    const base = packageRecord(pkg) + packageRecord('consumer');
    writeFileSync(status, base);
    writeFileSync(path.join(database, `info/${pkg}.list`), `/usr/lib/${soname}\n`);
    const library = path.join(root, 'usr/lib', soname);
    writeFileSync(library, 'unused package file');
    writeFileSync(path.join(root, 'usr/bin/consumer'), Buffer.from([0x7f, 0x45, 0x4c, 0x46]));
    const reader = path.join(temporary, 'readelf');
    writeFileSync(reader, '#!/bin/sh\nexit 0\n', { mode: 0o755 });
    const manifest = path.join(temporary, 'manifest.json');
    const run = mode => spawnSync(process.execPath, [audit, mode, root, manifest, reader, family],
      { encoding: 'utf8' });
    assert.equal(run('audit').status, 0);

    writeFileSync(status, base + packageRecord('dependent', `Pre-Depends: ${pkg}\n`));
    assert.ok(run('audit').stderr.includes(`dependent requires ${pkg}`));
    writeFileSync(status, base);
    writeFileSync(reader, `#!/bin/sh\nprintf " (NEEDED) Shared library: [${soname}]\\n"\n`);
    assert.ok(run('audit').stderr.includes(`consumer dynamically requires ${soname}`));
    writeFileSync(reader, '#!/bin/sh\nexit 0\n');
    writeFileSync(status, packageRecord('consumer'));
    assert.match(run('absent').stderr, /purged file remains/);
    unlinkSync(library);
    assert.equal(run('absent').status, 0);
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
});
