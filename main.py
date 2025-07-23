from pathlib import Path
from autosorter.utils import ensure_path
from autosorter.scanner import FolderScanner
from autosorter.classifier import RuleSet, Classifier
from autosorter.mover import SafeMover

def ask_yes_no(prompt: str) -> bool:
    return input(prompt + " [y/N]: ").strip().lower() == "y"

def main():
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
        flag = "(rename)" if r.reason else ""
        print(f"{r.src.name:40} -> {r.dst} {flag}")
    print(f"\nTotal files: {len(previews)}")

    if not ask_yes_no("Proceed with actual move?"):
        print("Aborted (dry-run only).")
        return

    # Real move
    mover = SafeMover(dest_root, dry_run=False)
    results = mover.move_many(pairs)

    moved = sum(1 for r in results if r.performed)
    print(f"\nDone. Moved {moved} files.")

if __name__ == "__main__":
    main()
