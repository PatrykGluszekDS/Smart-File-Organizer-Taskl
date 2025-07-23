# gui.py
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from autosorter.utils import ensure_path
from autosorter.scanner import FolderScanner
from autosorter.classifier import RuleSet, Classifier
from autosorter.mover import SafeMover
from autosorter.logger import MoveLogger
from autosorter.undo import UndoManager
from autosorter.models import MoveLogEntry, MoveResult

# ---------- GUI CLASS ----------

class AutoSorterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AutoSorter")
        self.geometry("800x600")

        self._build_ui()

        # State
        self.worker_thread: Optional[threading.Thread] = None
        self.stop_requested = False

    # ----- UI BUILD -----
    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        # Tabs
        self.tab_sort = ttk.Frame(notebook)
        self.tab_undo = ttk.Frame(notebook)
        notebook.add(self.tab_sort, text="Organize")
        notebook.add(self.tab_undo, text="Undo")

        # --- Organize tab widgets ---
        frm = ttk.Frame(self.tab_sort, padding=10)
        frm.pack(fill="x")

        self.src_var = tk.StringVar()
        self.dst_var = tk.StringVar()
        self.rules_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=True)
        self.dry_run_var = tk.BooleanVar(value=True)

        self._file_picker(frm, "Source folder:", self.src_var, row=0, is_dir=True)
        self._file_picker(frm, "Destination root (blank = source):", self.dst_var, row=1, is_dir=True)
        self._file_picker(frm, "Rules JSON (optional):", self.rules_var, row=2, is_dir=False, filetypes=[("JSON", "*.json")])

        ttk.Checkbutton(frm, text="Recursive", variable=self.recursive_var).grid(row=3, column=0, sticky="w")
        ttk.Checkbutton(frm, text="Dry run first", variable=self.dry_run_var).grid(row=3, column=1, sticky="w")

        self.btn_start = ttk.Button(frm, text="Start", command=self.on_start)
        self.btn_start.grid(row=4, column=0, pady=8, sticky="w")
        self.btn_stop = ttk.Button(frm, text="Stop", command=self.on_stop, state="disabled")
        self.btn_stop.grid(row=4, column=1, pady=8, sticky="w")

        # Log box
        self.txt_log = tk.Text(self.tab_sort, height=20, wrap="none")
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=(0,10))
        self._attach_scrollbars(self.txt_log)

        # --- Undo tab ---
        undo_frame = ttk.Frame(self.tab_undo, padding=10)
        undo_frame.pack(fill="x")

        self.undo_root_var = tk.StringVar()
        self._file_picker(undo_frame, "Destination root (.autosorter inside):", self.undo_root_var, row=0, is_dir=True)

        self.btn_list_batches = ttk.Button(undo_frame, text="Load Batches", command=self.on_list_batches)
        self.btn_list_batches.grid(row=1, column=0, sticky="w", pady=5)

        self.lst_batches = tk.Listbox(self.tab_undo, height=8)
        self.lst_batches.pack(fill="x", padx=10, pady=5)

        self.btn_undo_preview = ttk.Button(self.tab_undo, text="Undo (Preview)", command=self.on_undo_preview)
        self.btn_undo_preview.pack(padx=10, pady=(0,5), anchor="w")

        self.btn_undo_run = ttk.Button(self.tab_undo, text="Perform Undo", command=self.on_undo_run, state="disabled")
        self.btn_undo_run.pack(padx=10, pady=(0,10), anchor="w")

        self.txt_undo_log = tk.Text(self.tab_undo, height=15, wrap="none")
        self.txt_undo_log.pack(fill="both", expand=True, padx=10, pady=(0,10))
        self._attach_scrollbars(self.txt_undo_log)

    def _file_picker(self, parent, label, var, row, is_dir=True, filetypes=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
        entry = ttk.Entry(parent, textvariable=var, width=60)
        entry.grid(row=row, column=1, sticky="we", padx=5)
        parent.grid_columnconfigure(1, weight=1)

        def browse():
            if is_dir:
                path = filedialog.askdirectory()
            else:
                path = filedialog.askopenfilename(filetypes=filetypes or [("All files", "*.*")])
            if path:
                var.set(path)
        ttk.Button(parent, text="Browse", command=browse).grid(row=row, column=2, padx=5)

    def _attach_scrollbars(self, text_widget: tk.Text):
        yscroll = ttk.Scrollbar(text_widget.master, orient="vertical", command=text_widget.yview)
        xscroll = ttk.Scrollbar(text_widget.master, orient="horizontal", command=text_widget.xview)
        text_widget.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")

    # ----- Logging -----
    def log(self, msg: str):
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.update_idletasks()

    def log_undo(self, msg: str):
        self.txt_undo_log.insert("end", msg + "\n")
        self.txt_undo_log.see("end")
        self.update_idletasks()

    # ----- Actions -----
    def on_start(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return
        try:
            source = ensure_path(self.src_var.get())
        except Exception as e:
            messagebox.showerror("Error", f"Invalid source: {e}")
            return

        dest_input = self.dst_var.get().strip()
        dest_root = ensure_path(dest_input) if dest_input else source

        rules_path = None
        if self.rules_var.get().strip():
            rules_path = Path(self.rules_var.get()).expanduser().resolve()

        recursive = self.recursive_var.get()
        dry_run = self.dry_run_var.get()

        self.stop_requested = False
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.txt_log.delete("1.0", "end")

        args = (source, dest_root, rules_path, recursive, dry_run)
        self.worker_thread = threading.Thread(target=self._organize_worker, args=args, daemon=True)
        self.worker_thread.start()

    def on_stop(self):
        self.stop_requested = True
        self.log("Stop requested; finishing current file...")

    # Worker thread
    def _organize_worker(self, source: Path, dest_root: Path, rules_path: Optional[Path],
                         recursive: bool, dry_run_first: bool):
        try:
            # Scan
            self.log("Scanning...")
            scanner = FolderScanner(source, recursive=recursive)
            files = scanner.scan()
            self.log(f"Found {len(files)} files.")

            # Classify
            rule_set = RuleSet(rules_path)
            classifier = Classifier(rule_set)
            pairs = classifier.assign(files)

            # DRY RUN
            mover = SafeMover(dest_root, dry_run=True)
            previews = mover.move_many(pairs)
            self.log("--- DRY RUN (showing first 50) ---")
            for r in previews[:50]:
                flag = f" ({r.reason})" if r.reason else ""
                self.log(f"{r.src.name} -> {r.dst}{flag}")

            if not dry_run_first:
                # If user unchecked dry-run, we still showed preview but go ahead
                pass

            # Ask via dialog (must call on main thread)
            proceed = self._ask_user_yes_no("Proceed with actual move?")
            if not proceed:
                self.log("Aborted after dry-run.")
                self._finish_worker()
                return

            if self.stop_requested:
                self.log("Stopped before real move.")
                self._finish_worker()
                return

            # REAL MOVE
            mover = SafeMover(dest_root, dry_run=False)
            results: List[MoveResult] = []
            for rec, folder in pairs:
                if self.stop_requested:
                    self.log("Stop detected; ending early.")
                    break
                res = mover.move_one(rec, folder)
                if res.performed:
                    self.log(f"MOVED: {res.src.name} -> {res.dst}")
                results.append(res)

            moved = sum(1 for r in results if r.performed)
            self.log(f"Moved {moved} files.")

            # LOGGING
            batch_id = datetime.now().strftime("%Y%m%d-%H%M%S")
            logger = MoveLogger(dest_root)
            entries = [
                MoveLogEntry(batch_id, r.src, r.dst, datetime.now())
                for r in results if r.performed
            ]
            logger.write_batch(entries)
            self.log(f"Batch logged as {batch_id}")

        except Exception as e:
            self.log(f"ERROR: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            self._finish_worker()

    def _finish_worker(self):
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")

    def _ask_user_yes_no(self, question: str) -> bool:
        # Run sync on main thread
        result_container = {}
        def ask():
            result_container["ans"] = messagebox.askyesno("Confirm", question)
        self.after(0, ask)
        # Wait until answer is populated
        while "ans" not in result_container:
            self.update()
        return bool(result_container["ans"])

    # ----- Undo tab handlers -----
    def on_list_batches(self):
        self.lst_batches.delete(0, "end")
        root_str = self.undo_root_var.get().strip() or "."
        try:
            dest_root = ensure_path(root_str)
        except Exception as e:
            messagebox.showerror("Error", f"Invalid root: {e}")
            return

        logger = MoveLogger(dest_root)
        batches = logger.list_batches()
        if not batches:
            messagebox.showinfo("Info", "No batches found.")
            return

        for b in batches:
            self.lst_batches.insert("end", b)
        self.log_undo(f"Loaded {len(batches)} batches.")
        self.btn_undo_run.config(state="disabled")

    def _get_selected_batch(self) -> Optional[str]:
        sel = self.lst_batches.curselection()
        if not sel:
            messagebox.showwarning("Select", "Select a batch first.")
            return None
        return self.lst_batches.get(sel[0])

    def on_undo_preview(self):
        batch = self._get_selected_batch()
        if not batch:
            return
        root_str = self.undo_root_var.get().strip() or "."
        try:
            dest_root = ensure_path(root_str)
        except Exception as e:
            messagebox.showerror("Error", f"Invalid root: {e}")
            return

        logger = MoveLogger(dest_root)
        undo_mgr = UndoManager(dest_root, logger, dry_run=True)
        previews = undo_mgr.undo_batch(batch)

        self.txt_undo_log.delete("1.0", "end")
        self.log_undo(f"--- Preview undo of {batch} ---")
        for r in previews[:100]:
            flag = f" ({r.reason})" if r.reason else ""
            self.log_undo(f"{r.src.name} -> {r.dst}{flag}")

        self.btn_undo_run.config(state="normal")

    def on_undo_run(self):
        batch = self._get_selected_batch()
        if not batch:
            return
        if not messagebox.askyesno("Confirm", f"Really undo batch {batch}?"):
            return

        root_str = self.undo_root_var.get().strip() or "."
        dest_root = ensure_path(root_str)
        logger = MoveLogger(dest_root)
        undo_mgr = UndoManager(dest_root, logger, dry_run=False)
        results = undo_mgr.undo_batch(batch)
        restored = sum(1 for r in results if r.performed)
        self.log_undo(f"Restored {restored} files from batch {batch}.")

# ---------- ENTRY POINT ----------
if __name__ == "__main__":
    app = AutoSorterGUI()
    app.mainloop()
