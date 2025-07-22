from autosorter.utils import ensure_path
from autosorter.scanner import FolderScanner

def main():
    folder = input("Folder to scan: ").strip()
    root = ensure_path(folder)
    scanner = FolderScanner(root, recursive=True)
    files = scanner.scan()

    print(f"Found {len(files)} files.")
    for f in files[:20]:  # show first 20
        print(f"{f.ext:6}  {f.size:8}  {f.path}")

if __name__ == "__main__":
    main()
