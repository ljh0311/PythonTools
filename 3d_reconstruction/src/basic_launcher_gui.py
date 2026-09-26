#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D Reconstruction Suite — launcher UI.
Clear modes, status feedback, and Gaussian preflight checks.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from photo_upload_processor import PhotoUploadProcessor

# Visual tokens (warm charcoal + amber accent — not purple/cream AI defaults)
COLORS = {
    "bg": "#1c1b1a",
    "panel": "#2a2826",
    "panel_hi": "#343230",
    "text": "#f2eee8",
    "muted": "#a39e96",
    "accent": "#d97706",
    "accent_dim": "#b45309",
    "ok": "#4ade80",
    "warn": "#fbbf24",
    "err": "#f87171",
    "border": "#3f3c39",
}


class ModeCard(ttk.Frame):
    """One clickable mode with title + short tip."""

    def __init__(self, master, title: str, tip: str, command, style_name: str = "Card.TFrame"):
        super().__init__(master, style=style_name, padding=(14, 12))
        self._command = command
        title_lbl = ttk.Label(self, text=title, style="CardTitle.TLabel")
        tip_lbl = ttk.Label(self, text=tip, style="CardTip.TLabel", wraplength=420, justify=tk.LEFT)
        title_lbl.pack(anchor=tk.W)
        tip_lbl.pack(anchor=tk.W, pady=(4, 8))
        btn = ttk.Button(self, text="Open", command=command, style="Accent.TButton")
        btn.pack(anchor=tk.E)
        for widget in (self, title_lbl, tip_lbl):
            widget.bind("<Button-1>", lambda _e: command())


