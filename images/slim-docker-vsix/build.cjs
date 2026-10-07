// File: images/slim-docker-vsix/build.cjs
// Compile the pinned source; inventory only modules actually included by webpack.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const webpack = require('/src/node_modules/webpack');
const config = require('/src/webpack.config');
config.mode = 'production';
assert.equal(require('/src/node_modules/ws/package.json').version, '8.21.0');
assert.equal(require('/src/package.json').engines.vscode, '^1.80.0');
webpack(config, (error, stats) => {
  if (error || stats.hasErrors()) {
    console.error(error || stats.toString({all: false, errors: true}));
    process.exitCode = 1;
    return;
  }
  const packages = new Map();
  function visit(module) {
    if (module.resource && module.resource.includes('/node_modules/')) {
      let directory = path.dirname(module.resource);
      while (directory !== '/src' && directory !== '/') {
        const manifest = path.join(directory, 'package.json');
        if (fs.existsSync(manifest)) {
          const pkg = JSON.parse(fs.readFileSync(manifest));
          packages.set(`${pkg.name}@${pkg.version}`, {name: pkg.name, version: pkg.version, license: pkg.license});
          break;
        }
        directory = path.dirname(directory);
      }
    }
    if (module.modules) for (const child of module.modules) visit(child);
  }
  for (const module of stats.compilation.modules) visit(module);
  assert(packages.has('ws@8.21.0'), 'fixed ws must be in compiled bundle');
  assert(![...packages.values()].some(p => p.name === 'ws' && p.version !== '8.21.0'));
  // codicons are shipped media rather than imported webpack modules.
  packages.set('@vscode/codicons@0.0.32', {name: '@vscode/codicons', version: '0.0.32', license: 'CC-BY-4.0'});
  fs.writeFileSync('/src/runtime-packages.json', JSON.stringify([...packages.values()], null, 2));
  console.log(`Compiled bundle includes ${packages.size} runtime packages; ws 8.21.0 verified.`);
});
