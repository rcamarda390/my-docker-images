# Gnosis MCP v17 Xray remediation

The supplied 2026-09-17 Xray report contains 51 findings across 20
components in `rcamarda390/gnosis-mcp:0.14.1-v17`. This change remediates the
applicable findings without deleting dpkg metadata or masking packages from
the scanner.

## Removed components

Runtime dependency tracing showed that the service does not require the
following reported components. Their packages are purged from the flattened
runtime after the optional Python modules that loaded them are removed:

- `apt`, `libapt-pkg7.0`
- `bsdutils`, `util-linux`, `mount`, `libmount1`, `libuuid1`
- `coreutils`, `diffutils`, `sed`, `tar`, `gzip`
- `libacl1`, `libattr1`, `libbz2-1.0`
- `ncurses-base`, `ncurses-bin`, `libncursesw6`, `libtinfo6`, readline
- `libsystemd0`, `libudev1`
- `libc-bin`, `login.defs`

This removes every report entry for those components, including the report's
critical `tar` and `libc-bin` entries. Python's standard library provides the
file, compression, and UUID operations used by Gnosis.

## Replaced or patched components

### zlib

Debian `zlib1g` is replaced with checksum-pinned zlib 1.3.2, which fixes
CVE-2026-27171. The build also checksum-verifies and applies upstream commit
[`df84af25`](https://github.com/madler/zlib/commit/df84af25dc1942490e1d1c899a07619152a46148),
which fixes CVE-2026-85091 after the 1.3.2 release. The image build exercises
zlib's tests, then verifies Python compression and gzip round trips against
the replacement shared library.

### glibc

`libc6` remains load-bearing. The Debian Trixie source is rebuilt as
`2.41-12+deb13u4+rcamarda2` with release/2.41 backports for:

- CVE-2026-5435 and CVE-2026-6238 (`ns_sprintrrf`)
- CVE-2026-6791 and CVE-2026-6368 (`wordexp`)
- CVE-2026-19542 (`tdelete`)
- CVE-2026-19499 (`strfmon`)
- CVE-2026-77117 and CVE-2026-80489 (`iconv`)
- CVE-2026-18374 (`ccs=` handling)

The resolver fixes are narrow source-equivalent patches adapted to Debian's
2.41 context. The remaining upstream patches are checksum-pinned, and the
existing CVE-2026-5450 patch is retained. The build fails if a downloaded
patch checksum changes, or if any patch is neither applicable nor already
present in the Debian source.

CVE-2026-89092 applies to the `nscd` service; neither the `nscd` package nor
its service is present. Debian and upstream classify CVE-2018-20796,
CVE-2019-9192, and CVE-2019-1010022 through CVE-2019-1010025 as disputed or
non-security issues. `libc-bin` removal eliminates CVE-2019-1010022 from this
image, but a scanner may continue to associate the other historical records
with load-bearing `libc6`. They are not hidden or suppressed by this change.

## Open upstream issue

CVE-2026-85670 remains open upstream in `tokenizers`; the report's stated fix
version, 0.23.1, is the affected version already installed, and the latest
0.23.2 source still contains the affected implementation. The air-gap service
does not accept arbitrary tokenizer files: it loads only the fixed model
tokenizer downloaded during the image build. Runtime verification pins
tokenizers 0.23.1 and parses that exact bundled file. Upgrade when upstream
publishes a supported fix.

## Build-time assertions

- all reported, removed packages must not have `installed` dpkg state;
- optional `_bz2`, `_curses`, `_uuid`, and `readline` modules must be absent;
- zlib runtime version must be 1.3.2 and its compression paths must work;
- SQLite FTS5 and `sqlite-vec` must work with the custom SQLite library;
- the bundled tokenizer, ONNX Runtime, OpenSSL, and Gnosis imports must work;
- the glibc package version must match the patched build version.

A new Xray scan of the rebuilt image is required before promotion. This file
records source disposition and build assertions; it is not evidence of a
clean post-build scan.
