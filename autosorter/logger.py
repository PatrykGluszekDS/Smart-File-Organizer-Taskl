import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Iterable, List

from .models import MoveLogEntry

class MoveLogger:
    """Append-only logger. Also writes a JSON file per batch for quick undo."""
    def __init__(self, root: Path):
        self.root = root
        self.meta_dir = self.root / ".autosorter"
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.meta_dir / "moves.csv"

        # Ensure CSV header exists
        if not self.csv_path.exists():
            with self.csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["batch_id", "src", "dst", "timestamp"])

    def write_batch(self, entries: Iterable[MoveLogEntry]) -> None:
        entries = list(entries)
        if not entries:
            return

        # CSV append
        with self.csv_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for e in entries:
                writer.writerow([
                    e.batch_id,
                    str(e.src),
                    str(e.dst),
                    e.timestamp.isoformat(),
                ])

        # JSON snapshot for the batch
        batch_file = self.meta_dir / f"{entries[0].batch_id}.json"
        data = [
            {"src": str(e.src), "dst": str(e.dst), "timestamp": e.timestamp.isoformat()}
            for e in entries
        ]
        batch_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def list_batches(self) -> List[str]:
        """Return batch ids sorted newest→oldest."""
        ids = []
        with self.csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ids.append(row["batch_id"])
        return sorted(set(ids), reverse=True)

    def load_batch(self, batch_id: str) -> List[MoveLogEntry]:
        path = self.meta_dir / f"{batch_id}.json"
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        out: List[MoveLogEntry] = []
        for item in raw:
            out.append(
                MoveLogEntry(
                    batch_id=batch_id,
                    src=Path(item["src"]),
                    dst=Path(item["dst"]),
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                )
            )
        return out
