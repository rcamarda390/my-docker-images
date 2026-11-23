# patch-transformers-shards.py
"""Reject escaping checkpoint paths in the pinned Transformers source."""

import sys
from pathlib import Path

if len(sys.argv) == 2:
    path = Path(sys.argv[1])
else:
    import transformers.utils.hub as hub

    path = Path(hub.__file__)
source = path.read_text()
anchor = '    shard_filenames = sorted(set(index["weight_map"].values()))\n'
replacement = r'''
    # ponytail: downstream CVE-2026-75104 guard; remove after an upstream fix.
    from pathlib import PurePosixPath, PureWindowsPath

    def relative_checkpoint_path(value, *, allow_empty=False):
        if not isinstance(value, str) or "\\" in value or "\x00" in value:
            raise ValueError(f"Invalid checkpoint path: {value!r}")
        relative = PurePosixPath(value)
        if (relative.is_absolute() or PureWindowsPath(value).drive
                or ".." in relative.parts or (not relative.parts and not allow_empty)):
            raise ValueError(f"Invalid checkpoint path: {value!r}")
        return relative

    shard_paths = {
        filename: relative_checkpoint_path(filename)
        for filename in index["weight_map"].values()
    }
    subfolder = "" if subfolder is None else subfolder
    checkpoint_subfolder = relative_checkpoint_path(subfolder, allow_empty=True)
    if os.path.isdir(pretrained_model_name_or_path):
        model_root = Path(pretrained_model_name_or_path).resolve()
        checkpoint_root = (model_root / checkpoint_subfolder).resolve()
        if not checkpoint_root.is_relative_to(model_root):
            raise ValueError(f"Checkpoint subfolder escapes model directory: {subfolder!r}")
        for filename, relative in shard_paths.items():
            if not (checkpoint_root / relative).resolve().is_relative_to(checkpoint_root):
                raise ValueError(f"Checkpoint shard escapes model directory: {filename!r}")

    shard_filenames = sorted(shard_paths)
'''
assert source.count(anchor) == 1, "Transformers checkpoint anchor changed"
assert "downstream CVE-2026-75104 guard" not in source, "Already patched"
source = source.replace(anchor, replacement)
compile(source, str(path), "exec")
path.write_text(source)
print("Transformers checkpoint path guard applied")
