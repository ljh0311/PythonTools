#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Motion snapshot sessions and recording file listing for web/GUI."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def safe_camera_id(camera_id: str) -> str:
    return "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in camera_id)


def new_session_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]


def snapshot_filename(camera_id: str, session_id: str, phase: str) -> str:
    return f"{safe_camera_id(camera_id)}_evt_{session_id}_{phase}.jpg"


class MotionSessionStore:
    """Paired first/last motion snapshots with a shared session id."""

    NEW_FMT = re.compile(
        r"^(?P<camera>.+)_evt_(?P<session>\d{8}_\d{6}_[a-f0-9]+)_(?P<phase>first|last)\.jpg$",
        re.I,
    )
    LEGACY_FMT = re.compile(
        r"^(?P<camera>.+)_(?P<phase>first|last)_(?P<stamp>.+)\.jpg$",
        re.I,
    )

    def __init__(self, snapshot_dir: Path, project_root: Path):
        self.snapshot_dir = Path(snapshot_dir)
        self.project_root = Path(project_root)
        self.index_path = self.snapshot_dir / "sessions.json"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def rel_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.project_root)).replace("\\", "/")
        except ValueError:
            return str(path).replace("\\", "/")

    def snapshot_path(self, camera_id: str, session_id: str, phase: str) -> Path:
        return self.snapshot_dir / snapshot_filename(camera_id, session_id, phase)

    def _load_index(self) -> List[Dict]:
        if not self.index_path.exists():
            return []
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save_index(self, rows: List[Dict]) -> None:
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(rows[-500:], f, indent=2)

    def register_session_start(
        self, session_id: str, camera_id: str, first_path: Path, started_at: float
    ) -> None:
        rows = self._load_index()
        rows.append(
            {
                "session_id": session_id,
                "camera_id": camera_id,
                "started_at": started_at,
                "ended_at": None,
                "first_snapshot": self.rel_path(first_path),
                "last_snapshot": None,
                "label": f"{camera_id} · {session_id}",
            }
        )
        self._save_index(rows)

    def register_session_end(
        self, session_id: str, camera_id: str, last_path: Path, ended_at: float
    ) -> None:
        rows = self._load_index()
        for row in reversed(rows):
            if row.get("session_id") == session_id and row.get("camera_id") == camera_id:
                row["ended_at"] = ended_at
                row["last_snapshot"] = self.rel_path(last_path)
                break
        else:
            rows.append(
                {
                    "session_id": session_id,
                    "camera_id": camera_id,
                    "started_at": ended_at,
                    "ended_at": ended_at,
                    "first_snapshot": None,
                    "last_snapshot": self.rel_path(last_path),
                    "label": f"{camera_id} · {session_id}",
                }
            )
        self._save_index(rows)

    def _scan_legacy_pairs(self) -> Dict[str, Dict]:
        """Pair old-format first/last files by camera and chronological order."""
        first_by_cam: Dict[str, List[Tuple[float, str]]] = {}
        last_by_cam: Dict[str, List[Tuple[float, str]]] = {}

        if not self.snapshot_dir.exists():
            return {}

        for file_path in self.snapshot_dir.glob("*.jpg"):
            m = self.LEGACY_FMT.match(file_path.name)
            if not m:
                continue
            cam = m.group("camera")
            phase = m.group("phase").lower()
            rel = self.rel_path(file_path)
            mtime = file_path.stat().st_mtime
            bucket = first_by_cam if phase == "first" else last_by_cam
            bucket.setdefault(cam, []).append((mtime, rel))

        sessions: Dict[str, Dict] = {}
        for cam in set(first_by_cam) | set(last_by_cam):
            firsts = sorted(first_by_cam.get(cam, []))
            lasts = sorted(last_by_cam.get(cam, []))
            used_last = 0
            for idx, (first_time, first_rel) in enumerate(firsts):
                last_rel = None
                last_time = None
                while used_last < len(lasts):
                    candidate_time, candidate_rel = lasts[used_last]
                    if candidate_time >= first_time:
                        last_rel = candidate_rel
                        last_time = candidate_time
                        used_last += 1
                        break
                    used_last += 1
                first_name = Path(first_rel).name
                prefix = f"{cam}_first_"
                session_id = (
                    first_name[len(prefix) : -4]
                    if first_name.startswith(prefix)
                    else first_name
                )
                key = f"legacy::{cam}::{session_id}"
                sessions[key] = {
                    "session_id": session_id,
                    "camera_id": cam,
                    "first_snapshot": first_rel,
                    "last_snapshot": last_rel,
                    "label": f"{cam} · legacy event",
                    "legacy": True,
                    "started_at": first_time,
                    "ended_at": last_time,
                }
        return sessions

    def _scan_files(self) -> Dict[str, Dict]:
        sessions: Dict[str, Dict] = {}
        if not self.snapshot_dir.exists():
            return sessions

        for file_path in self.snapshot_dir.glob("*.jpg"):
            name = file_path.name
            rel = self.rel_path(file_path)
            m = self.NEW_FMT.match(name)
            if m:
                cam = m.group("camera")
                sid = m.group("session")
                phase = m.group("phase").lower()
                key = f"{cam}::{sid}"
                entry = sessions.setdefault(
                    key,
                    {
                        "session_id": sid,
                        "camera_id": cam,
                        "first_snapshot": None,
                        "last_snapshot": None,
                        "label": f"{cam} · event {sid}",
                    },
                )
                if phase == "first":
                    entry["first_snapshot"] = rel
                else:
                    entry["last_snapshot"] = rel

        sessions.update(self._scan_legacy_pairs())
        return sessions

    def list_sessions(self, limit: int = 50) -> List[Dict]:
        merged: Dict[str, Dict] = {}
        for row in self._load_index():
            key = f"{row.get('camera_id')}::{row.get('session_id')}"
            merged[key] = {**row, "complete": bool(row.get("first_snapshot") and row.get("last_snapshot"))}

        for key, scanned in self._scan_files().items():
            if key not in merged:
                merged[key] = {
                    **scanned,
                    "complete": bool(scanned.get("first_snapshot") and scanned.get("last_snapshot")),
                }
            else:
                if not merged[key].get("first_snapshot"):
                    merged[key]["first_snapshot"] = scanned.get("first_snapshot")
                if not merged[key].get("last_snapshot"):
                    merged[key]["last_snapshot"] = scanned.get("last_snapshot")
                merged[key]["complete"] = bool(
                    merged[key].get("first_snapshot") and merged[key].get("last_snapshot")
                )

        rows = list(merged.values())
        rows.sort(key=lambda r: r.get("ended_at") or r.get("started_at") or 0, reverse=True)
        return rows[:limit]

    def find_session(self, session_id: str, camera_id: Optional[str] = None) -> Optional[Dict]:
        for row in self.list_sessions(limit=500):
            if row.get("session_id") != session_id:
                continue
            if camera_id and row.get("camera_id") != camera_id:
                continue
            return row
        return None

    def remove_from_index(self, session_id: str, camera_id: str) -> None:
        rows = self._load_index()
        rows = [
            row
            for row in rows
            if not (row.get("session_id") == session_id and row.get("camera_id") == camera_id)
        ]
        self._save_index(rows)

    def session_snapshot_paths(self, session_id: str, camera_id: str) -> List[str]:
        session = self.find_session(session_id, camera_id)
        if not session:
            return []
        paths = []
        for key in ("first_snapshot", "last_snapshot"):
            rel = session.get(key)
            if rel:
                paths.append(rel)
        return paths


