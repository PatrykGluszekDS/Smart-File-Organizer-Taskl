from pathlib import Path
from typing import List, Tuple
import shutil

from .models import FileRecord, MoveResult
from .utils import unique_path

class SafeMover:
    def __init__(self, output_root: Path, dry_run: bool = True):
        self.output_root = output_root
        self.dry_run = dry_run

    def move_one(self, rec: FileRecord, subfolder: str) -> MoveResult:
        # Build destination folder and file path
        dest_dir = self.output_root / subfolder
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest_file = dest_dir / rec.name

        if dest_file.exists():
            dest_file = unique_path(dest_file)
            reason = "exists, renamed"
        else:
            reason = ""

        # Skip if source and destination are same
        if rec.path == dest_file:
            return MoveResult(rec.path, dest_file, performed=False, reason="same location")

        if self.dry_run:
            return MoveResult(rec.path, dest_file, performed=False, reason=reason)

        # Real move
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(rec.path), str(dest_file))
        return MoveResult(rec.path, dest_file, performed=True, reason=reason)

    def move_many(self, pairs: List[Tuple[FileRecord, str]]) -> List[MoveResult]:
        results: List[MoveResult] = []
        for rec, folder in pairs:
            results.append(self.move_one(rec, folder))
        return results
