from dataclasses import dataclass
import os
import re
import subprocess
import sys

import ollama


def venv_pip_path(venv_path: str) -> str:
    if sys.platform == "win32":
        return os.path.join(venv_path, "Scripts", "pip.exe")
    return os.path.join(venv_path, "bin", "pip")


def condense_pip_error(output: str) -> str:
    """Strip pip's version-ignore noise; keep actionable ERROR lines."""
    text = re.sub(
        r"ERROR: Ignored the following versions[^E]*(?=ERROR:|$)",
        "",
        output,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"ERROR: Ignored the following yanked versions[^E]*(?=ERROR:|$)",
        "",
        text,
        flags=re.DOTALL,
    )

    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("ERROR:") or stripped.startswith("WARNING:"):
            lines.append(stripped)

    if lines:
        return "\n".join(lines)

    trimmed = text.strip()
    return trimmed[:500] + ("..." if len(trimmed) > 500 else "")


def brief_error_summary(output: str) -> str:
    condensed = condense_pip_error(output)
    first_line = condensed.splitlines()[0] if condensed else "Installation failed."
    if first_line.startswith("ERROR:"):
        first_line = first_line.removeprefix("ERROR:").strip()
    if len(first_line) > 90:
        first_line = first_line[:87] + "..."
    return first_line


def summarize_pip_success(stdout: str) -> str:
    match = re.search(r"Successfully installed (.+)", stdout)
    if not match:
        return "All dependencies installed successfully."
    packages = match.group(1).strip().rstrip(".")
    count = len(re.findall(r"\S+-\S+", packages))
    if count:
        return f"Installed {count} package{'s' if count != 1 else ''} successfully."
    return "All dependencies installed successfully."


