from pathlib import Path
from datetime import datetime

from autosorter.utils import ensure_path
from autosorter.scanner import FolderScanner
from autosorter.classifier import RuleSet, Classifier
from autosorter.mover import SafeMover
from autosorter.logger import MoveLogger
from autosorter.undo import UndoManager
from autosorter.models import MoveLogEntry

def ask_yes_no(prompt: str) -> bool:
    return input(prompt + " [y/N]: ").strip().lower() == "y"

def organize_flow():
    source = ensure_path(input("Source folder to organize: ").strip())
    dest_input = input("Destination root (blank = same as source): ").strip()
    dest_root = ensure_path(dest_input) if dest_input else source

    rules_file = input("Path to rules.json (leave empty for defaults): ").strip() or None
    rules_path = Path(rules_file).expanduser().resolve() if rules_file else None

    # Scan
    scanner = FolderScanner(source, recursive=True)
    files = scanner.scan()

    # Classify
    rule_set = RuleSet(rules_path)
    classifier = Classifier(rule_set)
    pairs = classifier.assign(files)

    # Dry-run
    mover = SafeMover(dest_root, dry_run=True)
    previews = mover.move_many(pairs)
    print("\n--- DRY RUN --- (first 30 shown)")
    for r in previews[:30]:
        flag = f"({r.reason})" if r.reason else ""
        print(f"{r.src.name:40} -> {r.dst} {flag}")
    print(f"\nTotal files planned: {len(previews)}")

    if not ask_yes_no("Proceed with actual move?"):
        print("Aborted (dry-run only).")
        return

    # Real move
    mover = SafeMover(dest_root, dry_run=False)
    results = mover.move_many(pairs)

    # Log
    batch_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    logger = MoveLogger(dest_root)
    entries = [
        MoveLogEntry(batch_id, r.src, r.dst, datetime.now())
        for r in results if r.performed
    ]
    logger.write_batch(entries)

    moved = len(entries)
    print(f"\nDone. Moved {moved} files. Batch ID: {batch_id}")

def undo_flow():
    dest_root = ensure_path(input("Destination root (where .autosorter lives): ").strip() or ".")
    logger = MoveLogger(dest_root)
    batches = logger.list_batches()
    if not batches:
        print("No batches found.")
        return
    print("Available batches (newest first):")
    for i, b in enumerate(batches, 1):
        print(f"{i}. {b}")
    choice = input("Which batch to undo? (number, blank=1): ").strip()
    idx = int(choice) - 1 if choice else 0
    batch_id = batches[idx]

    undo_mgr = UndoManager(dest_root, logger, dry_run=True)
    previews = undo_mgr.undo_batch(batch_id)
    print("\n--- UNDO DRY RUN ---")
    for r in previews[:30]:
        flag = f"({r.reason})" if r.reason else ""
        print(f"{r.src.name:40} -> {r.dst} {flag}")
    if not ask_yes_no("Perform undo?"):
        print("Undo cancelled.")
        return

    undo_mgr = UndoManager(dest_root, logger, dry_run=False)
    done = undo_mgr.undo_batch(batch_id)
    performed = sum(1 for r in done if r.performed)
    print(f"Undo complete. Restored {performed} files.")

def main():
    print("1) Organize files")
    print("2) Undo last batch (or choose)")
    action = input("Select: ").strip()
    if action == "2":
        undo_flow()
    else:
        organize_flow()

if __name__ == "__main__":
    main()
