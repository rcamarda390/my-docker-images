# slim-archify — payload instructions

Baked at `/slim/AGENT.md`. Read first.

## What

- `archify` skill 3.0.1 (Node ESM scripts, MIT) + `node` binary. Copy-only. NO install step.
- Trimmed: no `test/`, no example HTML (~3.7 MB). Kept: everything `doctor` requires.
- Node kept in payload on purpose: internal Artifactory Node may be old. Payload node = known version.
- Method: `copy` (see `manifest.json` → `method`).

## Layout

```text
/slim/AGENT.md        this file
/slim/manifest.json   machine facts: versions, method, needs
/slim/payload/archify skill folder (has bin/archify.mjs, SKILL.md, package.json, package-lock.json)
/slim/payload/node    bin/node + LICENSE (node only, no npm)
```

## Use (build time, preferred)

```dockerfile
COPY --from=docker.io/rcamarda390/slim-archify:3.0.1-v1@sha256:<digest> /slim/payload/ /opt/slim/
RUN ln -s /opt/slim/node/bin/node /usr/bin/node
# skill install for Claude Code:
RUN mkdir -p /home/<user>/.claude/skills && cp -a /opt/slim/archify /home/<user>/.claude/skills/archify
```

Always pin by digest. Digest must be the one Xray scanned.

## Use (runtime, optional)

Docker Engine 28+:

```bash
docker run --mount type=image,source=docker.io/rcamarda390/slim-archify:3.0.1-v1@sha256:<digest>,target=/opt/slimroot,readonly ...
# files at /opt/slimroot/slim/payload/...
```

## Target needs

- linux/amd64, glibc. Shared libs node needs: see `manifest.json` → `node.needs` (libstdc++, libgcc_s, libc, libm).
- Wolfi: `apk add libstdc++` if missing. Debian-slim has them.
- Do NOT delete `package.json`/`package-lock.json`. Xray reads them.

## Run

```bash
node /opt/slim/archify/bin/archify.mjs doctor
node /opt/slim/archify/bin/archify.mjs render architecture in.json out.html
```

## Gotchas

- archify update check does GET to tt-a1i.github.io. Air-gap: fails, reminder only. Not an error.
- No npm install ever needed. If something asks for it, something is wrong.
