# security-regression.py
"""Exercise the actual patched dependencies; run in builder and runtime."""

import asyncio
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from importlib.metadata import version
from pathlib import Path

import tokenizers
from tokenizers import Tokenizer, models
from transformers.utils.hub import get_checkpoint_shard_files

for name, expected in {
    "litellm": "1.101.3", "PyJWT": "2.15.0", "mcp": "1.30.0",
    "fsspec": "2026.6.0", "multidict": "6.9.1",
    "tokenizers": "0.23.2+rcamarda1", "transformers": "5.17.0",
}.items():
    assert version(name) == expected, (name, version(name))

assert tokenizers.__version__ == "0.23.2+rcamarda1", tokenizers.__version__

# PanicException derives from BaseException: catching Exception deliberately
# rejects the original Rust panic while accepting the ordinary OOV error.
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
        raise AssertionError("Malformed BPE merge accepted")
valid = Tokenizer(models.BPE(vocab={"a": 0, "b": 1, "ab": 2}, merges=[("a", "b")]))
assert valid.encode("ab").ids == [2]

with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    root = base / "model"
    root.mkdir()
    index = root / "model.safetensors.index.json"
    outside = base / "outside.safetensors"
    outside.write_bytes(b"outside")
    (root / "linked.safetensors").symlink_to(outside)
    for filename in ("../outside.safetensors", str(outside), "linked.safetensors", r"..\outside.safetensors"):
        index.write_text(json.dumps({"metadata": {}, "weight_map": {"weight": filename}}))
        try:
            get_checkpoint_shard_files(str(root), str(index), local_files_only=True)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Escaping checkpoint accepted: {filename}")
    (root / "nested").mkdir()
    (root / "nested" / "weights.safetensors").write_bytes(b"valid")
    index.write_text(json.dumps({"metadata": {}, "weight_map": {"weight": "nested/weights.safetensors"}}))
    files, metadata = get_checkpoint_shard_files(str(root), str(index), local_files_only=True)
    assert files == [str(root / "nested" / "weights.safetensors")], files
    assert metadata["all_checkpoint_keys"] == ["weight"]

async def verify_mcp():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    parameters = StdioServerParameters(
        command=str(Path(sys.prefix) / "bin" / "headroom"),
        args=["mcp", "serve"], env=dict(os.environ),
    )
    async with asyncio.timeout(20):
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                result = await session.list_tools()
                assert initialized.serverInfo.name == "headroom"
                assert {tool.name for tool in result.tools} >= {
                    "headroom_compress", "headroom_retrieve", "headroom_stats",
                }


if sys.argv[1] == "runtime":
    asyncio.run(verify_mcp())
    assert importlib.util.find_spec("_uuid") is None
    assert uuid.uuid4().version == 4
    assert uuid.uuid1().version == 1
    for command in ("mount", "umount", "nsenter", "flock", "unshare", "logger", "bzip2recover", "nscd", "sort", "uniq", "unexpand", "chown", "env"):
        assert shutil.which(command) is None, command
    for package in ("util-linux", "mount", "bsdutils", "libmount1", "libblkid1", "libsmartcols1", "libuuid1", "nscd", "coreutils"):
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${db:Status-Status}", package],
            capture_output=True, text=True,
        )
        assert result.returncode in (0, 1), result.stderr
        assert result.stdout != "installed", package
    for pattern in ("libmount.so*", "libblkid.so*", "libsmartcols.so*", "libuuid.so*"):
        assert not list(Path("/usr/lib").rglob(pattern)), pattern
    subprocess.run(
        ["/bin/sh", "-c", 'case "$1" in *.*.*.*.*.tar.gz) exit 1;; esac', "verify", "." * 400 + "x"],
        check=True, timeout=5,
    )
    subprocess.run(
        ["/bin/sh", "-c", 'case "$1" in a[bc]*.txt) exit 0;; *) exit 1;; esac', "verify", "abc.txt"],
        check=True, timeout=5,
    )
    for escape in (r"\uFFFF", r"\U7fffffff"):
        output = subprocess.check_output(["/bin/sh", "-c", 'printf "%b" "$1"', "verify", escape], timeout=5)
        assert output == escape.encode(), output
    for search in ("example.com " + "a" * 244, "a" * 256 + " example.com"):
        subprocess.run(
            [sys.executable, "-c", "import ctypes; assert ctypes.CDLL(None).__res_init() == 0"],
            env={**os.environ, "LOCALDOMAIN": search}, check=True, timeout=5,
        )

print("Headroom security regressions passed")
