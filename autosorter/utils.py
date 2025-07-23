from pathlib import Path

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