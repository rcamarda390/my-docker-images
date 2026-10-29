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

// 0.9.31 starts Worker Compose as a detached daemon, so the CLI exits 0 once
// the engine is up. Only a non-zero exit is a startup failure. The entrypoint
// then holds PID 1 open; unref so this child does not keep Node alive.
function startServer() {
  const child = spawn(entrypoint, [], {
    stdio: "inherit",
    env: process.env,
  });
  child.unref();
  return child;
}
let server = startServer();

async function stopServer() {
  const stopped = spawnSync(entrypoint, ["stop"], { stdio: "inherit", env: process.env });
  if (stopped.status !== 0) throw new Error(`agentmemory stop failed with status ${stopped.status}`);
  const deadline = Date.now() + 20_000;
  while (Date.now() < deadline) {
    try {
      await fetch(`${baseUrl}/agentmemory/livez`);
    } catch {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("agentmemory did not stop cleanly for persistence test");
}

async function waitForHealth() {
  const deadline = Date.now() + 90_000;
  while (Date.now() < deadline) {
    if (server.exitCode !== null && server.exitCode !== 0) {
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

async function status(secret) {
  const response = await fetch(`${baseUrl}/agentmemory/status`, { headers: { Authorization: `Bearer ${secret}` } });
  assert.equal(response.status, 200, "status must be readable with the bearer");
  return response.json();
}

// The compose-launched worker only gets an allowlisted environment, so this proves the
// offline model loader reaches it and the vector checkpoint loads (no fetch or state race).
async function waitForVectors(secret, minimum) {
  const deadline = Date.now() + 60_000;
  let last;
  while (Date.now() < deadline) {
    last = await status(secret);
    if ((last.index?.vectorDocuments ?? 0) >= minimum && !last.indexPersistence?.vector?.lastError) return last;
    await new Promise((resolve) => setTimeout(resolve, 1_000));
  }
  throw new Error(`worker did not embed offline: vectorDocuments=${last?.index?.vectorDocuments} lastError=${last?.indexPersistence?.vector?.lastError}`);
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
  // Worker Compose writes the state worker config into its project directory.
  const composeFile = await readFile("/data/compose/worker-compose.yaml", "utf8");
  assert.ok(composeFile.includes("/data/state_store.db"), "state must stay on the persistent volume");
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
  await waitForVectors(secret, 1);
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
  // The vector checkpoint is saved on an interval; the pending log must restore the vector after restart.
  await waitForVectors(secret, 1);
  console.log("AgentMemory runtime, health, auth, offline embeddings, and restart persistence smoke OK");
} finally {
  await stopServer().catch(() => {});
}
