from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

@dataclass(frozen=True)
class FileRecord:
    path: Path
    name: str
    ext: str
    size: int
    mtime: datetime

@dataclass(frozen=True)
class MoveResult:
    src: Path
    dst: Path
    performed: bool  # False if dry-run
    reason: str = ""  # e.g., "exists, renamed", "skipped same location"


@dataclass(frozen=True)
class MoveLogEntry:
    batch_id: str
    src: Path
    dst: Path
    timestamp: datetime