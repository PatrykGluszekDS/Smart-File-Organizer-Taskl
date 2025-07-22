from autosorter.utils import ensure_path
from autosorter.scanner import FolderScanner
from autosorter.classifier import RuleSet, Classifier
from pathlib import Path

def main():
    folder = input("Folder to scan: ").strip()
    rules_file = input("Path to rules.json (leave empty for defaults): ").strip() or None

    root = ensure_path(folder)
    rules_path = Path(rules_file).expanduser().resolve() if rules_file else None

    scanner = FolderScanner(root, recursive=True)
    files = scanner.scan()

    rule_set = RuleSet(rules_path)
    classifier = Classifier(rule_set)
    assigned = classifier.assign(files)

    print(f"\nPlanned classification (first 30 shown):")
    for rec, dest in assigned[:30]:
        print(f"{rec.path.name:40} -> {dest}")

    print(f"\nTotal files: {len(files)}")

if __name__ == "__main__":
    main()
