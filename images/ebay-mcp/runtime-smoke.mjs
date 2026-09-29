import { spawn } from 'node:child_process';

const host = '127.0.0.1';
const port = 3000;
const baseUrl = `http://${host}:${port}`;
const server = spawn(process.execPath, ['build/serverHttp.js'], {
  cwd: process.cwd(),
  env: {
    ...process.env,
    MCP_HOST: host,
    MCP_PORT: String(port),
  },
  stdio: 'inherit',
});

const sleep = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

const parseMcpResponse = (body) => {
  const data = body
    .split('\n')
    .find((line) => line.startsWith('data:'))
    ?.slice('data:'.length)
    .trim();
  return JSON.parse(data ?? body);
};

const postMcp = async (payload, sessionId) => {
  const headers = {
    Accept: 'application/json, text/event-stream',
    'Content-Type': 'application/json',
  };
  if (sessionId) {
    headers['Mcp-Session-Id'] = sessionId;
  }
  return fetch(`${baseUrl}/`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });
};

try {
  let healthy = false;
  for (let attempt = 0; attempt < 30; attempt += 1) {
    if (server.exitCode !== null) {
      throw new Error(`server exited before becoming healthy: ${server.exitCode}`);
    }
    try {
      const response = await fetch(`${baseUrl}/health`);
      if (response.ok) {
        healthy = true;
        break;
      }
    } catch {
      // The server may still be starting.
    }
    await sleep(250);
  }
  if (!healthy) {
    throw new Error('health endpoint did not become ready');
  }

  const initializeResponse = await postMcp({
    jsonrpc: '2.0',
    id: 1,
    method: 'initialize',
    params: {
      protocolVersion: '2025-03-26',
      capabilities: {},
      clientInfo: { name: 'fib-docker-smoke', version: '1.0.0' },
    },
  });
  const initializeBody = await initializeResponse.text();
  if (!initializeResponse.ok) {
    throw new Error(`initialize failed (${initializeResponse.status}): ${initializeBody}`);
  }
  const initializeResult = parseMcpResponse(initializeBody);
  if (initializeResult.result?.serverInfo?.name !== 'ebay-mcp') {
    throw new Error(`unexpected initialize response: ${initializeBody}`);
  }

  const sessionId = initializeResponse.headers.get('mcp-session-id');
  if (!sessionId) {
    throw new Error('initialize response did not return an MCP session ID');
  }

  const initializedResponse = await postMcp(
    { jsonrpc: '2.0', method: 'notifications/initialized' },
    sessionId,
  );
  if (!initializedResponse.ok) {
    throw new Error(`initialized notification failed: ${initializedResponse.status}`);
  }

  const toolsResponse = await postMcp(
    { jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} },
    sessionId,
  );
  const toolsBody = await toolsResponse.text();
  if (!toolsResponse.ok) {
    throw new Error(`tools/list failed (${toolsResponse.status}): ${toolsBody}`);
  }
  const toolsResult = parseMcpResponse(toolsBody);
  if (!Array.isArray(toolsResult.result?.tools) || toolsResult.result.tools.length === 0) {
    throw new Error(`tools/list returned no tools: ${toolsBody}`);
  }

  console.log(`MCP protocol smoke test passed (${toolsResult.result.tools.length} tools)`);
} finally {
  server.kill('SIGTERM');
}
