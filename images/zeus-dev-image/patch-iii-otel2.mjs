import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const root = process.env.AGENTMEMORY_ROOT || "/opt/agentmemory";
const packageRoot = join(root, "node_modules");

// Zeus pins the coordinated OpenTelemetry 2.9.0 dependency family here and in package.json so the
// build fails if npm resolves a vulnerable copy or changes the dependency tree.
// iii-sdk 0.11.2 uses the pre-2.x Resource constructor and is patched below.
const fixedVersions = {
  "@opentelemetry/api-logs": "0.200.0",
  "@opentelemetry/core": "2.9.0",
  "@opentelemetry/context-async-hooks": "2.9.0",
  "@opentelemetry/instrumentation": "0.200.0",
  "@opentelemetry/otlp-transformer": "0.200.0",
  "@opentelemetry/propagator-b3": "2.9.0",
  "@opentelemetry/propagator-jaeger": "2.9.0",
  "@opentelemetry/resources": "2.9.0",
  "@opentelemetry/sdk-logs": "0.200.0",
  "@opentelemetry/sdk-metrics": "2.9.0",
  "@opentelemetry/sdk-trace-base": "2.9.0",
  "@opentelemetry/sdk-trace-node": "2.9.0",
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
    if (entry.version !== expected) {
      throw new Error(
        `${name} resolved to ${entry.version} at ${entry.path}; expected ${expected}`,
      );
    }
  }
  console.log(`dependency OK: ${name}@${expected}`);
}

// iii-sdk 0.11.2 imports the pre-2.x Resource constructor. OpenTelemetry 2.x
// deliberately exposes resourceFromAttributes instead, so patch both bundle
// formats and fail if the expected upstream bundle shape changes.
const iiiDist = join(packageRoot, "iii-sdk", "dist");
const replacements = [
  [
    'import { Resource } from "@opentelemetry/resources";',
    'import { resourceFromAttributes } from "@opentelemetry/resources";',
  ],
  [
    "const resource = new Resource(resourceAttributes);",
    "const resource = resourceFromAttributes(resourceAttributes);",
  ],
  [
    "const resource = new _opentelemetry_resources.Resource(resourceAttributes);",
    "const resource = _opentelemetry_resources.resourceFromAttributes(resourceAttributes);",
  ],
];

const changed = [];
for (const file of readdirSync(iiiDist)) {
  if (!file.endsWith(".mjs") && !file.endsWith(".cjs")) continue;
  const path = join(iiiDist, file);
  let source = readFileSync(path, "utf8");
  let fileChanged = false;

  for (const [from, to] of replacements) {
    const count = source.split(from).length - 1;
    if (count > 1) {
      throw new Error(`ambiguous iii-sdk patch target in ${path}: ${from}`);
    }
    if (count === 1) {
      source = source.replace(from, to);
      fileChanged = true;
    }
  }

  if (fileChanged) {
    writeFileSync(path, source);
    changed.push(file);
  }
}

if (!changed.includes("utils-DvwOdG2_.mjs")) {
  throw new Error("iii-sdk ESM Resource compatibility patch did not apply");
}
if (!changed.includes("utils-SC0gzoUa.cjs")) {
  throw new Error("iii-sdk CommonJS Resource compatibility patch did not apply");
}

console.log(`iii-sdk OpenTelemetry 2.x compatibility patched: ${changed.join(", ")}`);
