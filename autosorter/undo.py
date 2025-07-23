from typing import List
from pathlib import Path
import shutil

from .logger import MoveLogger
from .models import MoveLogEntry, MoveResult
from .utils import unique_path

class UndoManager:
    def __init__(self, root: Path, logger: MoveLogger, dry_run: bool = True):
        self.root = root
        self.logger = logger
        self.dry_run = dry_run

    def undo_batch(self, batch_id: str) -> List[MoveResult]:
        entries: List[MoveLogEntry] = self.logger.load_batch(batch_id)
        results: List[MoveResult] = []
        # Reverse order to better handle nested moves (not crucial here, but safe)
        for e in reversed(entries):
            src_now = e.dst
            dst_restore = e.src

            if not src_now.exists():
                results.append(MoveResult(src_now, dst_restore, performed=False, reason="missing source for undo"))
                continue

            final_dst = dst_restore
            if final_dst.exists():
                final_dst = unique_path(final_dst)
                reason = "restore name conflict"
            else:
                reason = ""

            if self.dry_run:
                results.append(MoveResult(src_now, final_dst, performed=False, reason=reason))
                continue

            final_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_now), str(final_dst))
            results.append(MoveResult(src_now, final_dst, performed=True, reason=reason))

        return results
