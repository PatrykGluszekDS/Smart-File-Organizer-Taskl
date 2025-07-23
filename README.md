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

* 🔍 **Recursive scan** of any folder
* 🧠 **Rule engine** using default extension → folder mappings or your own `rules.json`
* 🧪 **Dry‑run preview** before touching files
* 📂 **Safe moves** with collision handling (`file (1).txt`, etc.)
* 🧾 **Batch logging** (CSV + JSON) for each run
* ⏪ **Undo** entire batches with a click/command
* 🪟 **Tkinter GUI**: progress bar, stop button, saved settings
* 🧰 Pure **Python standard library** (3.8+)

---

## 📦 Installation

```bash
# Clone the repo
git clone ...
cd autosorter

# (Optional) Create & activate a virtual environment
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

```

> Tip: If you just want to run it, you can also do `python gui.py` or `python main.py` straight away.

---

## 🚀 Quick Start (CLI)

```bash
python main.py
```

You’ll be prompted for:

1. **Source** folder to organize
2. **Destination** root (leave blank to use the same folder)
3. Optional **rules.json** path

* The program prints a **dry‑run**.
* Confirm to perform the real move.
* A **batch ID** is shown; keep it for undo.

### Undo via CLI

Run `python main.py` again → choose option **2** → select a batch to undo.

---

## 🖥️ GUI Usage

```bash
python gui.py
```

1. Pick **source**, **destination**, and (optionally) a rules file.
2. Click **Start**. A dry‑run appears in the log box.
3. Confirm to move files.
4. Use the **Undo** tab to preview and restore batches.

The GUI stores your last-used paths in `~/.autosorter/gui_config.json`.

---

## ⚙️ Custom Rules (`rules.json`)

Create a simple JSON file mapping extensions to folder names:

```json
{
  ".csv": "Spreadsheets",
  ".psd": "Images",
  "no_extension": "Others"
}
```

* Keys should include the dot (`.ext`).
* Special key: `"no_extension"` handles files without a suffix.
* Defaults live in `autosorter/default_rules.py` and are merged with yours (yours override defaults).

---

## 🔄 Logging & Undo

Every move is recorded in `<dest_root>/.autosorter/`:

* `moves.csv` — cumulative log of all batches
* `<batch_id>.json` — snapshot for each run

The undo feature uses these snapshots to move files back (renaming if conflicts occur).

---

## 🧱 Project Structure

```
autosorter/
    __init__.py
    models.py          # Data classes (FileRecord, MoveResult, MoveLogEntry)
    scanner.py         # FolderScanner – collects FileRecord objects
    classifier.py      # RuleSet + Classifier – map file → folder
    default_rules.py   # Built-in extension map
    mover.py           # SafeMover – creates folders & moves files
    logger.py          # MoveLogger – CSV/JSON logging per batch
    undo.py            # UndoManager – restore batches
    utils.py           # Helpers (unique_path, path checks, etc.)
    errors.py          # Custom exceptions
main.py                # CLI entry point
gui.py                 # Tkinter GUI entry point
README.md              # This file
requirements.txt       # (Optional deps)
```

---

## 🛡️ Error Handling & Edge Cases

* **Invalid paths** → clear error messages (`InvalidPathError`)
* **Dest inside source** → blocked to avoid recursive nesting
* **Name collisions** → auto-suffixed `" (1)"`, `" (2)"`, …
* **Permission errors / locked files** → logged & skipped
* **Low disk space** (optional pre-check) → warn/abort
* **Undo missing sources** → noted but run continues
* **Windows long paths** → optional `\\?\` normalization helper

