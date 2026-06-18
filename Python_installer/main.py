import threading
import tkinter as tk
from tkinter import ttk

from inst import (
    Assistant,
    FixResult,
    PythonInstallerLogic,
    brief_error_summary,
    check_environment,
    condense_pip_error,
    dry_run_requirements,
    format_environment_status,
    format_requirements_preview,
    parse_requirements,
    pick_text_file,
    read_text_file,
    strip_markdown,
)


class PythonInstallerGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Python Dependency Installer")
        self.root.geometry("520x380")
        self.root.minsize(480, 340)
        self._installing = False
        self._summarizing = False
        self._busy_other = False
        self._last_requirements_file: str | None = None
        self._last_error_output: str | None = None
        self._details_text_value = ""

        self.assistant = Assistant()
        self.logic = PythonInstallerLogic(self.assistant)
        self.logic.on_phase = self._thread_safe(self.set_phase)
        self.logic.on_success = self._thread_safe(self.show_success)
        self.logic.on_error = self._thread_safe(self.show_error)

        self._build_gui()
        self._run_startup_check()

    def _thread_safe(self, callback):
        def wrapper(*args, **kwargs):
            self.root.after(0, lambda: callback(*args, **kwargs))

        return wrapper

    def _build_gui(self):
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Python Dependency Installer",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            frame,
            text="Install, validate, summarize, and fix Python dependencies with AI.",
            foreground="#666666",
        ).pack(anchor="w", pady=(4, 12))

        self.phase_label = ttk.Label(
            frame,
            text="Ready. Choose a tool below.",
        )
        self.phase_label.pack(anchor="w")

        self.progress = ttk.Progressbar(frame, mode="indeterminate", length=360)
        self.progress.pack(fill="x", pady=(8, 0))
        self.progress.pack_forget()

        self.result_label = ttk.Label(frame, text="", wraplength=420)
        self.result_label.pack(anchor="w", pady=(8, 0))

        self.details_frame = ttk.LabelFrame(frame, text="Details", padding=8)
        self.details_text = tk.Text(
            self.details_frame,
            height=6,
            width=52,
            wrap="word",
            state="disabled",
            relief="flat",
            font=("Segoe UI", 9),
        )
        self.details_text.pack(fill="both", expand=True)

        primary = ttk.Frame(frame)
        primary.pack(fill="x", pady=(14, 6))

        self.install_btn = ttk.Button(
            primary, text="Install", command=self.start_install
        )
        self.install_btn.pack(side="left")

        self.validate_btn = ttk.Button(
            primary, text="Validate file", command=self.start_validate
        )
        self.validate_btn.pack(side="left", padx=(8, 0))

        self.summarize_btn = ttk.Button(
            primary, text="Summarize", command=self.start_summarize
        )
        self.summarize_btn.pack(side="left", padx=(8, 0))

        ttk.Button(primary, text="Quit", command=self.root.quit).pack(side="right")

        secondary = ttk.Frame(frame)
        secondary.pack(fill="x")

        self.check_btn = ttk.Button(
            secondary, text="Check setup", command=self.start_check_setup
        )
        self.check_btn.pack(side="left")

        self.retry_btn = ttk.Button(
            secondary, text="Retry install", command=self.start_retry, state="disabled"
        )
        self.retry_btn.pack(side="left", padx=(8, 0))

        self.fix_req_btn = ttk.Button(
            secondary,
            text="Suggest requirements fix",
            command=self.start_suggest_fix,
            state="disabled",
        )
        self.fix_req_btn.pack(side="left", padx=(8, 0))

        self.copy_btn = ttk.Button(
            secondary, text="Copy details", command=self.copy_details, state="disabled"
        )
        self.copy_btn.pack(side="left", padx=(8, 0))

        self.env_label = ttk.Label(frame, text="", foreground="#666666", font=("Segoe UI", 8))
        self.env_label.pack(anchor="w", pady=(10, 0))

    def _run_startup_check(self) -> None:
        def worker():
            status = check_environment(self.assistant.model)
            text = f"Python {status.python_version} | Ollama: {'OK' if status.ollama_ok else 'offline'}"
            self.root.after(0, lambda: self.env_label.config(text=text))

        threading.Thread(target=worker, daemon=True).start()

    def set_phase(self, message: str) -> None:
        self.result_label.config(text="", foreground="")
        self.phase_label.config(text=message)
        if not self.progress.winfo_ismapped():
            self.progress.pack(fill="x", pady=(8, 0), after=self.phase_label)
        self.progress.start(12)

    def show_success(self, summary: str) -> None:
        self._finish_busy()
        self.phase_label.config(text="Done")
        self.result_label.config(text=f"✓ {summary}", foreground="#1a7f37")
        self.retry_btn.config(state="disabled")

    def show_error(self, terminal_output: str, fix: FixResult | None = None) -> None:
        self._finish_busy()
        self._last_error_output = terminal_output
        self.phase_label.config(text="Installation failed")
        summary = brief_error_summary(terminal_output)
        self.result_label.config(
            text=f"✗ {summary}",
            foreground="#c0392b",
        )
        self.retry_btn.config(state="normal" if self._last_requirements_file else "disabled")
        self.fix_req_btn.config(state="normal" if self._last_requirements_file else "disabled")
        self._set_details("Analyzing error...", title="What to do")
        self._run_ai_analysis(terminal_output, fix)

    def _format_fix_note(self, fix: FixResult | None) -> str | None:
        if fix is None:
            return None
        if not fix.attempted:
            return f"Auto-fix skipped: {fix.message}"
        if fix.success:
            return f"Auto-fix ran ({fix.command}) but install still failed."
        return f"Auto-fix tried ({fix.command}) but failed:\n{fix.message}"

    def _run_ai_analysis(self, terminal_output: str, fix: FixResult | None = None) -> None:
        def worker():
            try:
                explanation = strip_markdown(self.assistant.run(terminal_output))
            except Exception as exc:
                explanation = (
                    "Could not reach the AI assistant.\n\n"
                    f"{condense_pip_error(terminal_output)}\n\n"
                    f"(AI unavailable: {exc})"
                )
            fix_note = self._format_fix_note(fix)
            if fix_note:
                explanation = f"{fix_note}\n\n{explanation}"
            self.root.after(0, lambda: self._set_details(explanation, title="What to do"))

        threading.Thread(target=worker, daemon=True).start()

    def _set_details(self, text: str, title: str = "Details") -> None:
        self._details_text_value = text
        self.details_frame.config(text=title)
        self.details_frame.pack(fill="both", expand=True, pady=(12, 0))
        self.details_text.config(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.insert("1.0", text)
        self.details_text.config(state="disabled")
        self.copy_btn.config(state="normal" if text.strip() else "disabled")

    def _hide_details(self) -> None:
        self.details_frame.pack_forget()
        self.details_text.config(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.config(state="disabled")
        self._details_text_value = ""
        self.copy_btn.config(state="disabled")

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for btn in (
            self.install_btn,
            self.validate_btn,
            self.summarize_btn,
            self.check_btn,
        ):
            btn.config(state=state)
        if busy:
            self.retry_btn.config(state="disabled")
            self.fix_req_btn.config(state="disabled")
            self.copy_btn.config(state="disabled")

    def _finish_busy(self) -> None:
        self.progress.stop()
        self.progress.pack_forget()
        self._installing = False
        self._summarizing = False
        self._busy_other = False
        self._set_busy(False)
        if self._last_requirements_file and self._last_error_output:
            self.retry_btn.config(state="normal")
            self.fix_req_btn.config(state="normal")

    def copy_details(self) -> None:
        if not self._details_text_value.strip():
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self._details_text_value)
        self.result_label.config(text="✓ Copied to clipboard", foreground="#1a7f37")

    def _run_background(self, phase: str, worker_fn, on_done) -> None:
        if self._installing or self._summarizing or self._busy_other:
            return
        self._busy_other = True
        self._set_busy(True)
        self._hide_details()
        self.result_label.config(text="", foreground="")
        self.set_phase(phase)

        def thread_main():
            try:
                result = worker_fn()
            except Exception as exc:
                result = exc

            def finish():
                self._busy_other = False
                self._finish_busy()
                on_done(result)

            self.root.after(0, finish)

        threading.Thread(target=thread_main, daemon=True).start()

    def start_check_setup(self) -> None:
        def worker():
            return check_environment(self.assistant.model)

        def done(status):
            self.phase_label.config(text="Setup check complete")
            self.result_label.config(
                text="✓ Environment checked" if status.ollama_ok else "⚠ Ollama offline",
                foreground="#1a7f37" if status.ollama_ok else "#c0392b",
            )
            self._set_details(format_environment_status(status), title="Environment")

        self._run_background("Checking Python and Ollama...", worker, done)

    def start_validate(self) -> None:
        file_path = pick_text_file(
            parent=self.root, title="Select requirements file to validate"
        )
        if not file_path:
            return

        filename = file_path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]

        def worker():
            preview = parse_requirements(file_path)
            ok, dry_msg = dry_run_requirements(file_path)
            return preview, ok, dry_msg

        def done(result):
            preview, ok, dry_msg = result
            self.phase_label.config(text="Validation complete")
            self.result_label.config(
                text=f"{'✓' if ok else '✗'} {filename}",
                foreground="#1a7f37" if ok else "#c0392b",
            )
            body = format_requirements_preview(preview)
            body += f"\n\nDry-run: {dry_msg}"
            self._set_details(body, title="Validation")

        self._run_background(f"Validating {filename}...", worker, done)

    def start_summarize(self) -> None:
        file_path = pick_text_file(
            parent=self.root, title="Select a text file to summarize"
        )
        if not file_path:
            return

        filename = file_path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]

        def worker():
            return self.assistant.summarize_file(file_path)

        def done(summary):
            if isinstance(summary, Exception):
                summary = f"Summary failed: {summary}"
            self.phase_label.config(text="Summary ready")
            self.result_label.config(text=f"✓ {filename}", foreground="#1a7f37")
            self._set_details(summary, title="Summary")

        self._run_background(f"Summarizing {filename}...", worker, done)

    def start_suggest_fix(self) -> None:
        if not self._last_requirements_file or not self._last_error_output:
            return

        path = self._last_requirements_file
        filename = path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]

        def worker():
            content = read_text_file(path, max_chars=8000)
            return self.assistant.suggest_requirements_edit(
                self._last_error_output,
                content,
                filename=filename,
            )

        def done(suggestion):
            if isinstance(suggestion, Exception):
                suggestion = f"Suggestion failed: {suggestion}"
            self.phase_label.config(text="Suggested edit ready")
            self.result_label.config(text=f"✓ {filename}", foreground="#1a7f37")
            self._set_details(suggestion, title="Suggested requirements.txt")

        self._run_background("Suggesting requirements fix...", worker, done)

    def _begin_install(self, requirements_file: str) -> None:
        self._last_requirements_file = requirements_file
        self._last_error_output = None
        self.retry_btn.config(state="disabled")
        self.fix_req_btn.config(state="disabled")

        filename = requirements_file.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
        self.set_phase(f"Installing from {filename}...")

        def worker():
            self.logic.install_dependencies(requirements_file=requirements_file)

        threading.Thread(target=worker, daemon=True).start()

    def start_install(self) -> None:
        if self._installing or self._summarizing or self._busy_other:
            return

        self._installing = True
        self._set_busy(True)
        self._hide_details()
        self.result_label.config(text="", foreground="")
        self.phase_label.config(text="Choose a requirements file...")

        requirements_file = self.logic.get_requirements_file(parent=self.root)
        if not requirements_file:
            self._finish_busy()
            self.phase_label.config(text="Ready. Choose a tool below.")
            return

        self._begin_install(requirements_file)

    def start_retry(self) -> None:
        if not self._last_requirements_file or self._installing:
            return

        self._installing = True
        self._set_busy(True)
        self._hide_details()
        self.result_label.config(text="", foreground="")
        self._begin_install(self._last_requirements_file)


if __name__ == "__main__":
    root = tk.Tk()
    PythonInstallerGUI(root)
    root.mainloop()
