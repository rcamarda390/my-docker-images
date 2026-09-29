# Dashboard Recent Requests, Live Feed, and provider labels

Operational guidance for the `headroom-mcp` image (Headroom 0.36.5, commit
`87e71dd10057ff3cbe826bde617682971339e4f8`). Every source citation below was
re-checked against that tag; the behaviour is unchanged from 0.35.0, only the
line numbers moved.

## Symptom

The dashboard renders aggregate telemetry correctly — request counts, prefix
cache hit rates, compression-vs-cache totals, per-model token savings, and
`/stats-history` — but the **Recent Requests** table stays on:

```text
No requests yet. Start using the proxy to see activity here.
```

From the Docker host:

```console
$ curl -s http://127.0.0.1:8787/stats | jq '.recent_requests | type'
"null"
```

## Root cause

This is **not** a build, packaging, telemetry, or Bedrock/LiteLLM instrumentation
problem. It is Headroom's loopback gating on per-request data, interacting with
Docker bridge networking.

`/stats` splits its payload in two. Aggregate counters go to every caller;
per-request metadata is served only to callers Headroom classifies as local:

```python
# headroom/proxy/server.py:4480
include_sensitive = _request_can_view_dashboard_metadata(
    request, trusted_dashboard_client_cidrs
)
...
if not include_sensitive:
    # _build_stats_payload bakes these in; strip for network callers.
    payload.pop("recent_requests", None)   # server.py:4496
    payload.pop("request_logs", None)
```

`_request_is_loopback()` (`server.py:2362`) requires **both** gates to pass:

1. the `Host:` header must name loopback (`127.0.0.1`, `::1`, `localhost`,
   optionally with a port) — this is the DNS-rebinding defence; and
2. `request.client.host` — the TCP peer address — must be a loopback IP, **or**
   fall inside an operator-configured trusted-gateway CIDR
   (`HEADROOM_PROXY_TRUSTED_GATEWAY_CIDRS`, empty by default).

