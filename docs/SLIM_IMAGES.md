# Slim payload images — design + findings

Status: proposal. First candidate: archify.

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

## 6. Open points / need user

- archify needs Node in target. Which image gets it? ai-cli-runner (Wolfi, no Node) → add `nodejs` apk (new scan surface) or slim image bundles a Node binary too (then Node scanned in slim image).
- Which target image consumes first? Changes §5 choice.
- Docker Hub mirror too, or GHCR only? Default per repo policy = both.
- Does Artifactory remote repo proxy ghcr.io / docker.io on the air-gapped side? Determines build-time `COPY --from`.

## 7. Proposed `images/slim-archify/` (not yet created)

```dockerfile
FROM alpine/git@sha256:<pin> AS fetch
ARG ARCHIFY_VERSION=3.0.1
ARG ARCHIFY_COMMIT=<sha for tag>
RUN git clone https://github.com/tt-a1i/archify /src && cd /src \
 && git checkout "$ARCHIFY_COMMIT" \
 && test "$(git describe --tags --exact-match)" = "v$ARCHIFY_VERSION" \
 && mkdir /payload && cp -a archify/. /payload/ && cp LICENSE /payload/ \
 && rm -rf /payload/test            # optional; keep manifests
# build-time proof: runs with no install
FROM node:24-trixie-slim@sha256:<pin> AS verify
COPY --from=fetch /payload /payload
RUN node /payload/bin/archify.mjs doctor
FROM scratch
COPY --from=fetch /payload /payload
LABEL slim.payload.software=archify slim.payload.version=3.0.1 slim.payload.install=none
```

`image.yaml`: `name: slim-archify`, `upstream_version: 3.0.1`, `revision: 1`, `build_args: {ARCHIFY_COMMIT: ...}`, `publish: {ghcr: true, dockerhub: true, latest: false}`. Smoke test: `scratch` has no shell → smoke via verify stage (above), shared workflow smoke must be skipped/overridden for this image.

## Next steps

1. User answers §6.
2. Create `images/slim-archify/`, caller workflow, pin commit for tag `v3.0.1`.
3. Build, Xray scan slim image, consume in target, re-scan.
