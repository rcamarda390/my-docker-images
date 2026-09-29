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

const server = spawn(entrypoint, [], {
  detached: true,
  stdio: "inherit",
  env: process.env,
});

function stopServer() {
  if (server.pid === undefined) return;
  try {
    process.kill(-server.pid, "SIGTERM");
  } catch {
    // The process group may already have exited after a startup failure.
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
  const secret = (await readFile("/data/.hmac", "utf8")).trim();
  if (secret.length < 32) throw new Error("generated HMAC secret is unexpectedly short");

  const marker = `runtime-security-smoke-${Date.now()}`;
  await call("/agentmemory/remember", secret, {
    content: marker,
    type: "security-smoke",
    concepts: ["runtime-security-smoke"],
    project: "/tmp/runtime-security-smoke",
  });
  await call("/agentmemory/search", secret, {
    query: marker,
    limit: 1,
    format: "compact",
  });
  console.log("AgentMemory runtime, health, memory_save, and memory_recall smoke OK");
} finally {
  stopServer();
}
