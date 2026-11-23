#!/bin/sh
# Build downstream wheels with normal Python metadata and RECORD hashes.
set -eu

output=$1
python=$2
context=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

fetch_source() {
    url=$1
    digest=$2
    archive="$work/${url##*/}"
    curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location "$url" -o "$archive"
    printf '%s  %s\n' "$digest" "$archive" | sha256sum -c
    tar -xzf "$archive" -C "$work"
}

fetch_source \
    https://files.pythonhosted.org/packages/a1/98/7e457a3b014976887a050561955c0b76e1e7e2d6e27b78ecef2ef80518f2/anyio-4.16.0.tar.gz \
    59bb03251907983d1603d27c3087ddb1e93299ea2163adcdba37899a4fb12ffb
fetch_source \
    https://files.pythonhosted.org/packages/0e/9e/750649904a065007a838981785b2bd8d9ff26154c6c341ac67d0b7f82c68/transformers-5.17.0.tar.gz \
    a153be279169b55b92d8000bf4af294aed684503d091cca7804da2dd8a9de000

patch --batch --forward --fuzz=0 -d "$work/anyio-4.16.0" -p1 \
    < "$context/patches/anyio/0001-execute-pathlike-without-shell.patch"
"$python" "$context/patch-transformers-shards.py" \
    "$work/transformers-5.17.0/src/transformers/utils/hub.py"

"$python" - "$work/transformers-5.17.0" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
for path, marker in (
    (root / "setup.py", 'version="5.17.0"'),
    (root / "src/transformers/__init__.py", '__version__ = "5.17.0"'),
):
    source = path.read_text()
    assert source.count(marker) == 1, path
    path.write_text(source.replace(marker, marker.replace("5.17.0", "5.17.0+rcamarda1")))
PY

cat > "$work/build-constraints.txt" <<'EOF'
packaging==26.3
setuptools==84.1.0
setuptools-scm==8.3.1
EOF
export SOURCE_DATE_EPOCH=315532800
SETUPTOOLS_SCM_PRETEND_VERSION_FOR_ANYIO=4.16.0+rcamarda1 \
    uv build --quiet --python "$python" --wheel --no-sources \
        --build-constraints "$work/build-constraints.txt" --out-dir "$output" "$work/anyio-4.16.0"
uv build --quiet --python "$python" --wheel --no-sources \
    --build-constraints "$work/build-constraints.txt" --out-dir "$output" "$work/transformers-5.17.0"

test -f "$output/anyio-4.16.0+rcamarda1-py3-none-any.whl"
test -f "$output/transformers-5.17.0+rcamarda1-py3-none-any.whl"
sha256sum "$output"/*.whl
