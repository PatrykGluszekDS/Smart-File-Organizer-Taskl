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
