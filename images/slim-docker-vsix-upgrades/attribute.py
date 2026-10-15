"""Map Xray-reported npm packages to the VSIX that physically contains them. Usage: attribute.py <slim-dir>"""
import json
import sys
from pathlib import Path

WATCH = {'hono', '@hono/node-server', '@modelcontextprotocol/sdk', 'qs', 'fast-uri',
         'path-to-regexp', 'zod', 'ajv', 'body-parser', 'proxy-addr'}
root = Path(sys.argv[1]) / 'payload' / 'unpacked'
rows = []
for pkg in root.rglob('package.json'):
    try:
        data = json.loads(pkg.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        continue
    if data.get('name') in WATCH and data.get('version'):
        parts = pkg.relative_to(root).parts
        rows.append((parts[0], data['name'], data['version'], '/'.join(parts[1:-1])))
print('| VSIX | package | version | path |\n|---|---|---|---|')
for r in sorted(rows):
    print('| %s | %s | %s | `%s` |' % r)
print('\nPackages absent here may be bundled (esbuild/webpack) with no package.json; check those VSIX JS bundles by name.')
