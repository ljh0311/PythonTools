#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Desktop media browser for motion snapshots and recordings."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
from typing import List, Optional

from PIL import Image, ImageTk

from ..security.media_library import (
    MotionSessionStore,
    list_recording_files,
)


def open_path_in_os(path: Path) -> None:
    path = Path(path)
    if sys.platform == "win32":
        os.startfile(str(path))  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


class MediaBrowserDialog(tk.Toplevel):
    """Browse paired motion snapshots and recordings."""

    def __init__(self, parent, project_root: Path, motion_dir: Path, recordings_dirs: List[Path]):
        super().__init__(parent)
        self.title("Media Library")
        self.geometry("900x620")
        self.minsize(720, 480)

        self.project_root = Path(project_root)
        self.motion_store = MotionSessionStore(motion_dir, self.project_root)
        self.recordings_dirs = recordings_dirs

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.motion_frame = ttk.Frame(notebook)
        self.recordings_frame = ttk.Frame(notebook)
        notebook.add(self.motion_frame, text="Motion events")
        notebook.add(self.recordings_frame, text="Recordings")

        self._build_motion_tab()
        self._build_recordings_tab()
        self.refresh()

    def _build_motion_tab(self) -> None:
        toolbar = ttk.Frame(self.motion_frame)
        toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side=tk.LEFT)
        ttk.Button(
            toolbar,
            text="Open snapshots folder",
            command=lambda: open_path_in_os(self.motion_store.snapshot_dir),
        ).pack(side=tk.LEFT, padx=6)

        canvas = tk.Canvas(self.motion_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.motion_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.motion_list = ttk.Frame(canvas)
        self.motion_list.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.motion_list, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_recordings_tab(self) -> None:
        toolbar = ttk.Frame(self.recordings_frame)
        toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side=tk.LEFT)
        for directory in self.recordings_dirs:
            ttk.Button(
                toolbar,
                text=f"Open {directory.name}",
                command=lambda d=directory: open_path_in_os(d),
            ).pack(side=tk.LEFT, padx=4)

        list_frame = ttk.Frame(self.recordings_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.recording_tree = ttk.Treeview(
            list_frame,
            columns=("camera", "size", "modified"),
            show="headings",
            selectmode="browse",
        )
        self.recording_tree.heading("camera", text="Camera")
        self.recording_tree.heading("size", text="Size (MB)")
        self.recording_tree.heading("modified", text="Type")
        self.recording_tree.column("camera", width=120)
        self.recording_tree.column("size", width=80)
        self.recording_tree.column("modified", width=120)
        self.recording_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.recording_tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.recording_tree.configure(yscrollcommand=scroll.set)

        actions = ttk.Frame(self.recordings_frame)
        actions.pack(fill=tk.X, pady=6)
        ttk.Button(actions, text="Play selected", command=self._play_selected_recording).pack(side=tk.LEFT)

        self._recording_paths = {}

    def refresh(self) -> None:
        for child in self.motion_list.winfo_children():
            child.destroy()

        sessions = self.motion_store.list_sessions(limit=30)
        if not sessions:
            ttk.Label(self.motion_list, text="No motion snapshots yet.").pack(anchor="w", pady=8)
        else:
            for session in sessions:
                self._add_motion_session_row(session)

        for item in self.recording_tree.get_children():
            self.recording_tree.delete(item)
        self._recording_paths.clear()

        recordings = list_recording_files(self.recordings_dirs, self.project_root, limit=50)
        for rec in recordings:
            iid = rec["path"]
            self._recording_paths[iid] = rec
            kind = "motion" if rec.get("motion_triggered") else "continuous"
            self.recording_tree.insert(
                "",
                tk.END,
                iid=iid,
                values=(rec.get("camera_id"), rec.get("size_mb"), kind),
                text=rec.get("filename"),
            )

    def _load_thumb(self, path: Optional[str], max_size=(200, 150)) -> Optional[ImageTk.PhotoImage]:
        if not path:
            return None
        file_path = self.project_root / path.replace("/", os.sep)
        if not file_path.is_file():
            return None
        try:
            img = Image.open(file_path)
            img.thumbnail(max_size)
            return ImageTk.PhotoImage(img)
        except OSError:
            return None

    def _add_motion_session_row(self, session: dict) -> None:
        row = ttk.LabelFrame(
            self.motion_list,
            text=f"{session.get('camera_id')} · {session.get('session_id')}",
        )
        row.pack(fill=tk.X, pady=6, padx=4)

        images = ttk.Frame(row)
        images.pack(fill=tk.X, padx=6, pady=6)

        for label, key in (("Motion started", "first_snapshot"), ("Motion ended", "last_snapshot")):
            col = ttk.Frame(images)
            col.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=4)
            ttk.Label(col, text=label).pack()
            thumb = self._load_thumb(session.get(key))
            if thumb:
                lbl = ttk.Label(col, image=thumb)
                lbl.image = thumb
                lbl.pack()
                rel = session.get(key)
                ttk.Button(
                    col,
                    text="Open",
                    command=lambda p=rel: open_path_in_os(self.project_root / p.replace("/", os.sep)),
                ).pack(pady=2)
            else:
                ttk.Label(col, text="(missing)").pack(pady=20)

    def _play_selected_recording(self) -> None:
        selected = self.recording_tree.selection()
        if not selected:
            messagebox.showinfo("Recordings", "Select a recording first.")
            return
        rec = self._recording_paths.get(selected[0])
        if not rec:
            return
        file_path = self.project_root / rec["path"].replace("/", os.sep)
        if not file_path.is_file():
            for directory in self.recordings_dirs:
                alt = directory / rec.get("filename", "")
                if alt.is_file():
                    file_path = alt
                    break
        if file_path.is_file():
            open_path_in_os(file_path)
        else:
            messagebox.showerror("Recordings", f"File not found: {rec.get('filename')}")
