// File: images/slim-docker-vsix/verify-ws.cjs
// Regression: close TypedArray must send its actual byte length; fragments bounded.
const assert = require('node:assert/strict');
const {WebSocket, WebSocketServer, Receiver} = require('/src/node_modules/ws');
const timer = setTimeout(() => { throw new Error('WebSocket regression timed out'); }, 5000);
const receiver = new Receiver({isServer: false, maxFragments: 2});
let bounded = false;
receiver.on('error', error => {
  assert.equal(error.code, 'WS_ERR_TOO_MANY_BUFFERED_PARTS');
  bounded = true;
});
const fragment = Buffer.from([0x01, 0x01, 0x61]);
receiver.write(fragment);
receiver.write(Buffer.from([0x00, 0x01, 0x62]));
receiver.write(Buffer.from([0x00, 0x01, 0x63]));
const server = new WebSocketServer({port: 0, skipUTF8Validation: true});
server.on('listening', () => {
  const client = new WebSocket(`ws://127.0.0.1:${server.address().port}`, {skipUTF8Validation: true});
  client.on('close', (code, reason) => {
    assert(bounded, 'fragment limit must reject excess fragments');
    assert.equal(code, 1000);
    assert.deepEqual(reason, Buffer.alloc(80));
    server.close(() => { clearTimeout(timer); console.log('Both ws security regressions passed.'); });
  });
  client.on('error', error => { throw error; });
});
server.on('connection', socket => {
  assert.throws(() => socket._sender.close(1000, new Float32Array(20), false, () => {}), TypeError);
  socket.close(1000, new Uint8Array(80));
});
