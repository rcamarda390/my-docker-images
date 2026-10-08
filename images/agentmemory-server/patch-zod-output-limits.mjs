// patch-zod-output-limits.mjs: bound AgentMemory's generated-output validation.
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { runInNewContext } from 'node:vm';

const root = process.env.AGENTMEMORY_ROOT || '/opt/agentmemory';
const dist = join(root, 'node_modules/@agentmemory/agentmemory/dist');
const version = JSON.parse(readFileSync(join(dist, '../package.json'), 'utf8')).version;
assert.equal(version, '0.9.30', 'revalidate generated-output patch on upstream upgrades');
const { z } = await import(pathToFileURL(join(root, 'node_modules/zod/index.js')));
const fields = ['facts', 'concepts', 'files', 'keyDecisions', 'filesModified'];
const before = 'function validateInput(schema, data, functionId) {\n\tconst parsed = schema.safeParse(data);';
const after = `function validateInput(schema, data, functionId) {
	// ponytail: cap generated-output arrays at 1024 before Zod expands issues.
	// Revalidate/remove when upstream provides bounded validation; imports are unaffected.
	for (const field of ${JSON.stringify(fields)}) {
		if (Array.isArray(data?.[field]) && data[field].length > 1024) return {
			valid: false,
			result: {
				valid: false,
				errors: [field + ": generated output exceeds 1024 entries"],
				qualityScore: 0,
				latencyMs: 0,
				functionId
			}
		};
	}
	const parsed = schema.safeParse(data);`;

// Both entry bundles contain the same shared validator. Patch exact source;
// changing a different schema or a package-wide Zod API would broaden behavior.
for (const file of ['index.mjs', 'src-Jsq9LCeH.mjs']) {
  const path = join(dist, file);
  const source = readFileSync(path, 'utf8');
  assert.equal(source.split(before).length - 1, 1, `validator changed: ${file}`);
  const patched = source.replace(before, after);
  const body = patched.match(/function validateInput\(schema, data, functionId\) \{[\s\S]*?\n(?=function validateOutput)/)?.[0];
  assert.ok(body, `cannot extract validator: ${file}`);
  const validate = runInNewContext(body + '\nvalidateInput');
  const schema = z.object({ facts: z.array(z.string()).min(1) });
  assert.equal(validate(schema, { facts: ['remember this'] }, 'test').valid, true);
  assert.equal(validate(schema, { facts: Array(1024).fill('fact') }, 'test').valid, true);
  const invalid = validate(schema, { facts: [42] }, 'test');
  assert.equal(invalid.valid, false);
  assert.equal(invalid.result.errors.length, 1);
  assert.equal(invalid.result.functionId, 'test');
  for (const field of fields) {
    const rejected = validate({ safeParse() { throw new Error('Zod must not run'); } },
      { [field]: Array(1025).fill(null) }, 'test');
    assert.equal(rejected.valid, false);
    assert.match(rejected.result.errors[0], /exceeds 1024/);
  }
  writeFileSync(path, patched);
  console.log(`generated-output validation bounded and regression checked: ${file}`);
}
