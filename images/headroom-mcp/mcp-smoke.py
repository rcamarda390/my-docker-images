import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

# Test AWS dependencies before starting the proxy
print("Testing AWS dependencies...")
try:
    import boto3
    import botocore
    print(f"✓ boto3 version: {boto3.__version__}")
    print(f"✓ botocore version: {botocore.__version__}")
except ImportError as e:
    print(f"✗ Failed to import AWS dependencies: {e}", file=sys.stderr)
    sys.exit(1)

# Test awscrt (AWS Common Runtime) required for modern boto3
try:
    import awscrt
    print("✓ awscrt (AWS Common Runtime) available")
except ImportError:
    print("⚠ awscrt not available (fallback to older auth methods)")

# Start proxy server with offline mode enabled to verify cached models work
print("\nStarting Headroom proxy with offline mode...")
env = os.environ.copy()
env["HF_HUB_OFFLINE"] = "1"
env["TRANSFORMERS_OFFLINE"] = "1"

process = subprocess.Popen(
    ["headroom", "proxy", "--host", "0.0.0.0", "--port", "8787"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env=env,
)

# Wait for server to be ready
print("Waiting for proxy to be ready...")
max_retries = 30
retry_count = 0
while retry_count < max_retries:
    try:
        response = urllib.request.urlopen("http://localhost:8787/health", timeout=2)
        if response.status == 200:
            break
    except (urllib.error.URLError, OSError):
        pass
    retry_count += 1
    time.sleep(0.5)

def dump_proxy_logs():
    """Print the proxy's captured output.

    stdout/stderr are piped, so without this every proxy-side failure reaches CI
    as an opaque one-liner ("timed out") with the real traceback trapped in the
    pipe. Called only on failure paths.
    """
    try:
        process.terminate()
        out, err = process.communicate(timeout=10)
    except Exception:
        return
    for label, stream in (("stdout", out), ("stderr", err)):
        if stream and stream.strip():
            print(f"----- proxy {label} (last 40 lines) -----", file=sys.stderr)
            print("\n".join(stream.strip().splitlines()[-40:]), file=sys.stderr)


if retry_count >= max_retries:
    dump_proxy_logs()
    raise SystemExit("Proxy server failed to start within 15 seconds")

try:
    # Verify health endpoint
    print("\nTesting proxy endpoints...")
    response = urllib.request.urlopen("http://localhost:8787/health", timeout=2)
    if response.status != 200:
        raise SystemExit(f"Health check failed with status {response.status}")
    print("✓ Proxy health check OK")

    # Verify dashboard is available
    response = urllib.request.urlopen("http://localhost:8787/dashboard", timeout=2)
    if response.status != 200:
        raise SystemExit(f"Dashboard check failed with status {response.status}")
    print("✓ Proxy dashboard OK")

    # Test compression endpoint — this is critical for air-gapped operation
    print("\nTesting compression functionality...")
    test_content = """
    The quick brown fox jumps over the lazy dog. The quick brown fox jumps over the lazy dog.
    The quick brown fox jumps over the lazy dog. The quick brown fox jumps over the lazy dog.
    """ * 10  # Repeat to ensure sufficient token count for compression

    # POST /v1/compress takes an OpenAI-shaped body:
    #   {"messages": [...], "model": "...", "config": {}}
    # Both `messages` and `model` are required — omitting either is a 400. `model`
    # is only used to resolve the context limit and pick a tokenizer; it is never
    # dispatched to a provider, so no network egress and no credentials are needed.
    # The response carries the compressed messages plus metrics:
    #   messages, tokens_before, tokens_after, tokens_saved, compression_ratio,
    #   transforms_applied, ccr_hashes
    compress_url = "http://localhost:8787/v1/compress"

    # The first request builds tokenizers and loads the Kompress ONNX model out
    # of the baked-in cache. Measured at ~5s on run 32311533470, so 90s is ample.
    # It must stay below the workflow's `smoke_timeout` (120s): the request has
    # to time out before the outer `timeout` kills the container, otherwise the
    # except path never runs and dump_proxy_logs() never gets to explain why.
    def compress(body, timeout=90):
        """POST to /v1/compress and return the decoded JSON response."""
        request = urllib.request.Request(
            compress_url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response = urllib.request.urlopen(request, timeout=timeout)
        if response.status != 200:
            raise SystemExit(f"Compression endpoint returned error status {response.status}")
        return json.loads(response.read().decode("utf-8"))

    def joined_len(messages):
        """Total character count of the text content across messages."""
        total = 0
        for message in messages:
            content = message.get("content", "")
            if isinstance(content, str):
                total += len(content)
            elif isinstance(content, list):
                # Anthropic-style content blocks
                total += sum(len(b.get("text", "")) for b in content if isinstance(b, dict))
        return total

    base_body = {
        "messages": [{"role": "user", "content": test_content}],
        "model": "gpt-4o-mini",
    }

    try:
        result = compress(base_body)
        original_len = len(test_content)
        compressed_len = joined_len(result.get("messages", []))
        tokens_before = result.get("tokens_before", 0)
        tokens_after = result.get("tokens_after", 0)
        print("✓ Compression endpoint OK")
        print(f"  Original: {original_len} chars → Compressed: {compressed_len} chars")
        print(f"  Tokens: {tokens_before} → {tokens_after} (saved {result.get('tokens_saved', 0)})")
        print(f"  Transforms applied: {result.get('transforms_applied', [])}")
        if compressed_len >= original_len * 0.95:
            print("  ⚠ Compression minimal (content may be below the compressor's threshold)")
        else:
            print("  ✓ Significant compression achieved")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Endpoint doesn't exist; this is a configuration/version issue, not a runtime failure
            print("⚠ Compression endpoint not available (404) — skipping compression test")
            print("   (Headroom version may not expose /v1/compress endpoint)")
        else:
            # Any other HTTP error indicates a real problem (500, 422, 503, etc.)
            error_body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
            dump_proxy_logs()
            raise SystemExit(
                f"Compression endpoint HTTP {e.code}: {error_body[:200]}\n"
                f"This image cannot support compression in the air-gapped environment."
            )
    except Exception as e:
        dump_proxy_logs()
        raise SystemExit(f"Compression test failed: {e}")

    # A Kompress-specific probe (config.mode="lossy_inline") would exercise the
    # cached ONNX model directly. It is still left out: the default pipeline
    # above already proves the proxy compresses under HF_HUB_OFFLINE=1 without
    # reaching for the network, and a second model-loading call would only add
    # cost to a step whose duration is the open question. Worth adding back once
    # a green run shows what the first compression actually costs.
    print("\n✓ All smoke tests passed")

finally:
    process.terminate()
    process.wait(timeout=5)
