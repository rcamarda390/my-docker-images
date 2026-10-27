#!/usr/bin/env python3
"""Closure-aware removal of unused Debian packages, plus the removal manifest.

An image declares what it removes in images/<name>/removals.yaml. In the build
this tool:

1. computes the installed reverse-dependency closure of the declared packages
   (Depends and Pre-Depends) and fails if the closure holds a package the
   manifest does not declare, so every removed package has explicit evidence;
2. proves no ELF under the runtime roots, and no entrypoint, needs anything the
   closure would delete;
3. deletes the closure's files and dpkg records directly. No maintainer scripts
   run, so no stubs for debconf, perl or coreutils are needed and no
   `dpkg --force-depends` leaves broken dependencies behind;
4. proves every retained package still has its dependencies and every retained
   ELF still resolves, then writes /etc/image-removals.json.

Limits: dlopen()ed libraries are invisible to the ELF check; the image's smoke
tests are the proof for those.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

import yaml

CATEGORIES = {"unused-runtime", "build-only", "no-fix", "replaced"}
SHELL_BUILTINS = {
    "echo", "printf", "test", "[", "pwd", "kill", "exec", "exit", "export", "set",
    "cd", "read", "eval", "true", "false", "umask", "wait", "trap", "shift", "unset",
    "readonly", "return", "command", "type", "ulimit", "alias", "break", "continue",
    "getopts", "hash", "local", "times", "if", "then", "else", "fi", "case", "esac",
    "for", "do", "done", "while", "until", "in",
}
INFO_EXTENSIONS = {
    "list", "md5sums", "conffiles", "shlibs", "symbols", "triggers", "postinst",
    "postrm", "preinst", "prerm", "templates", "config",
}


# --------------------------------------------------------------------------
# dpkg database
# --------------------------------------------------------------------------
def parse_status(path):
    """Return ({name: package}, ordered stanza list) for installed packages."""
    with open(path, encoding="utf-8") as stream:
        text = stream.read()
    stanzas = [s for s in re.split(r"\n\n+", text.strip("\n")) if s.strip()]
    packages = {}
    for stanza in stanzas:
        fields = {}
        key = None
        for line in stanza.splitlines():
            if line[:1] in (" ", "\t") and key:
                fields[key] += "\n" + line
            elif ":" in line:
                key, _, value = line.partition(":")
                fields[key] = value.strip()
        if not fields.get("Status", "").endswith(" installed"):
            continue
        packages[fields["Package"]] = {
            "name": fields["Package"],
            "version": fields.get("Version", ""),
            "arch": fields.get("Architecture", ""),
            "depends": fields.get("Depends", "") + "," + fields.get("Pre-Depends", ""),
            "provides": fields.get("Provides", ""),
        }
    return packages, stanzas


def stanza_name(stanza):
    match = re.match(r"Package:\s*(\S+)", stanza)
    return match.group(1) if match else None


def relation_groups(value):
    """'a (>= 1) | b, c:any' -> [['a', 'b'], ['c']]."""
    groups = []
    for part in value.split(","):
        names = [re.match(r"\s*([A-Za-z0-9+.\-]+)", alt).group(1)
                 for alt in part.split("|") if re.match(r"\s*([A-Za-z0-9+.\-]+)", alt)]
        if names:
            groups.append(names)
    return groups


def providers(packages, removed):
    """Map every satisfiable name to the retained packages that satisfy it."""
    result = {}
    for name, package in packages.items():
        if name in removed:
            continue
        result.setdefault(name, set()).add(name)
        for group in relation_groups(package["provides"]):
            for virtual in group:
                result.setdefault(virtual, set()).add(name)
    return result


def unsatisfied(packages, removed):
    """[(package, group)] for retained packages with a dependency nobody provides."""
    available = providers(packages, removed)
    broken = []
    for name, package in packages.items():
        if name in removed:
            continue
        for group in relation_groups(package["depends"]):
            if not any(alt in available for alt in group):
                broken.append((name, group))
    return broken


def closure(packages, declared):
    """Declared packages plus every retained package that loses a dependency."""
    present = {name for name in declared if name in packages}
    already_broken = {(n, tuple(g)) for n, g in unsatisfied(packages, set())}
    removed = set(present)
    while True:
        grew = {n for n, g in unsatisfied(packages, removed)
                if (n, tuple(g)) not in already_broken and n not in removed}
        if not grew:
            return removed
        removed |= grew


# --------------------------------------------------------------------------
# file ownership and ELF checks
# --------------------------------------------------------------------------
def normalize(root, path):
    """Resolve the parent directory (usrmerge symlinks) but not the file itself."""
    rel = path.lstrip("/")
    directory, base = os.path.split(os.path.join(root, rel))
    return os.path.join(os.path.realpath(directory), base)


def info_stems(packages_by_name, name):
    package = packages_by_name[name]
    return {name, f"{name}:{package['arch']}"}


def owner_map(root, packages):
    owners = {}
    info = os.path.join(root, "var/lib/dpkg/info")
    for name in packages:
        for stem in info_stems(packages, name):
            listing = os.path.join(info, stem + ".list")
            if not os.path.exists(listing):
                continue
            with open(listing, encoding="utf-8") as stream:
                for line in stream:
                    path = line.rstrip("\n")
                    if path in ("", "/."):
                        continue
                    owners.setdefault(normalize(root, path), set()).add(name)
    return owners


def is_elf(path):
    try:
        with open(path, "rb") as stream:
            return stream.read(4) == b"\x7fELF"
    except OSError:
        return False


def elf_files(root, roots, extra):
    found = set(extra)
    for base in roots:
        for directory, _, names in os.walk(os.path.join(root, base.lstrip("/"))):
            for filename in names:
                path = os.path.join(directory, filename)
                if os.path.isfile(path) and not os.path.islink(path) and is_elf(path):
                    found.add(path)
    return sorted(found)


def find_loader():
    """The dynamic loader ldd drives; calling it directly needs no shell script
    and no helper command that the removal closure might delete."""
    for pattern in ("/lib64/ld-linux*.so*", "/lib/ld-linux*.so*", "/lib/*-linux-gnu/ld-linux*.so*"):
        found = sorted(glob.glob(pattern))
        if found:
            return found[0]
    return None


def run_ldd(path):
    """Resolved library paths and unresolved names for one ELF."""
    loader = find_loader()
    command = [loader, "--list", path] if loader else ["/bin/sh", "/usr/bin/ldd", path]
    result = subprocess.run(command, capture_output=True, text=True)
    output = result.stdout + result.stderr
    resolved = set(re.findall(r"=>\s+(/\S+)", output)) | set(re.findall(r"^\s*(/\S+)\s+\(0x", output, re.M))
    missing = re.findall(r"^\s*(\S+)\s+=>\s+not found", output, re.M)
    return resolved, missing


def elf_dependents(root, files, doomed_paths, ldd=run_ldd):
    """{elf: [needed doomed library]} and {elf: [unresolved names]}."""
    needs, unresolved = {}, {}
    for path in files:
        resolved, missing = ldd(path)
        if missing:
            unresolved[path] = missing
        hit = sorted(lib for lib in resolved if normalize(root, lib) in doomed_paths)
        if hit:
            needs[path] = hit
    return needs, unresolved


def entrypoint_commands(path, doomed_basenames):
    """Doomed command names appearing as words in an entrypoint script."""
    with open(path, encoding="utf-8", errors="replace") as stream:
        text = "".join(line for line in stream if not line.lstrip().startswith("#"))
    words = set(re.findall(r"[A-Za-z0-9._+\-\[]+", text)) - SHELL_BUILTINS
    return sorted(words & doomed_basenames)


def shebang_targets(root, roots, extra):
    """{script: interpreter} for executable scripts in bin/ dirs and the entrypoints."""
    targets = {}
    paths = set(extra)
    for base in roots:
        for directory, _, names in os.walk(os.path.join(root, base.lstrip("/"))):
            if os.path.basename(directory) in ("bin", "sbin"):
                paths.update(os.path.join(directory, n) for n in names)
    for path in paths:
        if os.path.islink(path) or not os.path.isfile(path) or not os.access(path, os.X_OK):
            continue
        try:
            with open(path, "rb") as stream:
                head = stream.read(128)
        except OSError:
            continue
        words = head[2:].split(b"\n", 1)[0].decode("utf-8", "replace").split() if head.startswith(b"#!") else []
        if words and words[0].startswith("/"):
            targets[path] = words[0]
    return targets


# --------------------------------------------------------------------------
# manifest
# --------------------------------------------------------------------------
def load_manifest(path):
    with open(path, "rb") as stream:
        raw = stream.read()
    data = yaml.safe_load(raw)
    allowed = {"schema_version", "image", "verified_against", "runtime_roots",
               "runtime_executables", "entrypoints", "packages", "paths"}
    unknown = set(data) - allowed
    if unknown:
        raise SystemExit(f"manifest has unknown keys: {sorted(unknown)}")
    if data.get("schema_version") != 1:
        raise SystemExit("unsupported manifest schema_version")
    for key in ("packages", "paths"):
        for item in data.get(key) or []:
            if item.get("category") not in CATEGORIES:
                raise SystemExit(f"{key} entry {item!r}: category must be one of {sorted(CATEGORIES)}")
            if not item.get("reason") or not item.get("evidence"):
                raise SystemExit(f"{key} entry {item!r}: reason and evidence are required")
    data["_sha256"] = hashlib.sha256(raw).hexdigest()
    return data


# --------------------------------------------------------------------------
# apply
# --------------------------------------------------------------------------
def remove_package(root, packages, name, owners, doomed):
    info = os.path.join(root, "var/lib/dpkg/info")
    deleted = 0
    for stem in info_stems(packages, name):
        listing = os.path.join(info, stem + ".list")
        if not os.path.exists(listing):
            continue
        with open(listing, encoding="utf-8") as stream:
            entries = [line.rstrip("\n") for line in stream if line.strip() and line.strip() != "/."]
        directories = []
        for entry in entries:
            path = normalize(root, entry)
            if os.path.isdir(path) and not os.path.islink(path):
                directories.append(path)
                continue
            if owners.get(path, set()) - doomed:
                continue
            if os.path.lexists(path):
                os.unlink(path)
                deleted += 1
        for path in sorted(directories, key=len, reverse=True):
            if owners.get(path, set()) - doomed:
                continue
            try:
                os.rmdir(path)
            except OSError:
                pass
    for filename in os.listdir(info):
        stem, _, extension = filename.rpartition(".")
        if extension in INFO_EXTENSIONS and stem in info_stems(packages, name):
            os.unlink(os.path.join(info, filename))
    return deleted


def rewrite_status(root, stanzas, doomed):
    path = os.path.join(root, "var/lib/dpkg/status")
    keep = [s for s in stanzas if stanza_name(s) not in doomed]
    with open(path + ".new", "w", encoding="utf-8") as stream:
        stream.write("\n\n".join(keep) + "\n\n")
    os.replace(path + ".new", path)


def expand_paths(root, pattern):
    return sorted(glob.glob(os.path.join(root, pattern.lstrip("/"))))


def apply(manifest_path, root, output, mode, dry_run, ldd=run_ldd, check_elf=True):
    manifest = load_manifest(manifest_path)
    status_file = os.path.join(root, "var/lib/dpkg/status")
    packages, stanzas = parse_status(status_file)
    skipped = []
    declared = {}
    for item in manifest.get("packages") or []:
        if mode == "baseline" and item.get("requires_carry"):
            skipped.append({"name": item["name"], "reason": "requires a CVE carry that baseline builds omit"})
            continue
        declared[item["name"]] = item
    absent = sorted(n for n in declared if n not in packages)
    for name in absent:
        print(f"note: declared package {name} is not installed; nothing to remove")
    doomed = closure(packages, declared)
    undeclared = sorted(doomed - set(declared))
    path_items = manifest.get("paths") or []
    planned_paths = {item["path"]: expand_paths(root, item["path"]) for item in path_items}
    doomed_files = [m for matches in planned_paths.values() for m in matches]
    before_broken = {(n, tuple(g)) for n, g in unsatisfied(packages, set())}
    owners = owner_map(root, packages)
    doomed_paths = {p for p, who in owners.items() if who and who <= doomed}
    broken_runtime = {}
    unresolved_before = {}
    files = []
    if check_elf:
        roots = manifest.get("runtime_roots") or []
        entries = [os.path.join(root, e.lstrip("/")) for e in manifest.get("entrypoints") or []]
        executables = [os.path.join(root, e.lstrip("/")) for e in manifest.get("runtime_executables") or []]
        files = [f for f in elf_files(root, roots, executables)
                 if not any(f == m or f.startswith(m.rstrip("/") + "/") for m in doomed_files)]
        needs, unresolved_before = elf_dependents(root, files, doomed_paths, ldd)
        broken_runtime.update({f"elf:{p}": libs for p, libs in needs.items()})
        doomed_commands = {os.path.basename(p) for p in doomed_paths if "/bin/" in p or "/sbin/" in p}
        for entry in entries:
            hits = entrypoint_commands(entry, doomed_commands)
            if hits:
                broken_runtime[f"entrypoint:{entry}"] = hits
        for script, target in shebang_targets(root, roots, entries).items():
            if normalize(root, target) in doomed_paths:
                broken_runtime[f"shebang:{script}"] = [target]
    # Report every problem at once so one build shows the whole picture.
    if undeclared or broken_runtime:
        if undeclared:
            print("Dependents of the declared packages that the manifest does not declare:", file=sys.stderr)
            for name in undeclared:
                edges = [g for n, g in unsatisfied(packages, doomed - {name}) if n == name]
                print(f"  - {name}  (loses: {edges})", file=sys.stderr)
            print("Declare each with a reason and evidence (stanzas below), or stop removing its dependency:", file=sys.stderr)
            for name in undeclared:
                print(f"  - name: {name}\n    category: unused-runtime\n    reason: dependent of a removed package\n    evidence: []", file=sys.stderr)
        if broken_runtime:
            print("Runtime needs packages in the removal closure; do not remove them:", file=sys.stderr)
            for key, needed in sorted(broken_runtime.items()):
                print(f"  - {key} needs {needed}", file=sys.stderr)
        raise SystemExit(1)

    report = {
        "schema_version": 1,
        "image": manifest.get("image"),
        "mode": mode,
        "manifest_sha256": manifest["_sha256"],
        "evidence_verified_against": manifest.get("verified_against"),
        "removed_packages": [
            {"name": n, "version": packages[n]["version"], "category": declared[n]["category"],
             "reason": declared[n]["reason"], "evidence": declared[n]["evidence"],
             "cves": declared[n].get("cves", [])}
            for n in sorted(doomed)],
        "kept_for_baseline": skipped,
        "removed_paths": [
            {"path": item["path"], "matched": len(planned_paths[item["path"]]), "category": item["category"],
             "reason": item["reason"], "evidence": item["evidence"]} for item in path_items],
        "audit": {"closure_size": len(doomed), "undeclared_dependents": 0},
    }
    if dry_run:
        print(json.dumps(report, indent=2))
        return report

    for name in sorted(doomed):
        remove_package(root, packages, name, owners, doomed)
    rewrite_status(root, stanzas, doomed)
    for item in path_items:
        for matched in planned_paths[item["path"]]:
            # Python-native: coreutils (rm) may already be in the removed closure.
            if os.path.isdir(matched) and not os.path.islink(matched):
                shutil.rmtree(matched)
            elif os.path.lexists(matched):
                os.unlink(matched)

    remaining, _ = parse_status(status_file)
    still_broken = [b for b in unsatisfied(remaining, set()) if (b[0], tuple(b[1])) not in before_broken]
    if still_broken:
        raise SystemExit(f"retained packages have unsatisfied dependencies: {still_broken}")
    gone = [n for n in doomed if n in remaining]
    if gone:
        raise SystemExit(f"packages still installed after removal: {gone}")
    for item in path_items:
        if expand_paths(root, item["path"]):
            raise SystemExit(f"path still present after removal: {item['path']}")
    if check_elf:
        if root == "/":
            subprocess.run(["ldconfig"], check=False)
        _, unresolved_after = elf_dependents(root, files, set(), ldd)
        regressed = {p: m for p, m in unresolved_after.items() if p not in unresolved_before}
        if regressed:
            raise SystemExit(f"ELF files lost libraries after removal: {regressed}")
    report["audit"]["unsatisfied_after"] = 0
    report["audit"]["retained_packages"] = len(remaining)
    os.makedirs(os.path.dirname(os.path.join(root, output.lstrip("/"))), exist_ok=True)
    with open(os.path.join(root, output.lstrip("/")), "w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"Removed {len(doomed)} packages and {sum(len(v) for v in planned_paths.values())} paths; "
          f"{len(remaining)} packages retained, none with an unsatisfied dependency.")
    return report


def verify(root, output):
    """Fail unless everything the generated manifest lists is gone and nothing is broken."""
    with open(os.path.join(root, output.lstrip("/")), encoding="utf-8") as stream:
        report = json.load(stream)
    remaining, _ = parse_status(os.path.join(root, "var/lib/dpkg/status"))
    present = [p["name"] for p in report["removed_packages"] if p["name"] in remaining]
    if present:
        raise SystemExit(f"packages recorded as removed are installed: {present}")
    broken = unsatisfied(remaining, set())
    if broken:
        raise SystemExit(f"unsatisfied dependencies: {broken}")
    for item in report["removed_paths"]:
        if glob.glob(os.path.join(root, item["path"].lstrip("/"))):
            raise SystemExit(f"recorded path still present: {item['path']}")
    print(f"Verified {len(report['removed_packages'])} removed packages and {len(report['removed_paths'])} paths.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("apply")
    run.add_argument("--manifest", required=True)
    run.add_argument("--root", default="/")
    run.add_argument("--out", default="/etc/image-removals.json")
    run.add_argument("--mode", choices=("baseline", "full"), required=True)
    run.add_argument("--dry-run", action="store_true")
    check = sub.add_parser("verify")
    check.add_argument("--root", default="/")
    check.add_argument("--out", default="/etc/image-removals.json")
    args = parser.parse_args(argv)
    if args.command == "apply":
        apply(args.manifest, args.root, args.out, args.mode, args.dry_run)
    else:
        verify(args.root, args.out)


if __name__ == "__main__":
    main()
