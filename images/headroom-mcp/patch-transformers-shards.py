# patch-transformers-shards.py
"""Reject escaping checkpoint paths in the pinned Transformers 5.17.0."""

from pathlib import Path

import transformers.utils.hub as hub

path = Path(hub.__file__)
source = path.read_text()
anchor = '    shard_filenames = sorted(set(index["weight_map"].values()))\n'
replacement = anchor + '''
    # ponytail: downstream CVE-2026-75104 guard; remove after an upstream fix.
    for filename in shard_filenames:
        if (not isinstance(filename, str) or os.path.isabs(filename)
                or ".." in filename.replace("\\\\", "/").split("/")):
            raise ValueError(f"Unsafe checkpoint shard filename: {filename!r}")
    if os.path.isdir(pretrained_model_name_or_path):
        model_root = os.path.realpath(pretrained_model_name_or_path)
        for filename in shard_filenames:
            resolved = os.path.realpath(os.path.join(model_root, subfolder, filename))
            if os.path.commonpath([model_root, resolved]) != model_root:
                raise ValueError(f"Checkpoint shard escapes model directory: {filename!r}")
'''
assert source.count(anchor) == 1, "Transformers checkpoint anchor changed"
assert "downstream CVE-2026-75104 guard" not in source, "Already patched"
source = source.replace(anchor, replacement)
compile(source, str(path), "exec")
path.write_text(source)
print("Transformers checkpoint path guard applied")