class BasicLauncherGUI:
    """Launcher for live, panorama, and Gaussian workflows."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("3D Reconstruction Suite")
        self.root.geometry("560x720")
        self.root.minsize(520, 640)
        self.root.configure(bg=COLORS["bg"])
        self._configure_styles()
        self.center_window()
        self.setup_ui()

    def _configure_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Root.TFrame", background=COLORS["bg"])
        style.configure("Panel.TFrame", background=COLORS["panel"])
        style.configure("Card.TFrame", background=COLORS["panel_hi"], relief="flat")
        style.configure(
            "Title.TLabel",
            background=COLORS["bg"],
            foreground=COLORS["text"],
            font=("Segoe UI Semibold", 20),
        )
        style.configure(
            "Subtitle.TLabel",
            background=COLORS["bg"],
            foreground=COLORS["muted"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background=COLORS["panel_hi"],
            foreground=COLORS["text"],
            font=("Segoe UI Semibold", 12),
        )
        style.configure(
            "CardTip.TLabel",
            background=COLORS["panel_hi"],
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "Status.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["text"],
            font=("Segoe UI", 9),
            wraplength=480,
        )
        style.configure(
            "Section.TLabelframe",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
        )
        style.configure(
            "Section.TLabelframe.Label",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
        )
        style.configure(
            "Accent.TButton",
            font=("Segoe UI Semibold", 10),
            padding=(12, 6),
        )
        style.map(
            "Accent.TButton",
            background=[("!disabled", COLORS["accent"]), ("disabled", COLORS["border"])],
            foreground=[("!disabled", "#1c1b1a")],
        )
        style.configure("Ghost.TButton", font=("Segoe UI", 9), padding=(10, 4))
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=COLORS["border"],
            background=COLORS["accent"],
            thickness=8,
        )

    def center_window(self) -> None:
        self.root.update_idletasks()
        w, h = 560, 720
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def setup_ui(self) -> None:
        outer = ttk.Frame(self.root, style="Root.TFrame", padding=20)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="3D Reconstruction", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            outer,
            text="Pick a mode. Tips under each card say how to shoot.",
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(4, 16))

        cards = ttk.Frame(outer, style="Root.TFrame")
        cards.pack(fill=tk.BOTH, expand=True)

        self.live_card = ModeCard(
            cards,
            "Live camera",
            "Space = keyframe (need 5+). R = rebuild. S = save PLY. Move around the subject.",
            self.launch_live_reconstruction,
        )
        self.live_card.pack(fill=tk.X, pady=6)

        self.pano_card = ModeCard(
            cards,
            "360 panorama",
            "Rotate in place. Overlap shots. Output is a wide PNG, not a 3D model.",
            self.launch_photo_reconstruction,
        )
        self.pano_card.pack(fill=tk.X, pady=6)

        self.view_card = ModeCard(
            cards,
            "View panorama",
            "Open a saved PNG from the output folder.",
            self.view_panorama,
        )
        self.view_card.pack(fill=tk.X, pady=6)

        self.gaussian_card = ModeCard(
            cards,
            "Gaussian Splatting (3D space)",
            "Walk around the subject (not spin in place). 20+ photos, same camera. "
            "Mixed sizes are auto-resized. Needs COLMAP + RTX.",
            self.launch_gaussian_splatting,
        )
        self.gaussian_card.pack(fill=tk.X, pady=6)

        utils = ttk.Frame(outer, style="Root.TFrame")
        utils.pack(fill=tk.X, pady=(12, 8))
        ttk.Button(utils, text="Help", command=self.show_help, style="Ghost.TButton").pack(
            side=tk.LEFT
        )
        ttk.Button(utils, text="Exit", command=self.root.quit, style="Ghost.TButton").pack(
            side=tk.RIGHT
        )

        status = ttk.LabelFrame(outer, text="Status", style="Section.TLabelframe", padding=10)
        status.pack(fill=tk.X, pady=(4, 0))
        self.status_var = tk.StringVar(value="Ready.")
        self.status_label = ttk.Label(status, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.pack(fill=tk.X)
        self.progress_bar = ttk.Progressbar(status, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(8, 0))

        self._action_cards = [
            self.live_card,
            self.pano_card,
            self.view_card,
            self.gaussian_card,
        ]

    def set_buttons_state(self, state) -> None:
        for card in self._action_cards:
            for child in card.winfo_children():
                if isinstance(child, ttk.Button):
                    child.config(state=state)

    def _project_python(self) -> Path:
        root = Path(__file__).resolve().parent.parent
        venv_python = root / "venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            return venv_python
        return Path(sys.executable)

    def launch_live_reconstruction(self) -> None:
        self.status_var.set("Launching live reconstruction…")
        try:
            src_dir = Path(__file__).parent
            script_path = src_dir / "live_reconstruction_app.py"
            python_exe = self._project_python()
            command = f'start cmd /k "{python_exe}" "{script_path}"'
            subprocess.Popen(command, shell=True, cwd=src_dir)
            self.status_var.set("Live reconstruction opened in a new window.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch live reconstruction:\n{e}")
            self.status_var.set("Live launch failed.")

    def launch_gaussian_splatting(self) -> None:
        folder = filedialog.askdirectory(title="Select photo folder for Gaussian Splatting")
        if not folder:
            self.status_var.set("Gaussian cancelled.")
            return

        from colmap_workspace import detect_mixed_dimensions, list_image_files

        images = list_image_files(Path(folder))
        if len(images) < 8:
            messagebox.showerror(
                "Not enough photos",
                f"Found {len(images)} images. Need at least 8 (20+ recommended).\n"
                "Walk around the subject with overlapping shots.",
            )
            self.status_var.set("Gaussian blocked: too few images.")
            return

        mixed = detect_mixed_dimensions(images)
        if mixed:
            proceed = messagebox.askokcancel(
                "Mixed image sizes",
                mixed
                + "\n\nContinue? (Recommended.) Portrait + landscape mixed without this often fails COLMAP.",
            )
            if not proceed:
                self.status_var.set("Gaussian cancelled.")
                return

        tip = (
            f"About to process {len(images)} photos.\n\n"
            "Shoot tip: walk around the subject. Do not only spin in place.\n"
            "This can take a long time (COLMAP + GPU training)."
        )
        if not messagebox.askokcancel("Start Gaussian Splatting", tip):
            self.status_var.set("Gaussian cancelled.")
            return

        self.set_buttons_state(tk.DISABLED)
        self.status_var.set("Starting Gaussian Splatting…")
        threading.Thread(
            target=self._run_gaussian_thread,
            args=(folder,),
            daemon=True,
        ).start()

    def _resolve_gsplat_python(self) -> str:
        root = Path(__file__).resolve().parent.parent
        venv_py = root / "venv_gsplat" / "Scripts" / "python.exe"
        if venv_py.is_file():
            return str(venv_py)
        return sys.executable

    def _friendly_gaussian_error(self, raw: str) -> str:
        text = raw or "unknown error"
        lower = text.lower()
        if "camera_single_dim" in lower or "different dimensions" in lower:
            return (
                "Photos have different widths/heights.\n"
                "Re-run: the app now auto-resizes them. Prefer one camera orientation."
            )
        if "no images with matches" in lower or "failed to create any sparse" in lower:
            return (
                "COLMAP found almost no matching views.\n"
                "Walk around the subject with 60–80% overlap. Avoid blurry frames."
            )
        if "colmap" in lower and "not found" in lower:
            return "COLMAP not found. Install it and open a new terminal, or use run_gaussian.bat."
        if "cv2" in lower or "opencv" in lower:
            return "OpenCV missing in venv_gsplat. Run: venv_gsplat\\Scripts\\pip install opencv-python"
        # Keep a short tail of the real log for debugging
        return text[-900:]

    def _run_gaussian_thread(self, folder: str) -> None:
        try:
            src_dir = Path(__file__).parent
            cli = src_dir / "gaussian_cli.py"
            python_exe = self._resolve_gsplat_python()
            self.update_status(5, f"Running with {Path(python_exe).name}…")

            cmd = [
                python_exe,
                str(cli),
                "--input-dir",
                folder,
                "--max-steps",
                "7000",
                "--data-factor",
                "2",
            ]
            completed = subprocess.run(
                cmd,
                cwd=str(src_dir),
                capture_output=True,
                text=True,
            )
            if completed.stdout:
                print(completed.stdout)
            if completed.stderr:
                print(completed.stderr)

            if completed.returncode == 0:
                self.root.after(
                    0,
                    messagebox.showinfo,
                    "Success",
                    "Gaussian Splatting finished.\nSee workspaces/<run_id>/results/",
                )
                self.update_status(100, "Gaussian complete. Check workspaces/.")
            else:
                err = self._friendly_gaussian_error(
                    completed.stderr or completed.stdout or ""
                )
                self.root.after(0, messagebox.showerror, "Gaussian failed", err)
                self.update_status(100, "Gaussian failed — see message.")
        except Exception as e:
            self.root.after(0, messagebox.showerror, "Critical Error", str(e))
            self.update_status(100, "Critical error.")
        finally:
            self.root.after(0, self.set_buttons_state, tk.NORMAL)

    def launch_photo_reconstruction(self) -> None:
        photo_paths = filedialog.askopenfilenames(
            title="Select photos for 360 panorama",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png"),
                ("All files", "*.*"),
            ],
        )
        if not photo_paths:
            self.status_var.set("Panorama cancelled.")
            return

        self.set_buttons_state(tk.DISABLED)
        self.status_var.set("Building panorama…")
        threading.Thread(
            target=self._run_photo_reconstruction_thread,
            args=(photo_paths,),
            daemon=True,
        ).start()

    def _run_photo_reconstruction_thread(self, photo_paths) -> None:
        try:
            processor = PhotoUploadProcessor()
            success = processor.reconstruct_from_photos(
                photo_paths,
                progress_callback=self.update_status,
            )
            if success and processor.panorama_image is not None and processor.panorama_image.size > 0:
                self.update_status(100, "Saving panorama…")
                saved_files = processor.save_reconstruction()
                if saved_files and saved_files.get("panorama"):
                    saved_path = saved_files["panorama"]
                    self.root.after(
                        0,
                        messagebox.showinfo,
                        "Success",
                        f"Panorama saved:\n{saved_path}",
                    )
                    self.update_status(100, "Panorama complete.")
                else:
                    self.root.after(0, messagebox.showerror, "Error", "Built but failed to save.")
                    self.update_status(100, "Save failed.")
            else:
                self.root.after(
                    0,
                    messagebox.showerror,
                    "Error",
                    "Panorama failed. Rotate in place with overlapping shots.",
                )
                self.update_status(100, "Panorama failed.")
        except Exception as e:
            self.root.after(0, messagebox.showerror, "Critical Error", str(e))
            self.update_status(100, "Critical error.")
        finally:
            self.root.after(0, self.set_buttons_state, tk.NORMAL)

    def update_status(self, progress: int, message: str) -> None:
        def do_update():
            self.status_var.set(message)
            self.progress_bar["value"] = progress

        self.root.after(0, do_update)

    def view_panorama(self) -> None:
        self.status_var.set("Opening panorama…")
        try:
            output_dir = Path(__file__).parent.parent / "output"
            if not output_dir.exists():
                messagebox.showwarning("No output", "Run panorama first.")
                self.status_var.set("No output folder.")
                return
            file_path = filedialog.askopenfilename(
                title="Select panorama",
                initialdir=str(output_dir),
                filetypes=[("PNG images", "*.png"), ("All files", "*.*")],
            )
            if not file_path:
                self.status_var.set("No file selected.")
                return
            self.launch_panorama_viewer(file_path)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status_var.set("Open failed.")

    def launch_panorama_viewer(self, file_path: str) -> None:
        try:
            path = Path(file_path).resolve()
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
            self.status_var.set(f"Opened {path.name}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status_var.set("Viewer failed.")

    def show_help(self) -> None:
        messagebox.showinfo(
            "Help",
            "Live — capture keyframes around a subject (5+), then rebuild.\n\n"
            "Panorama — rotate in place; output is a flat 360 PNG.\n\n"
            "Gaussian — walk around for a real 3D space (COLMAP + RTX).\n"
            "Use 20+ overlapping photos. Mixed sizes are auto-resized.\n\n"
            "Docs: docs/README_Gaussian.md",
        )

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    BasicLauncherGUI().run()


if __name__ == "__main__":
    main()
