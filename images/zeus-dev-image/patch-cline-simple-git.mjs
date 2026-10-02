// patch-cline-simple-git.mjs: adapt Cline's default import to simple-git 4's named export.
import fs from 'node:fs';
import path from 'node:path';

const root = '/opt/cline/node_modules/@cline/core/dist';
let changed = 0;
function patch(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const file = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      patch(file);
    } else if (/\.[cm]?js$/.test(entry.name)) {
      const source = fs.readFileSync(file, 'utf8');
      const updated = source.replace(/import\s+([\w$]+)\s+from\s*(["'])simple-git\2/g,
        (_, name) => `import {simpleGit as ${name}} from "simple-git"`);
      if (source !== updated) {
        fs.writeFileSync(file, updated);
        changed++;
      }
    }
  }
}
patch(root);
if (!changed) throw new Error('Cline simple-git import changed upstream; review/remove patch');
console.log(`Adapted simple-git imports in ${changed} Cline modules`);
