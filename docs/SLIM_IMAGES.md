# Slim payload images — design + findings

Status: first image (slim-archify) written, not yet built. See §9.

## Idea

Tiny image carries ONE software payload. Pushed to registry. Artifactory/Xray scans it. Air-gap side pulls through Artifactory. Payload copied into base/runtime image.

Goal = get software scanned by normal gate. Not bypass. Rule: payload MUST keep package metadata so Xray can see components.

## 1. Naming

Repo policy already: immutable tag `<upstream_version>-v<revision>`. Keep it.

| Item | Value |
| --- | --- |
| Repo | `slim-<software>` e.g. `slim-archify` |
| Tag | `<upstream_version>-v<revision>` e.g. `3.0.1-v1` |
| Full | `ghcr.io/rcamarda390/slim-archify:3.0.1-v1` (+ docker.io mirror) |
| Dir | `images/slim-archify/` (`Dockerfile`, `image.yaml`) |
| Workflow | `.github/workflows/build-slim-archify.yml` → shared `build-image.yml` |
| Label | `slim.payload.software`, `slim.payload.version`, `slim.payload.path=/payload`, `slim.payload.install=<none|npm-ci|pip|...>` |

Why not `slim-image-<sw>-<ver>-vX` as repo name: version in repo name = new repo per version, breaks Artifactory retention/promotion rules, breaks `image.yaml` flow. Version belongs in tag. Prefix `slim-` is enough to group them. Change if user wants other prefix.

## 2. archify findings (v3.0.1, MIT)

- It is an agent SKILL, not an app. Folder `archify/` = Node ESM scripts + SKILL.md + assets. 11 MB, 314 files.
- Runtime: Node >=18. Runtime imports only `node:*` builtins. `parse5/saxes/ajv/yaml` are devDependencies, used only by build/test scripts, NOT by `bin/archify.mjs`.
- Verified here: fresh clone, NO `npm install`, Node 22: `node archify/bin/archify.mjs doctor` all `[ok]`, `demo` renders HTML.
- Install upstream = `npx skills add tt-a1i/archify -g` → just copies folder to `~/.claude/skills/` (or `.agents/skills/`, `.config/opencode/skills/`). Needs network. Not needed here.
- Calls home: update check GETs `tt-a1i.github.io/archify/skill-updates/...` — reminder only, never installs. Air-gap: expect failure, harmless; confirm it degrades quietly (test in build).

**Answer: COPY is enough. No install step.** Pure files + Node. Node must exist in target (ai-cli-runner image has Claude Code/Cline as self-contained binaries, NO Node → gap, see §6).

## 3. Methods (pick per software)

| # | Method | Slim contents | Install on inside | Xray sees | Use when |
| --- | --- | --- | --- | --- | --- |
| A | Copy-only | source tree as-is, lockfile/manifest kept | none, `COPY` | files + manifest | pure scripts/skills (archify) |
| B | Build-then-copy | built output of `npm ci`/`pip install --target`/`cargo build`, metadata kept | none, `COPY` | components via metadata + binaries | native-free deps, same libc/arch |
| C | Ship source+lock, install inside | manifest + lockfile only | `npm ci` etc. inside | only manifest, deps NOT scanned until installed | AVOID: inside install pulls unscanned deps, needs registry |
| D | Ship offline wheel/tarball cache | wheels / `npm pack` tgz / vendor dir | offline install from cache | tarballs scanned as packages | native deps needing target-side build |
| E | Static binary | single binary | none | Go/Rust build info, binary | Go/Rust tools |

Rule: whatever gets scanned must equal whatever runs. C breaks that → prefer A/B/D/E. Method per software documented in its `image.yaml` (`payload_method: copy|build-copy|offline-cache|binary`).

## 4. Xray caveats (verify against your Artifactory version)

- Xray indexes Docker image layers; identifies components via package metadata (dpkg/apk db, `package.json`, `.dist-info`, `go.mod` build info, etc.) + SHA matching. Files with no metadata = may be NOT identified = scan "clean" but blind.
- So: KEEP `package.json`, `package-lock.json`, `node_modules/.package-lock.json`, `*.dist-info`. Never strip. Never rename files to dodge detection. That is the compliance line the user asked for.
- Slim base: use `FROM scratch` payload layer or Wolfi/distroless-style base. Fewer OS packages = fewer findings. `FROM scratch` has no OS pkgs → only payload scanned. Good for A/E. For B with native libs needs matching libc in target.
- Payload layer must be deterministic: pinned upstream commit/tag, `COPY --chmod`, fixed mtime (`SOURCE_DATE_EPOCH`), one layer.
- Xray policy applies to the slim image tag. Target image should reference by **digest** (`@sha256:`) so scanned bytes == consumed bytes.
- Xray may also scan the *consuming* image after copy → payload findings reappear there. Expected, fine.

## 5. Consuming the payload (3 ways)