def extract_command(text: str) -> str:
    text = text.strip()
    fenced = re.search(r"```(?:\w+\n)?(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    return text.splitlines()[0].strip()


def normalize_fix_suggestion(raw: str) -> str | None:
    """Parse AI fix reply into a pip subcommand, or None if not fixable."""
    raw = raw.strip()
    if not raw or raw.upper() == "NONE":
        return None

    raw = extract_command(raw)
    raw = raw.strip("*\"'` ")

    match = re.search(
        r"\b((?:install|uninstall)\s+(?:--[\w-]+\s+)*[\w\[\].=<>!~,\s+-]+)",
        raw,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip().rstrip(".")

    if re.match(r"^(install|uninstall)\b", raw, re.IGNORECASE):
        return raw.rstrip(".")

    return None


def strip_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


def read_text_file(path: str, max_chars: int = 12000) -> str:
    with open(path, encoding="utf-8", errors="replace") as handle:
        content = handle.read(max_chars + 1)
    if len(content) > max_chars:
        content = content[:max_chars] + "\n...(truncated)"
    return content


def pick_text_file(parent=None, title: str = "Select a text file") -> str | None:
    from tkinter import filedialog

    file_path = filedialog.askopenfilename(
        parent=parent,
        title=title,
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
    )
    return file_path or None


def parse_requirements(path: str) -> RequirementsPreview:
    packages: list[str] = []
    issues: list[str] = []
    try:
        content = read_text_file(path, max_chars=50000)
    except OSError as exc:
        return RequirementsPreview(path, 0, [], [f"Could not read file: {exc}"])

    for line_no, raw in enumerate(content.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        if line.startswith(("-r", "--requirement", "-c", "--constraint", "-f", "--find-links")):
            issues.append(f"Line {line_no}: includes nested/constraints ({line.split()[0]}) — not validated here.")
            continue
        name = re.split(r"[=<>!\[]", line, maxsplit=1)[0].strip()
        if name:
            packages.append(name)

    return RequirementsPreview(path, len(packages), packages, issues)


def check_environment(model: str = "llama3") -> EnvironmentStatus:
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    try:
        ollama.list()
        message = "Ollama is reachable."
        ok = True
    except Exception as exc:
        message = f"Ollama unavailable: {exc}"
        ok = False
    return EnvironmentStatus(
        python_version=py_version,
        python_executable=sys.executable,
        ollama_ok=ok,
        ollama_model=model,
        ollama_message=message,
    )


def format_environment_status(status: EnvironmentStatus) -> str:
    ollama_line = "OK" if status.ollama_ok else status.ollama_message
    return (
        f"Python {status.python_version}\n"
        f"Executable: {status.python_executable}\n"
        f"Ollama: {ollama_line}\n"
        f"AI model: {status.ollama_model}"
    )


def format_requirements_preview(preview: RequirementsPreview) -> str:
    lines = [
        f"File: {preview.path}",
        f"Packages found: {preview.package_count}",
    ]
    if preview.packages:
        shown = preview.packages[:20]
        lines.append("Packages: " + ", ".join(shown))
        if len(preview.packages) > 20:
            lines.append(f"... and {len(preview.packages) - 20} more")
    if preview.issues:
        lines.append("")
        lines.append("Notes:")
        lines.extend(preview.issues)
    return "\n".join(lines)


def dry_run_requirements(requirements_file: str) -> tuple[bool, str]:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            requirements_file,
            "--dry-run",
        ],
        capture_output=True,
        text=True,
    )
    output = (result.stdout or result.stderr or "").strip()
    condensed = condense_pip_error(output) if result.returncode != 0 else output
    if result.returncode == 0:
        return True, "Dry-run passed — pip can resolve these requirements for your Python version."
    return False, condensed or "Dry-run failed."


def parse_pip_argv(command: str, venv_pip: str) -> list[str] | None:
    """Turn an AI-suggested pip command into a safe argv list using the venv pip."""
    command = extract_command(command)
    command = re.sub(r"^(python\s+-m\s+)?pip3?\s+", "", command, flags=re.IGNORECASE)
    if not command:
        return None

    parts = command.split()
    if parts[0].lower() not in ("install", "uninstall"):
        return None

    return [venv_pip, *parts]


@dataclass
class FixResult:
    attempted: bool
    success: bool
    message: str
    command: str | None = None


@dataclass
class EnvironmentStatus:
    python_version: str
    python_executable: str
    ollama_ok: bool
    ollama_model: str
    ollama_message: str


@dataclass
class RequirementsPreview:
    path: str
    package_count: int
    packages: list[str]
    issues: list[str]


class PythonInstallerLogic:
    def __init__(self, assistant, venv_path="venv"):
        self.venv_path = venv_path
        self.assistant = assistant
        self.on_phase = None
        self.on_success = None
        self.on_error = None
        self.last_fix: FixResult | None = None

    def _phase(self, message: str) -> None:
        if self.on_phase:
            self.on_phase(message)

    def get_requirements_file(self, parent=None) -> str | None:
        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            parent=parent,
            title="Select requirements.txt file",
            filetypes=[("Requirements files", "*.txt"), ("All files", "*.*")],
        )
        return file_path or None

    def _pip_install(self, requirements_file: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [venv_pip_path(self.venv_path), "install", "-r", requirements_file],
            capture_output=True,
            text=True,
        )

    def install_dependencies(
        self,
        requirements_file=None,
        parent=None,
        auto_fix: bool = True,
    ) -> bool:
        if requirements_file is None:
            requirements_file = self.get_requirements_file(parent=parent)
        if not requirements_file:
            return False

        self.last_fix = None
        self._phase("Creating virtual environment...")
        result_venv = subprocess.run(
            [sys.executable, "-m", "venv", self.venv_path],
            capture_output=True,
            text=True,
        )
        if result_venv.returncode != 0:
            self._handle_error(result_venv.stderr or result_venv.stdout)
            return False

        self._phase("Installing dependencies...")
        result_install = self._pip_install(requirements_file)
        if result_install.returncode != 0:
            error_output = (result_install.stderr or result_install.stdout).strip()

            if auto_fix:
                fix = self.assistant.try_fix(
                    error_output,
                    requirements_file=requirements_file,
                    venv_pip=venv_pip_path(self.venv_path),
                )
                self.last_fix = fix
                if fix.attempted:
                    self._phase(f"Trying fix: {fix.command}")
                    if fix.success:
                        self._phase("Retrying installation...")
                        result_install = self._pip_install(requirements_file)
                        if result_install.returncode == 0:
                            summary = summarize_pip_success(result_install.stdout)
                            if self.on_success:
                                self.on_success(summary)
                            return True

            self._handle_error(error_output, fix=self.last_fix)
            return False

        summary = summarize_pip_success(result_install.stdout)
        if self.on_success:
            self.on_success(summary)
        return True

    def _handle_error(self, output: str, fix: FixResult | None = None) -> None:
        if self.on_error:
            self.on_error(output.strip(), fix)


