#!/bin/sh
# Run in an empty build directory. Sources stay on the Trixie ABI when rebuilt.
set -eu

# Debian source archive SHA256 values come from each package's signed .dsc.
# util-linux 2.42.4 includes the complete mount hardening; retain Trixie's
# 2.41.5 packaging instead of importing sid's debhelper 14 / libc requirements.
while read -r package archive checksum url; do
    mkdir -p "$package"
    curl --fail --location --silent --show-error --retry 3 "$url" -o "$archive"
    printf '%s  %s\n' "$checksum" "$archive" | sha256sum -c -
    case "$archive" in
        *.debian.tar.xz) tar --no-same-owner -xf "$archive" -C "$package" ;;
        *) tar --no-same-owner -xf "$archive" -C "$package" --strip-components=1 ;;
    esac
done <<'SOURCES'
attr attr.orig.tar.xz 6c8a2148a7b85043b68492bce43316b0e2e214fc4e628c7ede078e76e216330b https://deb.debian.org/debian/pool/main/a/attr/attr_2.6.0.orig.tar.xz
attr attr.debian.tar.xz b2a04e8170dbab934c5d43087deffeaa42168fdf3f31933ac28f62cb7995c6ab https://deb.debian.org/debian/pool/main/a/attr/attr_2.6.0-1.debian.tar.xz
acl acl.orig.tar.xz e661131456d2708a01c614a0f400e11d7d1bfaeb6f3e74b75bb980b72f0161a3 https://deb.debian.org/debian/pool/main/a/acl/acl_2.4.0.orig.tar.xz
acl acl.debian.tar.xz 65931c2fb3e821bda67f8d8d72d77e99ac61502748dcdf38b6805fe89339085e https://deb.debian.org/debian/pool/main/a/acl/acl_2.4.0-1.debian.tar.xz
ncurses ncurses.orig.tar.gz 3b91eb714ba61b9ebfcfe09cf8e7c1c45cf2e8a6282f5887fb942db514ae93bd https://deb.debian.org/debian/pool/main/n/ncurses/ncurses_6.6+20260608.orig.tar.gz
ncurses ncurses.debian.tar.xz 52a49c453121bd90d21edef53903beac9d9d8229e0ef4f49d3b0252e49932f4c https://deb.debian.org/debian/pool/main/n/ncurses/ncurses_6.6+20260608-2.debian.tar.xz
util-linux util-linux.orig.tar.xz fbd62a100ab7bb8746ba0661255c3c48185b1e9021507c624da01fbc696330ec https://mirrors.edge.kernel.org/pub/linux/utils/util-linux/v2.42/util-linux-2.42.4.tar.xz
util-linux util-linux.debian.tar.xz 5b327ccd22f0f4ed28a389870aa51d04ecedb8693e52a1d122850f2b3188cbf6 https://deb.debian.org/debian/pool/main/u/util-linux/util-linux_2.41.5-0+deb13u1.debian.tar.xz
zlib zlib.orig.tar.gz 7b6903eb019983987b7112eccf90f1703f1c6c0e0cede36564bf611d19ca579d https://deb.debian.org/debian/pool/main/z/zlib/zlib_1.3.dfsg+really1.3.2.orig.tar.gz
zlib zlib.debian.tar.xz 48f7309bccf9c81e9f68a7e22cf06e08a1f70b275535b953632fccb525c5439e https://deb.debian.org/debian/pool/main/z/zlib/zlib_1.3.dfsg+really1.3.2-3.debian.tar.xz
SOURCES

# These two Trixie backports are already in 2.42.4. Prove their code hunks
# before removing them (documentation and surrounding code have changed).
# Retain every other Debian patch and packaging rule.
(
    cd util-linux
    for patch in \
        upstream/loopdev-use-openat2-RESOLVE_NO_SYMLINKS-for-backing-file.patch \
        upstream/libmount-restrict-source-path-canonicalization-for-non-ro.patch; do
        git apply --reverse --check -C0 \
            --include='lib/loopdev.c' --include='libmount/src/context.c' \
            "debian/patches/$patch"
        grep -Fx "$patch" debian/patches/series
        sed -i "\|^${patch}$|d" debian/patches/series
    done
)

# Retain Debian's /usr/bin installation choice; upstream renamed only the
# neighboring source-file dependency. Fail rather than silently dropping it.
patch=util-linux/debian/patches/debian/lsfd-usrbin.patch
test "$(grep -Fc 'lsfd-cmd/file.c: errnos.h' "$patch")" -eq 1
sed -i 's@lsfd-cmd/file.c: errnos.h@lsfd-cmd/error.c: errnos.h@' "$patch"
# Do not introduce utilities absent from the retained binary-package manifests.
rules=util-linux/debian/rules
printf '\nCONFOPTS += --disable-getino --disable-copyfilerange\n' >> "$rules"

