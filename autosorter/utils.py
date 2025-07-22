from pathlib import Path

def ensure_path(path_str: str) -> Path:
    """Return a resolved Path object and ensure it exists."""
    p = Path(path_str).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {p}")
    return p
