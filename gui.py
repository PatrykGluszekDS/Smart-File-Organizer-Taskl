# gui.py
import threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple
import json

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from autosorter.utils import ensure_path
from autosorter.scanner import FolderScanner
from autosorter.classifier import RuleSet, Classifier
from autosorter.mover import SafeMover
from autosorter.logger import MoveLogger
from autosorter.undo import UndoManager
from autosorter.models import MoveLogEntry, MoveResult

CONFIG_NAME = "gui_config.json"
MAX_LOG_LINES = 500  # keep widget light


class AutoSorterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AutoSorter")
        self.geometry("900x650")

        # Queues for thread-safe communication
        self.log_q: queue.Queue[str] = queue.Queue()
        self.undo_log_q: queue.Queue[str] = queue.Queue()
        self.progress_q: queue.Queue[Tuple[int, int]] = queue.Queue()  # (current, total)

        self.worker_thread: Optional[threading.Thread] = None
        self.stop_requested = False

        self._build_ui()
        self._load_config()
        self._poll_queues()

    # ---------------- UI ----------------
    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.tab_sort = ttk.Frame(notebook)
        self.tab_undo = ttk.Frame(notebook)
        notebook.add(self.tab_sort, text="Organize")
        notebook.add(self.tab_undo, text="Undo")

        # --- Organize tab ---
        frm = ttk.Frame(self.tab_sort, padding=10)
        frm.pack(fill="x")

        self.src_var = tk.StringVar()
        self.dst_var = tk.StringVar()
        self.rules_var = tk.StringVar()
        self.recursive_var = tk.BooleanVar(value=True)
        self.dry_run_var = tk.BooleanVar(value=True)

        self._file_picker(frm, "Source folder:", self.src_var, row=0, is_dir=True)
        self._file_picker(frm, "Destination root (blank = source):", self.dst_var, row=1, is_dir=True)
        self._file_picker(frm, "Rules JSON (optional):", self.rules_var, row=2, is_dir=False,
                          filetypes=[("JSON", "*.json")])

        ttk.Checkbutton(frm, text="Recursive", variable=self.recursive_var)\
            .grid(row=3, column=0, sticky="w", pady=2)
        ttk.Checkbutton(frm, text="Dry run first", variable=self.dry_run_var)\
            .grid(row=3, column=1, sticky="w", pady=2)

        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=3, sticky="w", pady=8)
        self.btn_start = ttk.Button(btns, text="Start", command=self.on_start)
        self.btn_start.pack(side="left")
        self.btn_stop = ttk.Button(btns, text="Stop", command=self.on_stop, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))
        self.btn_clear = ttk.Button(btns, text="Clear Log", command=lambda: self._clear_text(self.txt_log))
        self.btn_clear.pack(side="left", padx=(8, 0))

        # Progress bar
        prog_frame = ttk.Frame(self.tab_sort)
        prog_frame.pack(fill="x", padx=10)
        self.progress = ttk.Progressbar(prog_frame, mode="determinate")
        self.progress.pack(fill="x", expand=True, side="left")
        self.lbl_progress = ttk.Label(prog_frame, text="")
        self.lbl_progress.pack(side="left", padx=8)

        # Log box
        self.txt_log = tk.Text(self.tab_sort, height=20, wrap="none")
        self.txt_log.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        self._attach_scrollbars(self.txt_log)

        # --- Undo tab ---
        undo_frame = ttk.Frame(self.tab_undo, padding=10)
        undo_frame.pack(fill="x")

        self.undo_root_var = tk.StringVar()
        self._file_picker(undo_frame, "Destination root (.autosorter inside):",
                          self.undo_root_var, row=0, is_dir=True)

        ttk.Button(undo_frame, text="Load Batches", command=self.on_list_batches)\
            .grid(row=1, column=0, sticky="w", pady=5)
        ttk.Button(undo_frame, text="Clear Log", command=lambda: self._clear_text(self.txt_undo_log))\
            .grid(row=1, column=1, sticky="w", pady=5, padx=5)

        self.lst_batches = tk.Listbox(self.tab_undo, height=8)
        self.lst_batches.pack(fill="x", padx=10, pady=(0, 5))

        btn_undo = ttk.Frame(self.tab_undo)
        btn_undo.pack(fill="x", padx=10, pady=5)
        self.btn_undo_preview = ttk.Button(btn_undo, text="Undo (Preview)", command=self.on_undo_preview)
        self.btn_undo_preview.pack(side="left")
        self.btn_undo_run = ttk.Button(btn_undo, text="Perform Undo", command=self.on_undo_run, state="disabled")
        self.btn_undo_run.pack(side="left", padx=(8, 0))

        self.txt_undo_log = tk.Text(self.tab_undo, height=15, wrap="none")
        self.txt_undo_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._attach_scrollbars(self.txt_undo_log)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(self, textvariable=self.status_var, anchor="w", relief="sunken")
        status.pack(fill="x", side="bottom")

    def _file_picker(self, parent, label, var, row, is_dir=True, filetypes=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
        ent = ttk.Entry(parent, textvariable=var, width=70)
        ent.grid(row=row, column=1, sticky="we", padx=5)
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

    # ---------------- Helpers ----------------
    def _clear_text(self, widget: tk.Text):
        widget.delete("1.0", "end")

    def _trim_lines(self, widget: tk.Text, max_lines: int):
        lines = int(widget.index('end-1c').split('.')[0])
        if lines > max_lines:
            widget.delete("1.0", f"{lines - max_lines}.0")

    def log(self, msg: str):
        self.log_q.put(msg)

    def log_undo(self, msg: str):
        self.undo_log_q.put(msg)

    def set_status(self, msg: str):
        self.status_var.set(msg)

    def update_progress(self, current: int, total: int):
        self.progress_q.put((current, total))

    def _poll_queues(self):
        # Logs
        while not self.log_q.empty():
            line = self.log_q.get_nowait()
            self.txt_log.insert("end", line + "\n")
            self.txt_log.see("end")
            self._trim_lines(self.txt_log, MAX_LOG_LINES)

        while not self.undo_log_q.empty():
            line = self.undo_log_q.get_nowait()
            self.txt_undo_log.insert("end", line + "\n")
            self.txt_undo_log.see("end")
            self._trim_lines(self.txt_undo_log, MAX_LOG_LINES)

        # Progress
        while not self.progress_q.empty():
            cur, tot = self.progress_q.get_nowait()
            if tot > 0:
                self.progress.config(maximum=tot, value=cur)
                self.lbl_progress.config(text=f"{cur}/{tot}")
            else:
                self.progress.config(mode="indeterminate")
                self.progress.start(10)

        self.after(100, self._poll_queues)

    # ---------------- Actions ----------------
    def on_start(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return
        try:
            source = ensure_path(self.src_var.get())
        except Exception as e:
            messagebox.showerror("Error", f"Invalid source: {e}")
            return

        dest_input = self.dst_var.get().strip()
        try:
            dest_root = ensure_path(dest_input) if dest_input else source
        except Exception as e:
            messagebox.showerror("Error", f"Invalid destination: {e}")
            return

        rules_path = None
        if self.rules_var.get().strip():
            rules_path = Path(self.rules_var.get()).expanduser().resolve()

        recursive = self.recursive_var.get()
        dry_run = self.dry_run_var.get()

        # Save config
        self._save_config(source, dest_root, rules_path)

        # Reset UI
        self.stop_requested = False
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.progress.config(value=0)
        self.lbl_progress.config(text="")
        self._clear_text(self.txt_log)
        self.set_status("Running...")

        args = (source, dest_root, rules_path, recursive, dry_run)
        self.worker_thread = threading.Thread(target=self._organize_worker, args=args, daemon=True)
        self.worker_thread.start()

    def on_stop(self):
        self.stop_requested = True
        self.log("Stop requested. Finishing current file...")

    # ---------------- Worker ----------------
    def _organize_worker(self, source: Path, dest_root: Path, rules_path: Optional[Path],
                         recursive: bool, dry_run_first: bool):
        try:
            self.log("Scanning...")
            scanner = FolderScanner(source, recursive=recursive)
            files = scanner.scan()
            self.log(f"Found {len(files)} files.")

            rule_set = RuleSet(rules_path)
            classifier = Classifier(rule_set)
            pairs = classifier.assign(files)

            # Dry run
            mover = SafeMover(dest_root, dry_run=True)
            previews = mover.move_many(pairs)
            self.log("--- DRY RUN ---")
            for r in previews[:50]:
                flag = f" ({r.reason})" if r.reason else ""
                self.log(f"{r.src.name} -> {r.dst}{flag}")
            if len(previews) > 50:
                self.log(f"...and {len(previews)-50} more")

            if dry_run_first:
                proceed = self._ask_user_yes_no("Proceed with actual move?")
                if not proceed:
                    self.log("Aborted after dry-run.")
                    return
                if self.stop_requested:
                    self.log("Stopped before real move.")
                    return

            # Real move
            mover = SafeMover(dest_root, dry_run=False)
            total = len(pairs)
            moved_results: List[MoveResult] = []
            for idx, (rec, folder) in enumerate(pairs, 1):
                if self.stop_requested:
                    self.log("Stop detected; ending early.")
                    break
                res = mover.move_one(rec, folder)
                if res.performed:
                    self.log(f"MOVED: {res.src.name} -> {res.dst}")
                    moved_results.append(res)
                self.update_progress(idx, total)

            moved = len(moved_results)
            self.log(f"Moved {moved} files.")

            # Log batch
            if moved > 0:
                batch_id = datetime.now().strftime("%Y%m%d-%H%M%S")
                logger = MoveLogger(dest_root)
                entries = [
                    MoveLogEntry(batch_id, r.src, r.dst, datetime.now())
                    for r in moved_results
                ]
                logger.write_batch(entries)
                self.log(f"Batch logged as {batch_id}")
            else:
                self.log("Nothing to log.")

        except Exception as e:
            self.log(f"ERROR: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            self.after(0, self._finish_worker)

    def _finish_worker(self):
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.set_status("Ready")
        self.progress.stop()
        self.progress.config(value=0, mode="determinate")
        self.lbl_progress.config(text="")

    def _ask_user_yes_no(self, question: str) -> bool:
        # Must run on main thread
        ans_container = {}

        def ask():
            ans_container["ans"] = messagebox.askyesno("Confirm", question)

        self.after(0, ask)
        while "ans" not in ans_container:
            self.update()
        return bool(ans_container["ans"])

    # ---------------- Undo tab ----------------
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

        self._clear_text(self.txt_undo_log)
        self.log_undo(f"--- Preview undo of {batch} ---")
        for r in previews[:100]:
            flag = f" ({r.reason})" if r.reason else ""
            self.log_undo(f"{r.src.name} -> {r.dst}{flag}")
        if len(previews) > 100:
            self.log_undo(f"...and {len(previews)-100} more")

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

    # ---------------- Config ----------------
    def _config_path(self) -> Path:
        # Save alongside destination root if available, else home dir
        base = Path.home()
        return base / ".autosorter" / CONFIG_NAME

    def _load_config(self):
        path = self._config_path()
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                self.src_var.set(data.get("source", ""))
                self.dst_var.set(data.get("dest", ""))
                self.rules_var.set(data.get("rules", ""))
                self.undo_root_var.set(data.get("undo_root", ""))
        except Exception:
            pass  # ignore bad config

    def _save_config(self, source: Path, dest_root: Path, rules_path: Optional[Path]):
        cfg_dir = self._config_path().parent
        cfg_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "source": str(source),
            "dest": str(dest_root),
            "rules": str(rules_path) if rules_path else "",
            "undo_root": str(dest_root),
        }
        try:
            self._config_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass


if __name__ == "__main__":
    app = AutoSorterGUI()
    app.mainloop()
