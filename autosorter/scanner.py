from pathlib import Path
from datetime import datetime
from typing import Iterable, List
from .models import FileRecord

class FolderScanner:
    """Scans a folder (optionally recursively) and yields FileRecord objects."""

    def __init__(self, root: Path, recursive: bool = True, ignore_hidden: bool = True):
        self.root = root
        self.recursive = recursive
        self.ignore_hidden = ignore_hidden

    def scan(self) -> List[FileRecord]:
        paths: Iterable[Path]
        if self.recursive:
            paths = self.root.rglob("*")
        else:
            paths = self.root.glob("*")

        files: List[FileRecord] = []
        for p in paths:
            if not p.is_file():
                continue
            if self.ignore_hidden and any(part.startswith('.') for part in p.parts):
                continue

            stat = p.stat()
            files.append(
                FileRecord(
                    path=p,
                    name=p.name,
                    ext=p.suffix.lower(),
                    size=stat.st_size,
                    mtime=datetime.fromtimestamp(stat.st_mtime),
                )
            )
        return files
