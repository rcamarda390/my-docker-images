import { execFileSync, spawn } from 'node:child_process';
import { readFileSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const root = process.argv[2];
const fixes = JSON.parse(readFileSync(new URL('./security-fixes.json', import.meta.url)));
for (const fix of fixes) {
  const manifest = JSON.parse(readFileSync(join(root, 'node_modules', fix.name, 'package.json')));
  if (manifest.version !== fix.version) throw Error(`${fix.name}: incorrect version`);
}
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
        if (response.id === 2 && response.result?.tools?.length) {clearTimeout(timer); child.kill(); resolve();}
      }
    });
    child.on('error', error => {clearTimeout(timer); reject(error);});
    child.on('exit', code => {clearTimeout(timer); if (code !== null) reject(Error(`MCP exited ${code}: ${errors}`));});
    child.stdin.write(JSON.stringify({jsonrpc: '2.0', id: 1, method: 'initialize', params: {protocolVersion: '2025-03-26', capabilities: {}, clientInfo: {name: 'security-check', version: '1'}}}) + '\n');
  });
} finally { rmSync(home, {recursive: true, force: true}); }
console.log('CodeBurn fixed versions, CLI help and stdio readiness passed');
