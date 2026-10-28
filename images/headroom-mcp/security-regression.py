# security-regression.py
"""Exercise the actual patched dependencies; run in builder and runtime."""

import asyncio
import ctypes
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
    "litellm": "1.103.10", "PyJWT": "2.15.1", "mcp": "1.30.0",
    "fsspec": "2026.6.0", "multidict": "6.9.1", "aiohttp": "3.14.5",
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

async def verify_aiohttp():
    from aiohttp import ClientSession, ClientTimeout, web

    async def reply(request):
        return web.json_response({"headroom": "ok"})

    application = web.Application()
    application.router.add_get("/", reply)
    runner = web.AppRunner(application)
    await runner.setup()
    try:
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = runner.addresses[0][1]
        async with ClientSession(timeout=ClientTimeout(total=5)) as client:
            async with client.get(f"http://127.0.0.1:{port}/") as response:
                assert response.status == 200
                assert await response.json() == {"headroom": "ok"}
    finally:
        await runner.cleanup()


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


# CVE-2026-95619: exercise the actual libstdc++ aligned-new implementation,
# rather than assuming that a Debian package version implies applicability.
# The nonthrowing ABI catches bad_alloc inside C++; no exception crosses ctypes.
cpp = ctypes.CDLL("libstdc++.so.6")
allocate = cpp._ZnwmSt11align_val_tRKSt9nothrow_t
allocate.argtypes = (ctypes.c_size_t, ctypes.c_size_t, ctypes.c_void_p)
allocate.restype = ctypes.c_void_p
release = cpp._ZdlPvSt11align_val_t
release.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
release.restype = None
nothrow = ctypes.addressof(ctypes.c_char.in_dll(cpp, "_ZSt7nothrow"))
maximum = ctypes.c_size_t(-1).value
for size, alignment in ((maximum - 8, 32), (maximum, 8), (maximum, 32),
                        (maximum, 1024), (maximum, 65536),
                        (maximum - 1, 16), (maximum - 1025, 1024),
                        (maximum - 1024, 1024), (maximum - 65536, 65536)):
    pointer = allocate(size, alignment, nothrow)
    if pointer:
        release(pointer, alignment)
        raise AssertionError(("Oversized aligned allocation succeeded", size, alignment))
pointer = allocate(64, 32, nothrow)
assert pointer and pointer % 32 == 0
release(pointer, 32)
print("CVE-2026-95619: oversized allocations rejected; ordinary allocation passed")

if sys.argv[1] == "runtime":
    asyncio.run(verify_aiohttp())
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