def media_mime_type(file_path: Path) -> str:
    """MIME type for snapshots and recordings."""
    ext = file_path.suffix.lower()
    if ext == ".mp4":
        return "video/mp4"
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    return "application/octet-stream"


def delete_media_file(relative_path: str, project_root: Path, allowed_dirs: List[Path]) -> Dict:
    """Delete one media file after path validation."""
    resolved = resolve_media_path(relative_path, project_root, allowed_dirs)
    resolved.unlink()
    rel = str(resolved.relative_to(project_root.resolve())).replace("\\", "/")
    return {"path": rel, "deleted": True}


def delete_media_files(
    paths: List[str], project_root: Path, allowed_dirs: List[Path]
) -> Dict:
    """Delete multiple media files; continues on individual failures."""
    deleted: List[str] = []
    errors: List[Dict] = []
    for rel_path in paths:
        try:
            delete_media_file(rel_path, project_root, allowed_dirs)
            deleted.append(rel_path)
        except (ValueError, FileNotFoundError, OSError) as exc:
            errors.append({"path": rel_path, "error": str(exc)})
    return {"deleted": deleted, "errors": errors, "count": len(deleted)}


def delete_older_media(
    project_root: Path,
    allowed_dirs: List[Path],
    recordings_dirs: List[Path],
    motion_dir: Path,
    older_than_days: int,
    include_recordings: bool = True,
    include_snapshots: bool = True,
) -> Dict:
    """Delete recordings and/or motion snapshots older than N days."""
    if older_than_days < 1:
        raise ValueError("older_than_days must be at least 1")
    cutoff = datetime.now().timestamp() - (older_than_days * 24 * 60 * 60)
    deleted: List[str] = []
    errors: List[Dict] = []

    def _try_delete(rel_path: str) -> None:
        try:
            delete_media_file(rel_path, project_root, allowed_dirs)
            deleted.append(rel_path)
        except (ValueError, FileNotFoundError, OSError) as exc:
            errors.append({"path": rel_path, "error": str(exc)})

    if include_recordings:
        for directory in recordings_dirs:
            if not directory or not directory.exists():
                continue
            for file_path in directory.glob("*.mp4"):
                if file_path.stat().st_mtime >= cutoff:
                    continue
                try:
                    rel = str(file_path.relative_to(project_root.resolve())).replace("\\", "/")
                except ValueError:
                    rel = str(file_path).replace("\\", "/")
                _try_delete(rel)

    if include_snapshots and motion_dir.exists():
        for file_path in motion_dir.glob("*.jpg"):
            if file_path.stat().st_mtime >= cutoff:
                continue
            try:
                rel = str(file_path.relative_to(project_root.resolve())).replace("\\", "/")
            except ValueError:
                rel = str(file_path).replace("\\", "/")
            _try_delete(rel)

    return {
        "deleted": deleted,
        "errors": errors,
        "count": len(deleted),
        "older_than_days": older_than_days,
    }


