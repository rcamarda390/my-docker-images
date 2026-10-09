"""Exercise the installed libraries behind the 2026-10-08 Xray findings."""

import ctypes
import errno
import mmap


libc = ctypes.CDLL(None, use_errno=True)
libc.mprotect.argtypes = (ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int)
libc.mprotect.restype = ctypes.c_int
libc.newlocale.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)
libc.newlocale.restype = ctypes.c_void_p
libc.freelocale.argtypes = (ctypes.c_void_p,)
libc.strfmon.restype = ctypes.c_ssize_t
libc.strfmon_l.restype = ctypes.c_ssize_t

# CVE-2026-19499 / upstream BZ 34510: the padding fits, but the old
# memmove length writes into the inaccessible page. Test both public APIs.
locale = libc.newlocale(1 << 4, b"C", None)  # Linux LC_MONETARY_MASK.
assert locale, "newlocale failed"
try:
    for function in ("strfmon", "strfmon_l"):
        with mmap.mmap(-1, 2 * mmap.PAGESIZE) as pages:
            base = ctypes.addressof(ctypes.c_char.from_buffer(pages))
            guard = base + mmap.PAGESIZE
            assert libc.mprotect(guard, mmap.PAGESIZE, 0) == 0
            try:
                destination = ctypes.c_void_p(guard - 100)
                args = [destination, ctypes.c_size_t(100)]
                if function == "strfmon_l":
                    args.append(ctypes.c_void_p(locale))
                ctypes.set_errno(0)
                result = getattr(libc, function)(
                    *args, ctypes.c_char_p(b"%100n"), ctypes.c_double(1.23)
                )
                assert result == -1 and ctypes.get_errno() == errno.E2BIG, (
                    function, result, ctypes.get_errno()
                )
                # Ordinary formatting must still succeed.
                result = getattr(libc, function)(
                    *args, ctypes.c_char_p(b"%.2n"), ctypes.c_double(1.23)
                )
                assert result == 4 and ctypes.string_at(destination) == b"1.23"
            finally:
                assert libc.mprotect(guard, mmap.PAGESIZE, 3) == 0
finally:
    libc.freelocale(locale)
print("CVE-2026-19499: strfmon and strfmon_l guard-page checks passed")

# CVE-2026-5435: upstream treats TSIG as an unknown RR instead of running
# the unsafe special formatter. Verify that behavior and caller boundaries.
resolver = ctypes.CDLL("libresolv.so.2")
formatter = resolver.ns_sprintrrf
formatter.argtypes = (
    ctypes.c_void_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_int,
    ctypes.c_int, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_size_t,
    ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t,
)
formatter.restype = ctypes.c_int
rdata = b"\0" * 13 + b"\xff\xff\0\0"
message = b"\0" * 12 + rdata
packet = ctypes.create_string_buffer(message)
for size in range(1, 257):
    storage = ctypes.create_string_buffer(b"\xa5" * (size + 64), size + 64)
    result = formatter(
        ctypes.addressof(packet), len(message), b"example.com", 1, 250, 0,
        ctypes.addressof(packet) + 12,
        len(rdata), None, None, ctypes.addressof(storage), size,
    )
    assert storage.raw[size:] == b"\xa5" * 64, (size, result)
    if result >= 0:
        assert b"unknown RR type 250" in storage.value, storage.value
assert result >= 0, "TSIG fallback did not fit the largest test buffer"
print("CVE-2026-5435: TSIG fallback and 256 buffer-boundary checks passed")

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
