from pathlib import Path
import shutil
from .errors import *

def ensure_path(path_str: str) -> Path:
    """Return a resolved Path object and ensure it exists."""
    p = Path(path_str).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {p}")
    return p


def unique_path(dest: Path) -> Path:
    """
    If dest exists, append ' (1)', ' (2)', ... before the suffix.
    Returns a Path that does not exist.
    """
    if not dest.exists():
        return dest

    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    i = 1
    while True:
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def validate_source_dest(src: Path, dest: Path) -> None:
    if not src.exists() or not src.is_dir():
        raise InvalidPathError(f"Source folder invalid: {src}")
    if not dest.exists() or not dest.is_dir():
        raise InvalidPathError(f"Destination folder invalid: {dest}")
    # Prevent moving into a subfolder of itself (infinite nesting)
    try:
        src_rel = dest.resolve().relative_to(src.resolve())
        # If above didn't raise, dest is inside src
        raise InvalidPathError("Destination cannot be inside source folder.")
    except ValueError:
        pass  # OK

def check_free_space(dest: Path, required_bytes: int) -> None:
    total, used, free = shutil.disk_usage(dest)
    if free < required_bytes:
        raise AutoSorterError("Not enough disk space to move files.")