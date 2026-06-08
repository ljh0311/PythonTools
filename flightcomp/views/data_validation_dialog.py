"""
Data Validation Dialog
Run structural and optional AI validation on airports, scenarios, checklists, training records.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, Callable, List
import threading

from utils.data_validator import (
    run_validation,
    ValidationResult,
    Severity,
)


class DataValidationDialog:
    """Dialog to run and view data validation results."""

    def __init__(self, parent, config: Dict[str, Any]):
        self.parent = parent
        self.config = config
        self.results: List[ValidationResult] = []
        self._running = False

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Data Validation")
        self.dialog.geometry("700x550")
        self.dialog.transient(parent)
        self.dialog.minsize(500, 400)

        self.dialog.update_idletasks()
        x = parent.winfo_x() + max(0, (parent.winfo_width() - 700) // 2)
        y = parent.winfo_y() + max(0, (parent.winfo_height() - 550) // 2)
        self.dialog.geometry(f"+{x}+{y}")

        self.setup_ui()

    def setup_ui(self):
        main = ttk.Frame(self.dialog, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Scope
        scope_frame = ttk.LabelFrame(main, text="Scope", padding=8)
        scope_frame.pack(fill=tk.X, pady=(0, 8))

        self.scope_airports = tk.BooleanVar(value=True)
        self.scope_scenarios = tk.BooleanVar(value=True)
        self.scope_checklists = tk.BooleanVar(value=True)
        self.scope_records = tk.BooleanVar(value=True)

        ttk.Checkbutton(scope_frame, text="Airports", variable=self.scope_airports).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Checkbutton(scope_frame, text="Scenarios", variable=self.scope_scenarios).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Checkbutton(scope_frame, text="Checklists", variable=self.scope_checklists).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Checkbutton(scope_frame, text="Training records", variable=self.scope_records).pack(side=tk.LEFT, padx=(0, 15))

        # Mode
        mode_frame = ttk.LabelFrame(main, text="Validation type", padding=8)
        mode_frame.pack(fill=tk.X, pady=(0, 8))

        self.structural_only = tk.BooleanVar(value=True)
        ttk.Radiobutton(
            mode_frame,
            text="Structural only (fast)",
            variable=self.structural_only,
            value=True,
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            mode_frame,
            text="Structural + AI (slower, requires Ollama)",
            variable=self.structural_only,
            value=False,
        ).pack(anchor=tk.W)

        # Run + progress
        run_frame = ttk.Frame(main)
        run_frame.pack(fill=tk.X, pady=(0, 8))

        self.run_btn = ttk.Button(run_frame, text="Run validation", command=self._on_run)
        self.run_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.progress_var = tk.StringVar(value="")
        self.progress_label = ttk.Label(run_frame, textvariable=self.progress_var, foreground="gray")
        self.progress_label.pack(side=tk.LEFT)

        # Summary
        self.summary_var = tk.StringVar(value="No results yet.")
        ttk.Label(main, textvariable=self.summary_var, font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(0, 4))

        # Results tree
        tree_frame = ttk.Frame(main)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        columns = ("severity", "entity_id", "category", "message")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12, selectmode="extended")
        self.tree.heading("severity", text="Severity")
        self.tree.heading("entity_id", text="Entity")
        self.tree.heading("category", text="Category")
        self.tree.heading("message", text="Message")
        self.tree.column("severity", width=70)
        self.tree.column("entity_id", width=120)
        self.tree.column("category", width=100)
        self.tree.column("message", width=280)
        scroll = ttk.Scrollbar(tree_frame)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=scroll.set)
        scroll.config(command=self.tree.yview)

        self.tree.tag_configure("pass", foreground="green")
        self.tree.tag_configure("warning", foreground="orange")
        self.tree.tag_configure("error", foreground="red")

        # Detail (on selection)
        detail_frame = ttk.LabelFrame(main, text="Detail", padding=4)
        detail_frame.pack(fill=tk.X, pady=(0, 8))
        self.detail_var = tk.StringVar(value="")
        self.detail_label = ttk.Label(detail_frame, textvariable=self.detail_var, wraplength=650)
        self.detail_label.pack(anchor=tk.W)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Copy results", command=self._copy_results).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="Save report...", command=self._save_report).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="Close", command=self.dialog.destroy).pack(side=tk.RIGHT)

    def _scope(self) -> Dict[str, bool]:
        return {
            "airports": self.scope_airports.get(),
            "scenarios": self.scope_scenarios.get(),
            "checklists": self.scope_checklists.get(),
            "training_records": self.scope_records.get(),
        }

    def _on_run(self):
        if self._running:
            return
        self._running = True
        self.run_btn.config(state=tk.DISABLED)
        self.progress_var.set("Running...")
        self.results = []
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.summary_var.set("Running validation...")
        self.detail_var.set("")

        def run():
            try:
                def progress(msg: str):
                    self.dialog.after(0, lambda: self.progress_var.set(msg))

                scope = self._scope()
                structural_only = self.structural_only.get()
                config = {
                    "ollama_url": self.config.get("ollama_url", "http://localhost:11434"),
                    "ai_model": self.config.get("ai_model", "llama2"),
                }
                results = run_validation(scope, structural_only, config, progress_callback=progress)
                self.dialog.after(0, lambda: self._show_results(results))
            except Exception as e:
                self.dialog.after(0, lambda: self._show_error(str(e)))
            finally:
                self.dialog.after(0, self._run_done)

        threading.Thread(target=run, daemon=True).start()

    def _show_results(self, results: List[ValidationResult]):
        self.results = results
        passed = sum(1 for r in results if r.severity == Severity.PASS)
        warnings = sum(1 for r in results if r.severity == Severity.WARNING)
        errors = sum(1 for r in results if r.severity == Severity.ERROR)
        self.summary_var.set(f"Passed: {passed}  |  Warnings: {warnings}  |  Errors: {errors}")

        for r in results:
            tag = r.severity.value
            self.tree.insert("", tk.END, values=(r.severity.value, r.entity_id, r.category, r.message[:80] + ("..." if len(r.message) > 80 else "")), tags=(tag,))

    def _show_error(self, msg: str):
        messagebox.showerror("Validation error", msg)
        self.summary_var.set("Validation failed.")

    def _run_done(self):
        self._running = False
        self.run_btn.config(state=tk.NORMAL)
        self.progress_var.set("Done.")

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            self.detail_var.set("")
            return
        item = self.tree.item(sel[0])
        vals = item["values"]
        if len(vals) < 4:
            return
        entity_id, category = vals[1], vals[2]
        for r in self.results:
            if r.entity_id == entity_id and r.category == category:
                detail = r.message
                if r.detail:
                    detail += "\n" + r.detail
                self.detail_var.set(detail)
                return
        self.detail_var.set("")

    def _copy_results(self):
        lines = [f"{r.severity.value}\t{r.entity_id}\t{r.category}\t{r.message}" + (f"\t{r.detail}" if r.detail else "") for r in self.results]
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append("\n".join(lines))
        self.dialog.update()
        self.progress_var.set("Results copied to clipboard.")

    def _save_report(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("JSON", "*.json"), ("All", "*.*")],
        )
        if not path:
            return
        try:
            if path.lower().endswith(".json"):
                import json
                data = [r.to_dict() for r in self.results]
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("# Data validation report\n\n")
                    f.write(f"{self.summary_var.get()}\n\n")
                    f.write("| Severity | Entity | Category | Message |\n")
                    f.write("|----------|--------|----------|--------|\n")
                    for r in self.results:
                        msg = (r.message + " " + (r.detail or "")).replace("|", " ").replace("\n", " ")
                        f.write(f"| {r.severity.value} | {r.entity_id} | {r.category} | {msg} |\n")
            self.progress_var.set("Report saved.")
        except Exception as e:
            messagebox.showerror("Save error", str(e))
