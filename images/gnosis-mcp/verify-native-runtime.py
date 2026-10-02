# verify-native-runtime.py
"""Fail the image build if the minimized native runtime is incomplete."""

import ctypes
import gzip
import importlib.util
import math
import ssl
import os
import subprocess
import sys
import uuid
import zlib
from importlib.metadata import version
from pathlib import Path

import onnxruntime
from tokenizers import Tokenizer, models


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

# CVE-2026-102473: the libc-backed matcher must reject an adversarial
# multi-star pattern within a bounded time. Keep ordinary matching intact.
subprocess.run(
    ["/bin/sh", "-c", 'case "$1" in *.*.*.*.*.tar.gz) exit 1;; esac',
     "verify", "." * 400 + "x"], check=True, timeout=5,
)
subprocess.run(
    ["/bin/sh", "-c", 'case "$1" in a[bc]*.txt) exit 0;; *) exit 1;; esac',
     "verify", "abc.txt"], check=True, timeout=5,
)
# CVE-2026-102474: this pinned Debian source has no Unicode escape encoder.
# Its printf leaves these escapes literal, so the reported encoder is absent.
for escape in (r"\uFFFF", r"\U7fffffff"):
    output = subprocess.check_output(
        ["/bin/sh", "-c", 'printf "%b" "$1"', "verify", escape], timeout=5,
    )
    assert output == escape.encode(), output

# CVE-2026-8674: initializing the resolver must not abort when LOCALDOMAIN
# exceeds the legacy 256-byte buffer, whether its first entry fits or not.
# Run each initialization in a fresh process; __res_init reads LOCALDOMAIN.
for search in ("example.com " + "a" * 244, "a" * 256 + " example.com"):
    subprocess.run(
        [sys.executable, "-c",
         "import ctypes; assert ctypes.CDLL(None).__res_init() == 0"],
        env={**os.environ, "LOCALDOMAIN": search},
        check=True,
        timeout=5,
    )

# CVE-2026-85670: malformed BPE merges must raise ordinary errors, not a
# PyO3 PanicException (a BaseException), abort, underflow, or invalid UTF-8.
assert version("tokenizers") == "0.23.1+rcamarda1"
for vocab, merges, prefix in (
    ({"aa": 0, "bb": 1}, [("aa", "bb")], None),
    ({"aa": 0, "b": 1}, [("aa", "b")], "###"),
    ({"a": 0, "é": 1}, [("a", "é")], "x"),
):
    kwargs = {} if prefix is None else {"continuing_subword_prefix": prefix}
    try:
        models.BPE(vocab=vocab, merges=merges, **kwargs)
    except Exception as error:
        assert "out of vocabulary" in str(error).lower(), error
    else:
        raise AssertionError("Malformed BPE merge unexpectedly accepted")
valid = Tokenizer(models.BPE(vocab={"a": 0, "b": 1, "ab": 2}, merges=[("a", "b")]))
assert valid.encode("ab").ids == [2]

tokenizer_path = Path(
    "/gnosis-model-cache/gnosis-mcp/models/MongoDB--mdbr-leaf-ir/tokenizer.json"
)
assert tokenizer_path.is_file()
tokenizer = Tokenizer.from_file(str(tokenizer_path))
assert tokenizer.encode("air-gap runtime verification").ids
# Exercise real offline ONNX inference, not just imports, after omitting
# libgomp1 and replacing tokenizers. This must produce a finite 384D vector.
from gnosis_mcp.local_embed import get_embedder

vector = get_embedder().embed(["air-gap runtime verification"])[0]
assert len(vector) == 384
assert all(math.isfinite(value) for value in vector)
assert abs(sum(value * value for value in vector) - 1) < 0.001
assert "libgomp" not in Path("/proc/self/maps").read_text()

print("Minimized native runtime verification passed")
