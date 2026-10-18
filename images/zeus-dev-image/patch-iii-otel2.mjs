import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const root = process.env.AGENTMEMORY_ROOT || "/opt/agentmemory";

// Zeus pins the coordinated OpenTelemetry 2.9.0 dependency family here and in package.json so the
// build fails if npm resolves a vulnerable copy or changes the dependency tree.
// iii-sdk 0.22.1 delegates telemetry to @iii-dev/helpers, patched below.
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

const helpers = join(root, "node_modules/@iii-dev/helpers");
if (JSON.parse(readFileSync(join(helpers, "package.json"))).version !== "0.22.1") {
  throw new Error("Revalidate OpenTelemetry compatibility against the new helpers version");
}

// Reuse the former iii-sdk Resource adaptation for its new helper package.
// OTel 2.x also supplies log processors through constructor options.
for (const extension of ["mjs", "cjs"]) {
  const files = readdirSync(join(helpers, "dist"))
    .filter(file => file.startsWith("telemetry-system-") && file.endsWith(`.${extension}`));
  if (files.length !== 1) throw new Error(`Expected one ${extension} telemetry bundle`);
  const file = join(helpers, "dist", files[0]);
  let source = readFileSync(file, "utf8");
  const prefix = extension === "mjs" ? "" : "_opentelemetry_sdk_logs.";
  const replacements = [
    ...(extension === "mjs" ? [[
      'import { Resource } from "@opentelemetry/resources";',
      'import { resourceFromAttributes } from "@opentelemetry/resources";',
    ]] : []),
    [
      `const resource = new ${extension === "mjs" ? "" : "_opentelemetry_resources."}Resource(resourceAttributes);`,
      `const resource = ${extension === "mjs" ? "" : "_opentelemetry_resources."}resourceFromAttributes(resourceAttributes);`,
    ],
    [
      `loggerProvider = new ${prefix}LoggerProvider({ resource });\n\tloggerProvider.addLogRecordProcessor(new ${prefix}BatchLogRecordProcessor(logExporter, {\n\t\tscheduledDelayMillis: logsScheduledDelayMillis,\n\t\tmaxExportBatchSize: logsMaxExportBatchSize\n\t}));`,
      `loggerProvider = new ${prefix}LoggerProvider({\n\t\tresource,\n\t\tprocessors: [new ${prefix}BatchLogRecordProcessor({\n\t\t\texporter: logExporter,\n\t\t\tscheduledDelayMillis: logsScheduledDelayMillis,\n\t\t\tmaxExportBatchSize: logsMaxExportBatchSize\n\t\t})]\n\t});`,
    ],
  ];
  for (const [from, to] of replacements) {
    if (source.split(from).length !== 2) throw new Error(`Changed upstream patch target: ${file}: ${from}`);
    source = source.replace(from, to);
  }
  writeFileSync(file, source);
  console.log(`OpenTelemetry 2.x helper compatibility patched: ${files[0]}`);
}