class Assistant:
    def __init__(self, model="llama3"):
        self.model = model

    def run(self, terminal_output: str) -> str:
        condensed = condense_pip_error(terminal_output)
        prompt = (
            "You are a helpful assistant for diagnosing Python dependency installation problems.\n"
            "The user attempted to install Python packages with pip and it failed.\n"
            "Analyze the error and explain it in plain language.\n\n"
            "Rules:\n"
            "- Keep the response under 120 words.\n"
            "- Use two short sections: Problem and How to fix (plain text, no markdown).\n"
            "- Give actionable steps (e.g. change Python version, pick another package, edit requirements.txt).\n"
            "- Do NOT paste or repeat the raw pip log.\n"
            "- Do NOT use asterisks, backticks, or bullet symbols.\n\n"
            f"Error output:\n{condensed}"
        )

        response = ollama.chat(
            model=self.model, messages=[{"role": "user", "content": prompt}]
        )
        return strip_markdown(response["message"]["content"])

    def suggest_fix_command(
        self,
        error_output: str,
        *,
        requirements_file: str,
        venv_pip: str,
    ) -> str | None:
        condensed = condense_pip_error(error_output)
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        prompt = (
            "A pip install from a requirements file failed.\n"
            f"Python version: {py_version}\n"
            f"Requirements file: {requirements_file}\n"
            f"Venv pip path: {venv_pip}\n\n"
            f"Error:\n{condensed}\n\n"
            "Suggest ONE pip subcommand that might fix this (install or uninstall only).\n"
            "Examples:\n"
            "  install open3d==0.18.0\n"
            "  install --upgrade pip setuptools wheel\n"
            "  uninstall conflicting-package\n\n"
            "If no pip command can fix it (e.g. wrong Python version), reply exactly: NONE\n"
            "Otherwise reply with the subcommand only — no 'pip' prefix, no markdown, no explanation."
        )

        response = ollama.chat(
            model=self.model, messages=[{"role": "user", "content": prompt}]
        )
        return normalize_fix_suggestion(response["message"]["content"])

    def try_fix(
        self,
        error_output: str,
        *,
        requirements_file: str,
        venv_pip: str,
    ) -> FixResult:
        try:
            suggestion = self.suggest_fix_command(
                error_output,
                requirements_file=requirements_file,
                venv_pip=venv_pip,
            )
        except Exception as exc:
            return FixResult(False, False, f"Could not get fix suggestion: {exc}")

        if not suggestion:
            return FixResult(False, False, "No automatic pip fix available for this error.")

        argv = parse_pip_argv(suggestion, venv_pip)
        if not argv:
            return FixResult(
                False,
                False,
                f"Suggested fix is not a safe pip command: {suggestion}",
            )

        command_display = " ".join(argv)
        result = subprocess.run(argv, capture_output=True, text=True)
        if result.returncode != 0:
            detail = condense_pip_error(result.stderr or result.stdout)
            return FixResult(
                attempted=True,
                success=False,
                message=detail or "Fix command failed.",
                command=command_display,
            )

        return FixResult(
            attempted=True,
            success=True,
            message="Fix command completed.",
            command=command_display,
        )

    def fix_error(self, error_summary: str, *, venv_pip: str) -> str:
        """Legacy wrapper — prefer try_fix() for structured results."""
        fix = self.try_fix(
            error_summary,
            requirements_file="requirements.txt",
            venv_pip=venv_pip,
        )
        if not fix.attempted:
            return fix.message
        if fix.success:
            return "Error fixed successfully."
        return self.run(fix.message)

    def summarize_text(self, content: str, *, filename: str = "file.txt") -> str:
        prompt = (
            "Summarize the following text file for a non-technical user.\n\n"
            "Rules:\n"
            "- Keep the response under 150 words.\n"
            "- Use plain text only (no markdown, bullets, or asterisks).\n"
            "- Say what the file is about and the most important details.\n"
            "- If it looks like requirements.txt, list the main packages and purpose.\n"
            "- If it is logs or errors, state the main issue briefly.\n\n"
            f"Filename: {filename}\n\n"
            f"Content:\n{content}"
        )

        response = ollama.chat(
            model=self.model, messages=[{"role": "user", "content": prompt}]
        )
        return strip_markdown(response["message"]["content"])

    def summarize_file(self, file_path: str) -> str:
        filename = os.path.basename(file_path)
        content = read_text_file(file_path)
        if not content.strip():
            return "The file is empty."
        return self.summarize_text(content, filename=filename)

    def suggest_requirements_edit(
        self,
        error_output: str,
        requirements_content: str,
        *,
        filename: str,
    ) -> str:
        condensed = condense_pip_error(error_output)
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        prompt = (
            "A pip install failed when using this requirements file.\n"
            f"Python version: {py_version}\n"
            f"Filename: {filename}\n\n"
            f"Error:\n{condensed}\n\n"
            f"Current requirements file:\n{requirements_content}\n\n"
            "Suggest an edited requirements file that might install on this Python version.\n"
            "Rules:\n"
            "- Return ONLY the new file contents (plain text lines).\n"
            "- Change the minimum needed (pin versions, remove unsupported packages, or add comments).\n"
            "- If nothing can fix it without changing Python version, return a one-line comment starting with # explaining that.\n"
            "- No markdown fences or explanations outside the file."
        )
        response = ollama.chat(
            model=self.model, messages=[{"role": "user", "content": prompt}]
        )
        return strip_markdown(response["message"]["content"]).strip()
