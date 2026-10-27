"""Copy the shared removal tool into this image's build context.

Run from the repository root (build-image.yml's prepare_script does this; for a
local build run it before `docker build`). The generated copy is not committed.
"""
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[2]
shutil.copyfile(root / "tools" / "image_removals.py", root / "images" / "headroom-mcp" / "image_removals.py")
