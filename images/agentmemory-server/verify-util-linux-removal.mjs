// verify-util-linux-removal.mjs: audit runtime dependencies and physical absence.
import { execFileSync } from 'node:child_process';
import { closeSync, existsSync, lstatSync, openSync, readFileSync, readSync,
  readdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const [mode, root, manifest, readelf = '/tmp/readelf-tool/readelf', family = 'util-linux'] = process.argv.slice(2);
if (!['audit', 'absent'].includes(mode) || !root?.startsWith('/') ||
    !['util-linux', 'sqlite'].includes(family)) {
  throw new Error('usage: audit|absent ROOT MANIFEST [READELF] [util-linux|sqlite]');
}
const removed = new Set(family === 'sqlite' ? ['libsqlite3-0'] :
  ['bsdutils', 'login', 'mount', 'util-linux', 'libblkid1',
    'liblastlog2-2', 'libmount1', 'libsmartcols1', 'libuuid1']);
const query = (...args) => execFileSync('dpkg-query',
  [`--admindir=${root}/var/lib/dpkg`, ...args], { encoding: 'utf8' });
const rows = query('-W', '-f=${Package}\t${db:Status-Status}\t${Depends}\t${Pre-Depends}\n')
  .trim().split('\n').map(line => line.split('\t'));
const installed = rows.filter(([, state]) => state === 'installed');
const present = p => existsSync(p) || (() => {
  try { return lstatSync(p).isSymbolicLink(); } catch { return false; }
})();

if (mode === 'absent') {
  for (const [pkg] of installed) {
    if (removed.has(pkg)) throw new Error(`${pkg} remains installed`);
  }
  for (const file of JSON.parse(readFileSync(manifest, 'utf8'))) {
    if (present(root + file)) throw new Error(`purged file remains: ${file}`);
  }
  console.log(`${family} package and physical-file absence verified`);
  process.exit(0);
}

// Check the actual installed dependency graph, including Pre-Depends. Fail
// conservatively even for an alternative containing a removed package.
for (const [pkg, , depends = '', predepends = ''] of installed) {
  if (removed.has(pkg)) continue;
  for (const dependency of `${depends},${predepends}`.split(/[,|]/)) {
    const name = dependency.trim().match(/^([a-z0-9][a-z0-9+.-]*)/)?.[1];
    if (removed.has(name)) throw new Error(`${pkg} requires ${name}`);
  }
}

// Normalize Debian's merged-/usr file names for ownership comparison only.
const merged = file => file.replace(/^\/(bin|sbin|lib|lib64)(?=\/)/, '/usr/$1');
const owned = new Set();
const physical = new Set();
for (const [pkg] of installed) {
  if (!removed.has(pkg)) continue;
  for (const file of query('-L', pkg).trim().split('\n')) {
    if (!file.startsWith('/') || !present(root + file)) continue;
    const stat = lstatSync(root + file);
    if (stat.isDirectory()) continue;
    owned.add(merged(file));
    physical.add(file);
  }
}
if (!owned.size) throw new Error(`no installed ${family} files to audit`);

const forbidden = family === 'sqlite' ? /^libsqlite3\.so(?:\.|$)/ :
  /^lib(?:blkid|lastlog2|mount|smartcols|uuid)\.so(?:\.|$)/;
let checked = 0;
function walk(directory) {
  for (const entry of readdirSync(root + directory, { withFileTypes: true })) {
    const file = path.posix.join(directory, entry.name);
    if (entry.isDirectory()) { walk(file); continue; }
    if (!entry.isFile() || owned.has(merged(file))) continue;
    const fd = openSync(root + file, 'r');
    const magic = Buffer.alloc(4);
    try { readSync(fd, magic, 0, 4, 0); } finally { closeSync(fd); }
    if (!magic.equals(Buffer.from([0x7f, 0x45, 0x4c, 0x46]))) continue;
    const dynamic = execFileSync(readelf, ['--dynamic', root + file],
      { encoding: 'utf8', maxBuffer: 4 * 1024 * 1024,
        env: { ...process.env, LD_LIBRARY_PATH: path.dirname(readelf) } });
    for (const line of dynamic.split('\n')) {
      const needed = line.match(/\(NEEDED\).*Shared library: \[([^\]]+)\]/)?.[1];
      if (needed && forbidden.test(needed)) {
        throw new Error(`${file} dynamically requires ${needed}`);
      }
    }
    checked++;
  }
}
walk('/');
if (!checked) throw new Error('no retained ELF files inspected');
writeFileSync(manifest, JSON.stringify([...physical].sort()));
console.log(`${family} removal audit: installed reverse dependencies clear; ${checked} retained ELF files checked`);
