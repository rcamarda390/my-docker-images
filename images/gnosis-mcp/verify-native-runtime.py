"""Fail the image build if the minimized native runtime is incomplete."""

import ctypes
import gzip
import importlib.util
import ssl
import uuid
import zlib
from importlib.metadata import version
from pathlib import Path

import onnxruntime
from tokenizers import Tokenizer


# These extension modules pulled in every native package removed for the v17
# findings. Gnosis does not import them; fail if a future base image restores
# one and silently reintroduces the dependency.
for module in ("_bz2", "_curses", "_curses_panel", "_uuid", "readline"):
    assert importlib.util.find_spec(module) is None, f"Unexpected optional module: {module}"

assert uuid.uuid4().version == 4
payload = b"gnosis native runtime check\n" * 100
assert zlib.ZLIB_RUNTIME_VERSION == "1.3.2"
assert zlib.decompress(zlib.compress(payload)) == payload
assert gzip.decompress(gzip.compress(payload)) == payload
ctypes.CDLL("/usr/local/lib/libz.so.1")
ctypes.CDLL("/usr/local/lib/libsqlite3.so.0")
assert ssl.OPENSSL_VERSION.startswith("OpenSSL 3.")
assert onnxruntime.get_device() in {"CPU", "GPU"}

# tokenizers has no upstream CVE-2026-85670 fix yet. The service only loads the
# checksum-bundled, build-time model tokenizer; exercise that exact input and
# reject any accidental version drift until an upstream release is available.
assert version("tokenizers") == "0.23.1"
tokenizer_path = Path(
    "/gnosis-model-cache/gnosis-mcp/models/MongoDB--mdbr-leaf-ir/tokenizer.json"
)
assert tokenizer_path.is_file()
tokenizer = Tokenizer.from_file(str(tokenizer_path))
assert tokenizer.encode("air-gap runtime verification").ids

print("Minimized native runtime verification passed")
