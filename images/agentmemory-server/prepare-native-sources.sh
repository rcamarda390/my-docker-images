#!/bin/sh
# Run in an empty build directory. Sources stay on the Trixie ABI when rebuilt.
set -eu

# Debian source archive SHA256 values come from each package's signed .dsc.
# util-linux 2.41.6 is the upstream stable security release; retain Trixie's
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
util-linux util-linux.orig.tar.xz e596083744e746be7d2823b62b43f4418dd7bf56303b4dc09e6fe8112fe3d7ed https://mirrors.edge.kernel.org/pub/linux/utils/util-linux/v2.41/util-linux-2.41.6.tar.xz
util-linux util-linux.debian.tar.xz 5b327ccd22f0f4ed28a389870aa51d04ecedb8693e52a1d122850f2b3188cbf6 https://deb.debian.org/debian/pool/main/u/util-linux/util-linux_2.41.5-0+deb13u1.debian.tar.xz
zlib zlib.orig.tar.gz 7b6903eb019983987b7112eccf90f1703f1c6c0e0cede36564bf611d19ca579d https://deb.debian.org/debian/pool/main/z/zlib/zlib_1.3.dfsg+really1.3.2.orig.tar.gz
zlib zlib.debian.tar.xz 48f7309bccf9c81e9f68a7e22cf06e08a1f70b275535b953632fccb525c5439e https://deb.debian.org/debian/pool/main/z/zlib/zlib_1.3.dfsg+really1.3.2-3.debian.tar.xz
SOURCES

# These two Trixie backports are already in 2.41.6. Prove that before removing
# them from the series; retain every other Debian patch and packaging rule.
(
    cd util-linux
    for patch in \
        upstream/loopdev-use-openat2-RESOLVE_NO_SYMLINKS-for-backing-file.patch \
        upstream/libmount-restrict-source-path-canonicalization-for-non-ro.patch; do
        git apply --reverse --check "debian/patches/$patch"
        grep -Fx "$patch" debian/patches/series
        sed -i "\|^${patch}$|d" debian/patches/series
    done
)

for entry in attr:1:2.6.0-1 acl:2.4.0-1 ncurses:6.6+20260608-2 util-linux:2.41.6-0 zlib:1:1.3.dfsg+really1.3.2-3; do
    package=${entry%%:*}
    version=${entry#*:}
    changelog="$package/debian/changelog"
    {
        revision=1
        if [ "$package" = util-linux ]; then revision=2; fi
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

# Backport upstream fixes for the 2.41.6 libmount build and resolve flags:
# 7e2e010874b10b3aabdc3c4c844c9ffc46a4a374 (missing fileutils.h)
# 20361d66df4d3f32d5e137fe61a55cdf156c91f0 (correct symlink flag)
# Apply after Debian's patches; fail if the pinned source context changes.
cat > /tmp/util-linux-openat2.patch <<'UTIL_LINUX_OPENAT2_PATCH'
diff --git a/libmount/src/hook_idmap.c b/libmount/src/hook_idmap.c
--- a/libmount/src/hook_idmap.c
+++ b/libmount/src/hook_idmap.c
@@ -23,6 +23,7 @@
 
 #include "strutils.h"
 #include "all-io.h"
+#include "fileutils.h"
 #include "namespace.h"
 
 #include "mountP.h"
diff --git a/include/fileutils.h b/include/fileutils.h
--- a/include/fileutils.h
+++ b/include/fileutils.h
@@ -11,6 +11,10 @@
 #include <dirent.h>
 #include <sys/stat.h>
 
+#ifdef HAVE_LINUX_OPENAT2_H
+# include <linux/openat2.h>
+#endif
+
 #include "c.h"
 
 extern int mkstemp_cloexec(char *template);
@@ -69,7 +73,7 @@ extern int ul_openat_resolve(int dirfd, const char *path, int flags,
 			     mode_t mode, unsigned long long resolve);
 
 #ifndef RESOLVE_NO_SYMLINKS
-# define RESOLVE_NO_SYMLINKS	0x02
+# define RESOLVE_NO_SYMLINKS	0x04
 #endif
 #ifndef RESOLVE_BENEATH
 # define RESOLVE_BENEATH	0x08
diff --git a/lib/fileutils.c b/lib/fileutils.c
--- a/lib/fileutils.c
+++ b/lib/fileutils.c
@@ -19,10 +19,6 @@
 #include <fcntl.h>
 #include <errno.h>
 
-#ifdef HAVE_LINUX_OPENAT2_H
-# include <linux/openat2.h>
-#endif
-
 #include "c.h"
 #include "all-io.h"
 #include "fileutils.h"
UTIL_LINUX_OPENAT2_PATCH
(
    cd util-linux
    git apply --check /tmp/util-linux-openat2.patch
    git apply /tmp/util-linux-openat2.patch
)

# prepare-native-sources.sh: extra upstream fixes absent from the pinned releases
# and verify fixes already present in pinned source.
# CVE-2026-3184: preserve the caller's FQDN for PAM_RHOST.
# CVE-2026-76642: v2.41.6 already includes the failed-helper hook guards.
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
        elif git apply --reverse --check "$patch"; then
            echo "Upstream fix already present: $commit"
        else
            echo "Cannot apply or prove upstream fix: $commit" >&2
            exit 1
        fi
    )
done <<'PATCHES'
util-linux 8b29aeb081e297e48c4c1ac53d88ae07e1331984 6c2213341fe4dc23dc0182b8057605af54563ac434f4fa60430d7a483649112e
zlib df84af25dc1942490e1d1c899a07619152a46148 110ff14375733173d8aa54574473424fbd7dfe4b81f1ca34a759c6fe14b15b14
PATCHES

# CVE-2026-76642 is already fixed in the pinned v2.41.6 source. Check the
# security-relevant libmount hunk against upstream, allowing Debian's harmless
# debug-macro difference, and verify cleanup when the post-mount hook is skipped.
patch=/tmp/util-linux-f57cea130839c0af8dc0525274267ae4cfd66bbf.patch
curl --fail --location --silent --show-error --retry 3 \
    https://github.com/util-linux/util-linux/commit/f57cea130839c0af8dc0525274267ae4cfd66bbf.patch \
    -o "$patch"
printf '%s  %s\n' \
    229a079c614cfe551d8b1b0aa09c10d2f051a7fc9b9b1db270eac87fa12e11f5 "$patch" \
    | sha256sum -c -
(
    cd util-linux
    git apply --reverse --check --include='libmount/src/context_mount.c' "$patch"
    grep -Fq 'cleanup after skipped MOUNT_POST hook' libmount/src/hook_loopdev.c
    grep -Fq 'if (hd->loopdev_fd > -1)' libmount/src/hook_loopdev.c
    grep -Fq 'delete_loopdev(cxt, hd);' libmount/src/hook_loopdev.c
)