def resolve_media_path(relative_path: str, project_root: Path, allowed_dirs: List[Path]) -> Path:
    """Resolve a project-relative media path; block traversal."""
    rel = relative_path.replace("\\", "/").lstrip("/")
    if ".." in rel.split("/"):
        raise ValueError("Invalid path")
    candidate = (project_root / rel).resolve()
    for root in allowed_dirs:
        root_resolved = root.resolve()
        try:
            candidate.relative_to(root_resolved)
            if candidate.is_file():
                return candidate
        except ValueError:
            continue
    raise FileNotFoundError(relative_path)


def list_recording_files(recordings_dirs: List[Path], project_root: Path, limit: int = 50) -> List[Dict]:
    """List mp4 recordings from one or more directories."""
    seen = set()
    items: List[Dict] = []
    name_re = re.compile(r"^(?P<prefix>motion|continuous)_(?P<camera>.+?)_(?P<stamp>\d{8}_\d{6})\.mp4$", re.I)

    for directory in recordings_dirs:
        if not directory or not directory.exists():
            continue
        for file_path in sorted(directory.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
            if file_path in seen:
                continue
            seen.add(file_path)
            stat = file_path.stat()
            try:
                rel = str(file_path.relative_to(project_root)).replace("\\", "/")
            except ValueError:
                rel = str(file_path).replace("\\", "/")
            m = name_re.match(file_path.name)
            items.append(
                {
                    "filename": file_path.name,
                    "path": rel,
                    "camera_id": m.group("camera") if m else file_path.stem,
                    "motion_triggered": bool(m and m.group("prefix").lower() == "motion"),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified_at": stat.st_mtime,
                }
            )
            if len(items) >= limit:
                return items
    return items


def collect_recordings_dirs(project_root: Path, config_output_dir: str, recorder_dir: Optional[Path] = None) -> List[Path]:
    backend_dir = project_root / "web_version" / "backend"
    candidates = [
        recorder_dir,
        backend_dir / config_output_dir,
        project_root / config_output_dir,
        backend_dir / "recordings",
    ]
    unique: List[Path] = []
    for path in candidates:
        if path is None:
            continue
        resolved = Path(path).resolve()
        if resolved not in unique:
            unique.append(resolved)
    return unique
