import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { spawn, spawnSync } from "node:child_process";

const entrypoint = "/usr/local/bin/agentmemory-entrypoint.sh";
const baseUrl = "http://127.0.0.1:3111";

const offline = spawnSync(entrypoint, ["--offline-embedding-test"], {
  stdio: "inherit",
  env: process.env,
});
if (offline.status !== 0) {
  throw new Error(`offline embedding smoke failed with status ${offline.status}`);
}

function startServer() {
  return spawn(entrypoint, [], {
    detached: true,
    stdio: "inherit",
    env: process.env,
  });
}
let server = startServer();

async function stopServer() {
  if (server.pid === undefined) return;
  try {
    process.kill(-server.pid, "SIGTERM");
  } catch {
    // The process group may already have exited after a startup failure.
  }
  const deadline = Date.now() + 10_000;
  while (server.exitCode === null && server.signalCode === null && Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  if (server.exitCode === null && server.signalCode === null) {
    try { process.kill(-server.pid, "SIGKILL"); } catch {}
    throw new Error("agentmemory did not stop cleanly for persistence test");
  }
}

async function waitForHealth() {
  const deadline = Date.now() + 90_000;
  while (Date.now() < deadline) {
    if (server.exitCode !== null) {
      throw new Error(`agentmemory exited before health check: ${server.exitCode}`);
    }
    try {
      const response = await fetch(`${baseUrl}/agentmemory/livez`);
      if (response.ok) return;
    } catch {
      // Startup is still in progress.
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error("agentmemory did not become healthy within 90 seconds");
}

async function call(path, secret, body) {
  const response = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${secret}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const responseBody = await response.text();
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}: ${responseBody}`);
  }
  return responseBody;
}

try {
  await waitForHealth();
  // iii 0.22.1 migrates inline settings into its configuration worker on boot.
  // The active values live under the bundled config engine working directory.
  const stateConfig = await readFile("/home/node/.agentmemory/config/iii-state.yaml", "utf8");
  const streamConfig = await readFile("/home/node/.agentmemory/config/iii-stream.yaml", "utf8");
  assert.ok(stateConfig.includes("/data/state_store.db"), "state must stay on the persistent volume");
  assert.ok(streamConfig.includes("/data/stream_store"), "streams must stay on the persistent volume");
  const secret = (await readFile("/data/.hmac", "utf8")).trim();
  if (secret.length < 32) throw new Error("generated HMAC secret is unexpectedly short");

  const unauthorized = await fetch(`${baseUrl}/agentmemory/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: "authentication-smoke", limit: 1 }),
  });
  assert.equal(unauthorized.status, 401, "REST requests must require authentication");

  const marker = `runtime-security-smoke-${Date.now()}`;
  await call("/agentmemory/remember", secret, {
    content: marker,
    type: "security-smoke",
    concepts: ["runtime-security-smoke"],
    project: "/tmp/runtime-security-smoke",
  });
  const results = await call("/agentmemory/search", secret, {
    query: marker,
    limit: 1,
    format: "compact",
  });
  assert.ok(results.includes(marker), "saved memory must be returned by search");
  // File stores flush every 2000ms; allow a full interval plus scheduling margin.
  await new Promise((resolve) => setTimeout(resolve, 4_000));
  await stopServer();
  server = startServer();
  await waitForHealth();
  assert.equal((await readFile("/data/.hmac", "utf8")).trim(), secret, "restart must preserve authentication secret");
  const persisted = await call("/agentmemory/search", secret, {
    query: marker,
    limit: 1,
    format: "compact",
  });
  assert.ok(persisted.includes(marker), "saved memory must survive a server restart");
  console.log("AgentMemory runtime, health, auth, offline embeddings, and restart persistence smoke OK");
} finally {
  await stopServer();
}
