import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.env.AGENTMEMORY_ROOT || "/opt/agentmemory";

// Xray's fixed versions are pinned here as well as in package.json so the
// build fails if npm resolves a vulnerable copy or changes the package tree.
// Packages absent from today's graph retain their fix floor if they return
// through floating transitive ranges. iii-sdk 0.22.1 no longer needs the
// downstream OpenTelemetry Resource API patch or its runtime SDK overrides.
const fixedVersions = {
  "adm-zip": "0.6.1",
  "proxy-addr": "2.0.8",
  "@modelcontextprotocol/sdk": "1.32.0",
  hono: "4.13.11",
  "@hono/node-server": "2.1.3",
  "fast-uri": "3.1.8",
  "brace-expansion": "5.0.9",
  "ip-address": "10.7.1",
  sharp: "0.35.5",
  tar: "7.5.21",
  undici: "6.28.0",
  "@opentelemetry/propagator-jaeger": "2.9.0",
};

const lock = JSON.parse(readFileSync(join(root, "package-lock.json"), "utf8"));
for (const [name, expected] of Object.entries(fixedVersions)) {
  const installed = Object.entries(lock.packages)
    .filter(([path, entry]) => {
      const packageName = entry.name || path.split("node_modules/").at(-1);
      return packageName === name;
    })
    .map(([path, entry]) => ({ path, version: entry.version }));

  if (installed.length === 0) {
    console.log(`dependency absent (not in resolved graph): ${name}`);
    continue;
  }

  for (const entry of installed) {
    const actual = JSON.parse(
      readFileSync(join(root, entry.path, "package.json"), "utf8"),
    ).version;
    if (entry.version !== expected || actual !== expected) {
      throw new Error(
        `${name} lock=${entry.version}, installed=${actual} at ${entry.path}; expected ${expected}`,
      );
    }
  }
  console.log(`dependency OK: ${name}@${expected}`);
}

