import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { once } from "node:events";

const require = createRequire(import.meta.url);
process.env.OTEL_TRACES_SAMPLER = "always_on";
const load = name => process.argv[2] === "cjs" ? require(name) : import(name);
const { WebSocketServer } = await import("ws");
const otel = await load("@iii-dev/helpers/observability");
const { getMeter } = await load("@iii-dev/helpers/observability/internal");
const { W3CBaggagePropagator } = await load("@opentelemetry/core");
const { ROOT_CONTEXT, propagation } = await load("@opentelemetry/api");

// CVE-2026-54285: oversized incoming baggage must be rejected before parsing.
const propagator = new W3CBaggagePropagator();
const getter = { keys: Object.keys, get: (carrier, key) => carrier[key] };
const oversized = propagator.extract(ROOT_CONTEXT, { baggage: "k=" + "x".repeat(8192) }, getter);
assert.equal(propagation.getBaggage(oversized), undefined);
const ordinary = propagator.extract(ROOT_CONTEXT, { baggage: "k=value" }, getter);
assert.equal(propagation.getBaggage(ordinary).getEntry("k").value, "value");

// Exercise all three exporters against a local receiver; no external service.
const receiver = new WebSocketServer({ host: "127.0.0.1", port: 0 });
await once(receiver, "listening");
const frames = [];
const connected = once(receiver, "connection");
receiver.on("connection", socket => socket.on("message", data => frames.push(Buffer.from(data))));
try {
  otel.initOtel({
    enabled: true,
    engineWsUrl: `ws://127.0.0.1:${receiver.address().port}`,
    metricsEnabled: true,
    fetchInstrumentationEnabled: false,
  });
  await connected;
  await otel.withSpan("security-smoke", {}, async span => {
    assert.ok(span.isRecording());
    span.setAttribute("verified", true);
  });
  new otel.Logger().info("security-smoke");
  getMeter().createCounter("security_smoke").add(1);
  await otel.flushOtel();
  const deadline = Date.now() + 5000;
  while (new Set(frames.map(frame => frame.subarray(0, 4).toString())).size < 3 && Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 20));
  }
  for (const prefix of ["OTLP", "MTRC", "LOGS"]) {
    const frame = frames.find(frame => frame.subarray(0, 4).toString() === prefix);
    assert.ok(frame, `${prefix} export missing`);
    const payload = JSON.parse(frame.subarray(4).toString());
    assert.ok(payload.resourceSpans || payload.resourceMetrics || payload.resourceLogs,
      `${prefix} payload invalid`);
  }
  console.log(`OpenTelemetry baggage limit and trace/metric/log exports OK (${process.argv[2] || "esm"})`);
} finally {
  await otel.shutdownOtel();
  for (const socket of receiver.clients) socket.terminate();
  await new Promise(resolve => receiver.close(resolve));
}
