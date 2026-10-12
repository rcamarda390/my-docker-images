import { execFileSync, spawn } from 'node:child_process';
import { readFileSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';
const root = process.argv[2];
const fixes = JSON.parse(readFileSync(new URL('./security-fixes.json', import.meta.url)));
for (const fix of fixes) {
  const manifest = JSON.parse(readFileSync(join(root, 'node_modules', fix.name, 'package.json')));
  if (manifest.version !== fix.version) throw Error(`${fix.name}: incorrect version`);
}
// A bounded invalid array must fail before visiting even one element.
const {z} = await import(pathToFileURL(join(root, 'node_modules/zod/index.js')));
for (const asyncParse of [false, true]) {
  let visits = 0;
  const schema = z.array(z.preprocess(value => {visits++; return value;}, z.string())).max(16);
  const values = Array(10000).fill(0);
  const result = asyncParse ? await schema.safeParseAsync(values) : schema.safeParse(values);
  assert.equal(result.success, false);
  assert.equal(result.error.issues.length, 1);
  assert.equal(result.error.issues[0].code, 'too_big');
  assert.equal(visits, 0, 'CVE-2023-54404: oversized input walked before bound');
}
// Execute the actual bundled plugin schema to catch Zod 4 default regressions.
const bundle = readFileSync(join(root, 'dist/main.js'), 'utf8');
const start = bundle.indexOf('    pluginManifestSchema = z.object({');
const end = bundle.indexOf('\n  }\n});', start);
assert.ok(start >= 0 && end > start);
const pluginSchema = new Function('z', 'SUBCOMMAND', 'DOTTED_KEY', 'let pluginManifestSchema;\n' + bundle.slice(start, end) + '\nreturn pluginManifestSchema;')(z, /^[a-z][a-z0-9-]{0,31}$/, /^[a-z][a-z0-9]*(?:[._][a-z0-9]+)+$/);
const plugin = {name: 'fixture', version: '1.0.0', cliCompat: '>=0.9.0'};
const defaults = {commands: [], syncAttributes: [], payloadSections: [], spanKinds: []};
assert.deepEqual(pluginSchema.parse(plugin).capabilities, defaults);
assert.deepEqual(pluginSchema.parse({...plugin, capabilities: {}}).capabilities, defaults);
assert.equal(pluginSchema.safeParse({...plugin, capabilities: {commands: Array(10000).fill(0)}}).error.issues.length, 1);
const home = mkdtempSync(join(tmpdir(), 'codeburn-test-'));
const env = { ...process.env, HOME: home, USERPROFILE: home, CODEBURN_CACHE_DIR: join(home, 'cache'), XDG_CONFIG_HOME: home, XDG_CACHE_HOME: home, XDG_DATA_HOME: home };
try {
  const launch = join(root, 'dist/launch.js');
  const help = execFileSync(process.execPath, [launch, 'models', '--help'], {env, timeout: 30000, encoding: 'utf8'});
  if (!/^Usage: codeburn models\b/m.test(help)) throw Error('CLI arguments broken');
  await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [launch, 'serve', '--stdio'], {env, stdio: ['pipe', 'pipe', 'pipe']});
    let output = '', errors = '';
    const timer = setTimeout(() => { child.kill(); reject(Error(`No ready frame: ${errors}`)); }, 10000);
    child.stderr.on('data', data => errors += data);
    child.stdout.on('data', data => {
      output += data;
      if (output.split('\n').some(line => { try { return JSON.parse(line).ready === true; } catch { return false; } })) {
        clearTimeout(timer); child.kill(); resolve();
      }
    });
    child.on('error', error => {clearTimeout(timer); reject(error);});
    child.on('exit', code => {clearTimeout(timer); if (code !== null) reject(Error(`Serve exited ${code}: ${errors}`));});
  });

  await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [launch, 'mcp'], {env, stdio: ['pipe', 'pipe', 'pipe']});
    let output = '', errors = '';
    const timer = setTimeout(() => {child.kill(); reject(Error(`MCP timeout: ${errors}`));}, 10000);
    child.stderr.on('data', data => errors += data);
    child.stdout.on('data', data => {
      output += data;
      const lines = output.split('\n'); output = lines.pop();
      for (const line of lines) {
        const response = JSON.parse(line);
        if (response.error) {clearTimeout(timer); child.kill(); reject(Error(JSON.stringify(response.error)));}
        if (response.id === 1 && response.result?.capabilities) {
          child.stdin.write(JSON.stringify({jsonrpc: '2.0', method: 'notifications/initialized'}) + '\n');
          child.stdin.write(JSON.stringify({jsonrpc: '2.0', id: 2, method: 'tools/list'}) + '\n');
        }
        if (response.id === 2 && response.result?.tools?.length) {
          child.stdin.write(JSON.stringify({jsonrpc: '2.0', id: 3, method: 'tools/call', params: {name: 'get_usage', arguments: {period: 'today'}}}) + '\n');
        }
        if (response.id === 3) {
          clearTimeout(timer); child.kill();
          if (response.result?.isError || !response.result?.structuredContent) reject(Error(JSON.stringify(response)));
          else resolve();
        }
      }
    });
    child.on('error', error => {clearTimeout(timer); reject(error);});
    child.on('exit', code => {clearTimeout(timer); if (code !== null) reject(Error(`MCP exited ${code}: ${errors}`));});
    child.stdin.write(JSON.stringify({jsonrpc: '2.0', id: 1, method: 'initialize', params: {protocolVersion: '2025-03-26', capabilities: {}, clientInfo: {name: 'security-check', version: '1'}}}) + '\n');
  });
} finally { rmSync(home, {recursive: true, force: true}); }
console.log('CodeBurn fixed versions, CLI help and stdio readiness, MCP tool call and bounded Zod regression passed');