1. Build time (best, immutable):
```dockerfile
COPY --from=ghcr.io/rcamarda390/slim-archify:3.0.1-v1@sha256:<digest> /payload /opt/archify
```
Works only if build host reaches registry/Artifactory remote. Target image then re-scanned as a whole. Fits `images/*/Dockerfile` pattern.

2. Runtime copy (user's idea): entrypoint or init step:
```bash
cid=$(docker create "$SLIM_IMAGE") && docker cp "$cid:/payload/." /opt/archify && docker rm "$cid"
```
Needs Docker socket in the container or run from host. Mutable runtime state → breaks "permanent artifact = image build" rule in AGENT_INSTRUCTIONS. Use only as host-side bootstrap script, not inside container.

3. Image mount: Docker Engine 28+ `--mount type=image,source=<slim>,target=/opt/archify`. Read-only, no copy, no socket. Verify engine version on RHEL host + Artifactory pull path.

Recommend 1 for baked images, 3 for optional add-ons, avoid 2 in containers.

## 6. Standard in-image layout (all slim images)

Every slim image MUST contain, at fixed paths:

```text
/slim/AGENT.md        how to use THIS payload (caveman markdown; method differs per software)
/slim/manifest.json   machine facts: software, version, method, install_step, needs
/slim/payload/<name>  the software (+ supporting software, e.g. payload/node)
```

- `AGENT.md` source lives in `images/slim-<software>/AGENT.md`, baked by Dockerfile.
- Labels: `slim.payload.{software,version,path,method,docs}`.
- Consumers copy `/slim/payload/` only; `AGENT.md` tells them how to wire it.
- Reference images always by digest.

## 7. Node: where it comes from

- Node ships as official nodejs.org release tarballs (GPG-signed `SHASUMS256.txt.asc`). The Docker Hub `node` image = Debian + that tarball (see `nodejs/docker-node` Dockerfile).
- Repo already pins `node:24-trixie-slim@sha256:8ec5d7…` (ai-cli-runner). slim-archify reuses that digest, copies ONLY `/usr/local/bin/node` + LICENSE. No npm/corepack (less to scan).
- Node binary statically bundles V8/OpenSSL/zlib/etc, so Xray flags it by Node version. Needs from target: glibc, libstdc++, libgcc_s. Recorded in `manifest.json` → `node.needs`.
- Bump Node = bump the digest in the Dockerfile + `NODE_MAJOR` if major changes; revision `v+1`.

## 8. Q&A

**Fully install archify, then copy the folder — works?** Yes, and for archify copy IS the install. General rule: tree copy works when install output is relocatable: pure JS/static files, same arch + libc, no absolute paths, no post-install writes outside the tree, no OS package db. Breaks for: apt/apk packages, Python venvs (absolute shebangs — install at same path as target), native modules built vs different libc/Node ABI. Mark per software in `manifest.json` → `method`.

**Ship everything as an install source, Xray it, internal builder installs from it?** Valid (method D). Tradeoff: Xray scans tarballs/wheels, not the final installed tree; install scripts and resolution run later. Safe only with lockfile + integrity hashes + offline install (`npm ci --offline`, `pip --no-index`). Prefer B/A (scan the installed tree = what runs). Use D when target must compile native code. Hybrid: slim image carries BOTH `payload/` (installed tree) and `src/` (tarballs) — doubles scan surface, only if needed.

**Multiple images: build time or startup?**

| | Build time (`COPY --from=slim@sha256`) | Startup (`--mount type=image` / init container) |
| --- | --- | --- |
| Scanned as one unit | yes (final image) | no, composed at run |
| Reproducible/immutable | yes | only if digests pinned in compose |
| Needs registry at | build | every start |
| Swap payload w/o rebuild | no | yes |
| Use for | default; software the image needs to function | optional add-ons, big/rarely-changing payloads |

Default = build time. Startup only when payload truly optional/swappable. Never `docker cp` from inside a container.

## 9. Status

- Created `images/slim-archify/` (Dockerfile, image.yaml, AGENT.md) + `.github/workflows/build-slim-archify.yml`. Publishes GHCR + Docker Hub like bifrost-mcp, tag `3.0.1-v1`, no `latest`.
- NOT yet built: no Docker daemon in authoring sandbox. First proof = run workflow; verify stage in Dockerfile fails build if node major, archify version, `doctor`, or demo render is wrong.
- Pull path: Artifactory pulls from Docker Hub (user confirmed). GHCR copy is secondary.
- Open: which target image consumes first (Wolfi ai-cli-runner needs `libstdc++` apk if absent — check in that image's scan).

## Next steps

1. Dispatch `build-slim-archify.yml`, read first failure if any.
2. Xray scan `docker.io/rcamarda390/slim-archify:3.0.1-v1`.
3. Add consumer `COPY --from` to chosen target image, rescan.
