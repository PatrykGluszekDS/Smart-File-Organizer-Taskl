# Smart file organizer

## Description
Automatically sort files in a folder into subfolders based on extension or rules.

## Getting Started
1. Clone this repository or download the files.
2. Install required packages if necessary.

Keep in mind that the code must be written in OOP.

## Tasks
- Understand how file paths work. Write code to scan files in a folder.
- Classify files by extension (e.g., .jpg, .pdf, etc.).
- Create destination folders and move files using `shutil.move()`.
- Add logging of moved files (source, destination, time).
- Add menu to let user choose which folder to organize.
- Add undo function by keeping a “moved files” history.
- Add a GUI using tkinter: folder selection and start/stop button.
- Add error handling (conflicting names, permission issues).
- Final testing. Create README with instructions and screenshots. Submit as Git repo.

# AutoSorter

Automatically sort files in a folder into subfolders based on file extension or custom rules.  
Includes a **CLI**, a **Tkinter GUI**, **dry‑run mode**, **logging**, and **undo**.

---

## ✨ Features

- Scan a folder (recursively) and classify files using defaults or your own `rules.json`.
- Safe moves with collision handling (`file (1).txt`, etc.).
- **Dry‑run** preview before touching anything.
- Detailed CSV/JSON logging per batch, with a one‑click **undo**.
- Polished GUI (progress bar, stop button, saved settings).
- Works on Windows, macOS, Linux (Python 3.8+).