for entry in attr:1:2.6.0-1 acl:2.4.0-1 ncurses:6.6+20260608-2 util-linux:2.42.4-0 zlib:1:1.3.dfsg+really1.3.2-3; do
    package=${entry%%:*}
    version=${entry#*:}
    changelog="$package/debian/changelog"
    {
        revision=1
        printf '%s (%s+rcamarda%s) trixie; urgency=high\n\n' "$package" "$version" "$revision"
        printf '  * Rebuild fixed upstream sources for the AgentMemory Trixie runtime.\n\n'
        printf ' -- rcamarda390 image build <rcamarda390@users.noreply.github.com>  Tue, 15 Sep 2026 00:00:00 +0000\n\n'
        cat "$changelog"
    } > "$changelog.new"
    mv "$changelog.new" "$changelog"
    dpkg-source --before-build "$package"
done

# Docker builds run as real root. Debian disables setuid environment access,
# so tic ignores TERMINFO and writes Debian-only entries outside debian/tmp.
# Pass the staging directory explicitly; keep ncurses security flags intact.
# Remove this adaptation when Debian's recipe supplies tic -o itself.
rules=ncurses/debian/rules
# Match the literal recipe suffix, not Make's expanded debian/tmp prefix.
if [ "$(grep -Fc '/usr/bin/tic -x debian/' "$rules")" -ne 1 ]; then
    echo "Expected one staged tic command in $rules; recipe changed:" >&2
    grep -n 'tic' "$rules" >&2 || true
    exit 1
fi
sed -i 's@/usr/bin/tic -x debian/@/usr/bin/tic -x -o "$(CURDIR)/debian/tmp/usr/share/terminfo" debian/@' "$rules"
if [ "$(grep -Fc '/usr/bin/tic -x -o "$(CURDIR)/debian/tmp/usr/share/terminfo" debian/' "$rules")" -ne 1 ]; then
    echo "Failed to add explicit tic staging directory in $rules" >&2
    exit 1
fi

# The release includes the openat2 header/flag fixes. Verify the actual
# fallback value, which older stable sources incorrectly set to 0x02.
grep -Eq '^# define RESOLVE_NO_SYMLINKS[[:space:]]+0x04$' util-linux/include/fileutils.h
grep -F '# include <linux/openat2.h>' util-linux/include/fileutils.h
grep -F '#include "fileutils.h"' util-linux/libmount/src/hook_idmap.c

# prepare-native-sources.sh: extra upstream fixes absent from the pinned releases
# and verify fixes already present in pinned source.
# CVE-2026-3184: preserve the caller's FQDN for PAM_RHOST.
# CVE-2026-78408: prove complete cgroup descriptor cleanup in the release.
# CVE-2026-76642: the release includes the failed-helper hook guards.
# CVE-2026-85091: fix stale gzwrite pointers after a non-blocking write stall.
while read -r package commit checksum; do
    patch="/tmp/${package}-${commit}.patch"
    case "$package" in
        util-linux) repo=util-linux/util-linux ;;
        zlib) repo=madler/zlib ;;
    esac
    curl --fail --location --silent --show-error --retry 3 \
        "https://github.com/$repo/commit/$commit.patch" -o "$patch"
    printf '%s  %s\n' "$checksum" "$patch" | sha256sum -c -
    (
        cd "$package"
        if git apply --check "$patch"; then
            git apply "$patch"
        elif git apply --reverse --check -C0 "$patch"; then
            echo "Upstream fix already present: $commit"
        else
            echo "Cannot apply or prove upstream fix: $commit" >&2
            exit 1
        fi
    )
done <<'PATCHES'
util-linux 8b29aeb081e297e48c4c1ac53d88ae07e1331984 6c2213341fe4dc23dc0182b8057605af54563ac434f4fa60430d7a483649112e
util-linux 286dd3ff41526b582ef48830de239dffbaa61f90 bd5b45db9dbfb340622250e92a9f35dbfd9a3574045c4e89e3d034e2391f7697
zlib df84af25dc1942490e1d1c899a07619152a46148 110ff14375733173d8aa54574473424fbd7dfe4b81f1ca34a759c6fe14b15b14
PATCHES

# CVE-2026-76642 is already fixed in the pinned v2.42.4 source. Check the
# security-relevant libmount hunks against upstream, including cleanup when the
# post-mount hook is skipped. Unchanged debug/context lines differ by release.
patch=/tmp/util-linux-f57cea130839c0af8dc0525274267ae4cfd66bbf.patch
curl --fail --location --silent --show-error --retry 3 \
    https://github.com/util-linux/util-linux/commit/f57cea130839c0af8dc0525274267ae4cfd66bbf.patch \
    -o "$patch"
printf '%s  %s\n' \
    229a079c614cfe551d8b1b0aa09c10d2f051a7fc9b9b1db270eac87fa12e11f5 "$patch" \
    | sha256sum -c -
(
    cd util-linux
    git apply --reverse --check -C0 --include='libmount/src/context_mount.c' "$patch"
    # Ignore unchanged context only for the loopdev hunk's debug-macro
    # difference; every added line must still be present in the right block.
    git apply --reverse --check -C0 --include='libmount/src/hook_loopdev.c' "$patch"
)