With `docker run -p <hostport>:8788` on a bridge network, traffic from the host
is SNATed by Docker, so the proxy sees the **bridge gateway** address
(`172.17.0.1` or the custom network's gateway), never `127.0.0.1`. Gate 1 passes
for `curl http://127.0.0.1:8787/...`; gate 2 fails; `recent_requests` and
`request_logs` are stripped.

Observed behaviour maps exactly onto the two gates:

| Caller | Peer IP seen by proxy | `Host:` header | Gate 1 | Gate 2 | `recent_requests` |
| --- | --- | --- | --- | --- | --- |
| `curl http://127.0.0.1:8787/stats` on the Docker host | `172.17.0.1` | `127.0.0.1:8787` | pass | **fail** | stripped |
| Browser **on the Docker host** at `http://<server-ip>:8787/dashboard` | `172.17.0.1` | `<server-ip>:8787` | **fail** | fail | stripped |
| in-container probe against `127.0.0.1:8788` (see [Validation](#validation)) | `127.0.0.1` | `127.0.0.1:8788` | pass | pass | **served** |

### Why the aggregates still populate

Both effects run from the same funnel, `record_request_outcome()`:

```text
headroom/proxy/outcome.py:500   await handler.metrics.record_request(...)   # /stats aggregates, history
headroom/proxy/outcome.py:551   request_logger = getattr(handler, "logger", None)
headroom/proxy/outcome.py:559   request_logger.log(RequestLog(...))        # recent_requests source
```

`ProxyConfig.log_requests` defaults to `True` (`headroom/proxy/models.py:343`)
and has no CLI flag or environment override in 0.36.5, so the in-memory request
deque (10 000 entries) is always being filled. Because the aggregate counters are
populating, the per-request log is populating too. The data exists; the response
withholds it.

The distinction is visible in the JSON: a *disabled* logger yields
`"recent_requests": []` (an empty array), whereas the loopback strip removes the
key entirely — which is why `jq '.recent_requests | type'` reports `"null"`.

### The same gate explains the other two observations

`/transformations/feed` and `/v1/telemetry` use the **strict** guard,
`loopback_guard.require_loopback` (`server.py:4546`, `server.py:4820`), which
raises **404 — not 403** so the endpoints stay invisible to scanners
(`headroom/proxy/loopback_guard.py:173-216`). It has no trusted-CIDR escape
hatch. A `GET /v1/telemetry` that is registered in the OpenAPI document but
answers `{"detail":"Not Found"}` is this guard firing, not a missing route.

Note that `{}`-shaped output from the feed is ambiguous without the status code:
a *successful* response is also a JSON object,
`{"transformations": [...], "log_full_messages": false}`. Use `-w '%{http_code}'`
when probing it (see [Validation](#validation)).

## Fix

No image rebuild is required. The change is in the `docker run` invocation.

### Option A — trusted gateway CIDR (recommended for bridge networking)

Derive the subnet from the network the container is actually attached to. Do
**not** inspect `bridge` by name — a container on a user-defined network (any
Compose deployment, or `docker run --network <name>`) has a different gateway,
and allow-listing the default bridge would both leave gate 2 closed and trust an
unrelated network:

```bash
docker inspect -f '{{range $net, $cfg := .NetworkSettings.Networks}}{{$net}} {{$cfg.Gateway}}{{"\n"}}{{end}}' headroom-ai
```

That prints `<network-name> <gateway-ip>` per attachment. Feed the name back in
to get the subnet to allow-list:

```bash
docker inspect -f '{{range $net, $cfg := .NetworkSettings.Networks}}{{$net}}{{"\n"}}{{end}}' headroom-ai \
  | xargs -I{} docker network inspect {} -f '{{.Name}} {{range .IPAM.Config}}{{.Subnet}} {{end}}'
```

Add the subnet that command reports to the run command — `172.17.0.0/16` below is
the default-bridge value, correct only if that is what you actually got:

```bash
-e HEADROOM_PROXY_TRUSTED_GATEWAY_CIDRS=172.17.0.0/16
```

Then reach the dashboard over a **loopback** URL, so gate 1 still passes:

```text
http://127.0.0.1:8787/dashboard
```

A malformed CIDR raises `ValueError` at startup rather than silently disabling
the gate, so a typo fails loudly.

### Option B — remote dashboard by server IP

If the dashboard is opened from another machine, gate 1 can never pass, and
`_request_can_view_dashboard_metadata` (`server.py:2405`) takes over. It requires
all three of:

* the `Host:` header is an **IP literal** (`10.20.30.40:8787`) — a DNS hostname
  is rejected;
* `Origin`/`Referer`, if the browser sends them, match that exact scheme/host/port;
* the address returned by `resolve_client_ip()` falls inside
  `HEADROOM_PROXY_TRUSTED_DASHBOARD_CLIENT_CIDRS`.

**The third bullet is the one that bites.** `resolve_client_ip()`
(`forwarded_headers.py:253`) returns the raw TCP peer address and only
substitutes `X-Forwarded-For` when the peer is itself inside
`HEADROOM_PROXY_TRUSTED_GATEWAY_CIDRS`. Headroom also starts uvicorn with
`proxy_headers=False` (`server.py:5507`) precisely so nothing rewrites
`request.client.host` behind the guard's back. So the CIDR has to match whatever
address actually arrives, which depends on the path the traffic takes:

| Path to the published port | Address the guard matches on | CIDR to allow-list |
| --- | --- | --- |
| Browser on **another machine**, no reverse proxy | the remote client's own IP (Docker's inbound DNAT does not rewrite an external source address) | the client subnet, e.g. `10.20.0.0/16` |
| Browser on the **Docker host** itself, via the server's IP | the bridge gateway — the host-local path is SNATed | the bridge subnet (see the caution below) |
| Behind a reverse proxy that sets `X-Forwarded-For` | the forwarded client IP, **but only if** `HEADROOM_PROXY_TRUSTED_GATEWAY_CIDRS` already covers the proxy's own peer address | the client subnet, plus the gateway CIDR for the proxy |

```bash
-e HEADROOM_PROXY_TRUSTED_DASHBOARD_CLIENT_CIDRS=10.20.0.0/16
```

Do not paper over row 2 by setting the dashboard-client CIDR to the bridge
subnet. Every client reaching the published port over that path shares the
gateway address, so allow-listing it grants per-request metadata to all of them,
not just to you. For a browser on the Docker host, use Option A with a loopback
URL instead — that is exactly the case Option A is for.

Which row applies is a property of your network, not of Headroom, so confirm it
rather than assuming: set the CIDR, load the dashboard from the machine you
actually intend to use, and check `recent_requests` is an array
(see [Validation](#validation)). If it is still `null`, the address the guard saw
was not in the CIDR you set.

Options A and B are independent and can be combined.

### Option C — host networking

`--network host` makes the container share the host's network namespace, so a
host-side client is a genuine loopback peer and every gate passes, including the
strict ones. This is the only configuration in which the **Live Feed** panel and
`/v1/telemetry` work from the host. It gives up port remapping (the proxy binds
`--port 8788` directly on the host) and container network isolation.

### Live Feed limitation

`/transformations/feed` has no CIDR escape hatch, so on a bridge network the
dashboard's Live Feed panel stays empty even after Option A or B. Recent Requests
— the reported symptom — is fixed by A or B; the Live Feed needs Option C or an
in-container client:

```bash
docker exec headroom-ai python -c "import urllib.request,json; print(json.dumps(json.load(urllib.request.urlopen('http://127.0.0.1:8788/transformations/feed?limit=5',timeout=10)),indent=2))"
```

Message bodies in the feed additionally require full message logging, which is
off by default and logs prompt and completion content:

```bash
-e HEADROOM_LOG_MESSAGES=true    # WARNING: logs request/response content
```

Without it the feed still returns entries; `request_messages`,
`compressed_messages`, and `response_content` are `null`.

## Validation

Run these against the deployed container.

**The runtime image has no `curl`.** It is installed in the builder stage only
(`Dockerfile:33`), and the hardened runtime stage never adds it — which is why
`mcp-smoke.py` probes over `urllib`. `docker exec headroom-ai curl ...` fails
with `OCI runtime exec failed: ... executable file not found in $PATH`; piped
into `jq` that surfaces as the misleading
`parse error: Invalid numeric literal at line 1, column 4`. In-container probes
below therefore use `python`, which is on `PATH` via `/opt/venv/bin`. Host-side
probes use `curl` normally.

Baseline — prove the request log is populated, independent of any gate:

```bash
docker exec headroom-ai python -c "import urllib.request,json; r=json.load(urllib.request.urlopen('http://127.0.0.1:8788/stats',timeout=10)).get('recent_requests'); print('type:',type(r).__name__,'count:',len(r) if isinstance(r,list) else 0)"
```

Expect `type: list` and a non-zero count after traffic has flowed. This alone
distinguishes "data missing" from "data withheld".

Then confirm the host-side path before the fix:

```bash
curl -s http://127.0.0.1:8787/stats | jq '.recent_requests | type'   # "null"  -> stripped
```

and after restarting with Option A:

```bash
curl -s http://127.0.0.1:8787/stats | jq '{type: (.recent_requests|type),
                                           count: (.recent_requests|length)}'
# {"type": "array", "count": <n>}
```

Confirm the strict-guard endpoints with status codes, not body shape:

```bash
curl -s -o /dev/null -w 'feed=%{http_code}\n'      http://127.0.0.1:8787/transformations/feed
curl -s -o /dev/null -w 'telemetry=%{http_code}\n' http://127.0.0.1:8787/v1/telemetry
docker exec headroom-ai python -c "
import urllib.request, urllib.error
for path in ('/transformations/feed', '/v1/telemetry'):
    try:
        print(path, urllib.request.urlopen('http://127.0.0.1:8788' + path, timeout=10).status)
    except urllib.error.HTTPError as exc:
        print(path, exc.code)
"
```

`404` from the host with `200` from inside the container confirms the guard
rather than a routing fault.

Confirm prompt caching is unaffected by the change — the fix touches no request
path:

```bash
curl -s http://127.0.0.1:8787/stats | jq '.prefix_cache.by_provider'
```

`cache_read_tokens` and `hit_rate` must match their pre-change values.

## Provider display name

The dashboard label `litellm-bedrock` comes from `LiteLLMBackend.name`
(`headroom/backends/litellm.py:663`), which returns `f"litellm-{self.provider}"`.
`--backend bedrock` is normalized to `litellm-bedrock` in
`headroom/providers/registry.py:223`.

**`--provider-name` does not rename it.** `resolve_display_provider()`
(`headroom/proxy/helpers.py:1128-1146`) reclassifies only requests whose raw
provider is exactly `openai`; every other label, `litellm-bedrock` included, is
returned unchanged. The flag is for OpenAI-compatible upstreams such as
OpenRouter.

Renaming would therefore require a downstream source patch to the `name`
property. That is **not recommended**, because `backend.name` is the value passed
as `provider=` into the outcome funnel, so it is a key — not just a caption — in:

* `/stats` → `requests.by_provider` and `prefix_cache.by_provider`;
* the persisted savings ledger behind `/stats-history` and `/stats-lifetime`;
* Prometheus labels on `/metrics`.

Changing it splits existing history across two provider keys and breaks
continuity of the persisted ledger under `/home/headroom/.headroom`. The label is
cosmetic; the cost of renaming is not. Leave it as `litellm-bedrock`.

## Ruled out

For the record, none of these contribute to the symptom:

* **`--extra proxy` / packaging.** No optional dependency gates request-history
  logging. The logger is `headroom/proxy/request_logger.py`, an in-memory
  `deque`, always present.
* **`HEADROOM_TELEMETRY`.** This is Headroom's *local* TOIN/compression
  collector (`headroom/telemetry/beacon.py:31`), surfaced as `/stats.telemetry`.
  It is unrelated to `recent_requests`, which is fed by the request logger.
  Removing `--no-telemetry` and adding `HEADROOM_TELEMETRY=on` changed the
  `.telemetry` block only.
* **Bedrock/LiteLLM-specific instrumentation.** The provider is a label on a
  shared funnel; the OpenAI, Anthropic, and LiteLLM handlers all reach
  `record_request_outcome()`.
* **Transformation-conditional logging.** Every outcome below HTTP 500 is
  logged, whether or not compression fired.
* **Request-history storage path.** The `recent_requests` source is in-memory and
  never touches the mounted `/home/headroom/.headroom` volume. `--log-file` is
  an additional JSONL sink, not the dashboard's source.

## Security notes

Two items surfaced while tracing this. Neither blocks the fix; both are
deployment decisions for this air-gapped GovCloud runtime.

* `HEADROOM_PROXY_TRUSTED_GATEWAY_CIDRS` is also the gate for honouring
  `X-Forwarded-*` headers. Because every published-port client shares the bridge
  gateway as its peer, allow-listing that subnet means any client that can reach
  the port can forge `X-Forwarded-For`. That value feeds
  `resolve_client_ip()` — used for the Option B dashboard CIDR check and for
  rate-limit attribution — but **not** the `_request_is_loopback` peer check,
  which reads the raw socket address. Scope the CIDR to the bridge subnet, not
  to `0.0.0.0/0`.
* The upload beacon is a separate switch from `HEADROOM_TELEMETRY` and is
  **opt-out, on by default** (`BEACON_DEFAULT_ON = True`,
  `headroom/telemetry/beacon.py:56`). `--no-telemetry` does not disable it. For
  an air-gapped deployment set `HEADROOM_BEACON=off` (or `DO_NOT_TRACK=1`) to
  stop the attempt rather than relying on the network to fail it.

Separately, the container binds `--host 0.0.0.0` with no `HEADROOM_PROXY_TOKEN`,
so the `/v1/*` data-plane routes are reachable unauthenticated by anything that
can reach the published port. Headroom logs a warning about this at startup
(`headroom/proxy/server.py:3370`). The loopback gating described above is what
keeps prompt content and per-request metadata off that surface — which is why
widening it should be done with the narrowest CIDR that works.
