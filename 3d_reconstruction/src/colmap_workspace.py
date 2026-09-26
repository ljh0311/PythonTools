"""Persistent COLMAP workspace helper for Gaussian Splatting (and SfM reuse)."""

from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path
from typing import Iterable, List, Literal, Optional, Sequence, Tuple

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
MatcherKind = Literal["exhaustive", "sequential"]


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_workspaces_root() -> Path:
    return project_root() / "workspaces"


def _known_colmap_candidates() -> List[Path]:
    """Common install locations (covers stale terminal PATH after install)."""
    candidates: List[Path] = []
    if sys.platform == "win32":
        local = Path.home() / "AppData" / "Local" / "Programs" / "COLMAP" / "COLMAP.bat"
        candidates.append(local)
        candidates.append(Path(r"C:\Program Files\COLMAP\COLMAP.bat"))
    return candidates


def find_colmap_executable() -> Path:
    """Locate ``colmap`` on PATH, then fall back to known Windows installs."""
    lookup = ["where", "colmap"] if sys.platform == "win32" else ["which", "colmap"]
    try:
        completed = subprocess.run(
            lookup,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        lines = [ln.strip() for ln in completed.stdout.splitlines() if ln.strip()]
        if lines:
            return Path(lines[0])
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    for candidate in _known_colmap_candidates():
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(
        "COLMAP executable not found on PATH. Install COLMAP and ensure "
        "'colmap' is available in a terminal (Windows: `where colmap`). "
        "Expected also at %LOCALAPPDATA%\\Programs\\COLMAP\\COLMAP.bat."
    )


def list_image_files(directory: Path) -> List[Path]:
    if not directory.is_dir():
        return []
    files = [
        p
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return sorted(files, key=lambda p: p.name.lower())


def _run_colmap(args: Sequence[str], cwd: Optional[Path] = None) -> None:
    colmap_exe = find_colmap_executable()
    cmd = [str(colmap_exe), *args]
    try:
        subprocess.run(cmd, check=True, cwd=str(cwd) if cwd else None)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            "Failed to launch COLMAP. Is 'colmap' on PATH?"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"COLMAP command failed (exit {exc.returncode}): {' '.join(cmd)}"
        ) from exc


def _image_size(path: Path) -> Tuple[int, int]:
    """Return (width, height) without requiring OpenCV at import time for listing."""
    try:
        import cv2

        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Cannot read image: {path}")
        h, w = img.shape[:2]
        return w, h
    except Exception as exc:
        raise ValueError(f"Cannot read image size for {path}: {exc}") from exc


def detect_mixed_dimensions(image_paths: Sequence[Path]) -> Optional[str]:
    """Return a human warning if images are not all the same size, else None."""
    paths = [Path(p) for p in image_paths]
    if len(paths) < 2:
        return None
    sizes = {_image_size(p) for p in paths}
    if len(sizes) == 1:
        return None
    sample = ", ".join(f"{w}x{h}" for w, h in sorted(sizes)[:5])
    extra = "" if len(sizes) <= 5 else f" (+{len(sizes) - 5} more)"
    return (
        f"Found {len(sizes)} different image sizes ({sample}{extra}). "
        "They will be resized to one size for COLMAP."
    )


def prepare_images(
    image_sources: Iterable[Path],
    images_dir: Path,
    *,
    clear_existing: bool = True,
    normalize_size: bool = True,
) -> List[Path]:
    """Copy source images into ``images_dir`` with stable names.

    When ``normalize_size`` is True, all frames are resized to the median width/height
    so COLMAP ``ImageReader.single_camera=1`` does not fail with CAMERA_SINGLE_DIM_ERROR.
    """
    import cv2

    images_dir.mkdir(parents=True, exist_ok=True)
    if clear_existing:
        for existing in list_image_files(images_dir):
            existing.unlink(missing_ok=True)

    sources = [Path(src) for src in image_sources]
    if not sources:
        return []

    loaded = []
    for src in sources:
        if not src.is_file():
            raise FileNotFoundError(f"Image not found: {src}")
        img = cv2.imread(str(src), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Cannot read image: {src}")
        loaded.append((src, img))

    target_w, target_h = None, None
    if normalize_size and loaded:
        widths = sorted(img.shape[1] for _, img in loaded)
        heights = sorted(img.shape[0] for _, img in loaded)
        mid = len(widths) // 2
        target_w, target_h = widths[mid], heights[mid]
        unique = {(img.shape[1], img.shape[0]) for _, img in loaded}
        if len(unique) > 1:
            print(
                f"[colmap] Normalizing {len(unique)} image sizes → {target_w}x{target_h}"
            )

    copied: List[Path] = []
    for index, (src, img) in enumerate(loaded):
        if target_w and target_h and (img.shape[1], img.shape[0]) != (target_w, target_h):
            img = cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_AREA)
        dest = images_dir / f"image_{index:06d}.jpg"
        if not cv2.imwrite(str(dest), img, [int(cv2.IMWRITE_JPEG_QUALITY), 95]):
            raise RuntimeError(f"Failed to write normalized image: {dest}")
        copied.append(dest)
    return copied


def ensure_sparse_model(sparse_dir: Path) -> Path:
    """Return ``sparse/0`` (or first numbered model) or raise a clear error."""
    if not sparse_dir.exists():
        raise FileNotFoundError(
            f"COLMAP sparse model directory missing: {sparse_dir}. "
            "Run COLMAP mapping first, or check that reconstruction succeeded."
        )

    model_0 = sparse_dir / "0"
    if model_0.is_dir() and any(model_0.iterdir()):
        return model_0

    numbered = sorted(
        (p for p in sparse_dir.iterdir() if p.is_dir() and p.name.isdigit()),
        key=lambda p: int(p.name),
    )
    for candidate in numbered:
        if any(candidate.iterdir()):
            return candidate

    raise FileNotFoundError(
        f"No COLMAP sparse model found under {sparse_dir}. "
        "Feature matching or mapping likely failed (need more overlapping views)."
    )


class ColmapWorkspace:
    """Persistent COLMAP workspace: images + database.db + sparse/0."""

    def __init__(
        self,
        run_id: Optional[str] = None,
        workspaces_root: Optional[Path] = None,
        *,
        matcher: MatcherKind = "exhaustive",
    ):
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self.workspaces_root = Path(workspaces_root or default_workspaces_root())
        self.root = self.workspaces_root / self.run_id
        self.images_dir = self.root / "images"
        self.database_path = self.root / "database.db"
        self.sparse_dir = self.root / "sparse"
        self.matcher: MatcherKind = matcher

    def create_layout(self) -> Path:
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.sparse_dir.mkdir(parents=True, exist_ok=True)
        return self.root

    def prepare_from_paths(
        self,
        image_paths: Sequence[Path],
        *,
        clear_existing: bool = True,
    ) -> List[Path]:
        self.create_layout()
        return prepare_images(
            image_paths, self.images_dir, clear_existing=clear_existing
        )

    def prepare_from_directory(
        self,
        input_dir: Path,
        *,
        clear_existing: bool = True,
    ) -> List[Path]:
        sources = list_image_files(Path(input_dir))
        if not sources:
            raise FileNotFoundError(f"No images found in {input_dir}")
        return self.prepare_from_paths(sources, clear_existing=clear_existing)

    def run_feature_extractor(self) -> None:
        find_colmap_executable()
        _run_colmap(
            [
                "feature_extractor",
                "--database_path",
                str(self.database_path),
                "--image_path",
                str(self.images_dir),
                "--ImageReader.single_camera",
                "1",
            ]
        )

    def run_matcher(self) -> None:
        find_colmap_executable()
        if self.matcher == "sequential":
            _run_colmap(
                [
                    "sequential_matcher",
                    "--database_path",
                    str(self.database_path),
                ]
            )
        else:
            _run_colmap(
                [
                    "exhaustive_matcher",
                    "--database_path",
                    str(self.database_path),
                ]
            )

    def run_mapper(self) -> Path:
        find_colmap_executable()
        self.sparse_dir.mkdir(parents=True, exist_ok=True)
        _run_colmap(
            [
                "mapper",
                "--database_path",
                str(self.database_path),
                "--image_path",
                str(self.images_dir),
                "--output_path",
                str(self.sparse_dir),
            ]
        )
        return ensure_sparse_model(self.sparse_dir)

    def run_sfm(
        self,
        image_paths: Optional[Sequence[Path]] = None,
        *,
        skip_if_sparse_exists: bool = False,
    ) -> Tuple[Path, Path]:
        """
        Full SfM pipeline.

        Returns:
            (workspace_root, sparse_model_dir)
        """
        self.create_layout()
        if image_paths is not None:
            self.prepare_from_paths(image_paths)

        if skip_if_sparse_exists:
            try:
                sparse_model = ensure_sparse_model(self.sparse_dir)
                if list_image_files(self.images_dir):
                    return self.root, sparse_model
            except FileNotFoundError:
                pass

        n_images = len(list_image_files(self.images_dir))
        if n_images < 2:
            raise ValueError(
                f"Need at least 2 images in {self.images_dir} for COLMAP SfM "
                f"(found {n_images})."
            )

        if self.database_path.exists():
            self.database_path.unlink()

        print(f"[colmap] feature_extractor ({n_images} images)...")
        self.run_feature_extractor()
        print(f"[colmap] {self.matcher}_matcher...")
        self.run_matcher()
        print("[colmap] mapper...")
        try:
            sparse_model = self.run_mapper()
        except (RuntimeError, FileNotFoundError) as exc:
            raise RuntimeError(
                "COLMAP failed to build a 3D model. Common causes:\n"
                "  - Photos are too similar / not enough overlap while walking around\n"
                "  - Blurry frames or heavy motion blur\n"
                "  - Mixed portrait/landscape without resize (now auto-normalized)\n"
                f"Details: {exc}"
            ) from exc
        print(f"[colmap] sparse model: {sparse_model}")
        return self.root, sparse_model


def build_colmap_workspace(
    image_paths: Sequence[Path],
    *,
    run_id: Optional[str] = None,
    workspaces_root: Optional[Path] = None,
    matcher: MatcherKind = "exhaustive",
    skip_colmap: bool = False,
) -> Tuple[Path, Path]:
    """
    Convenience entry: prepare images and run (or reuse) COLMAP SfM.

    Returns:
        (workspace_root, sparse_model_dir)
    """
    ws = ColmapWorkspace(
        run_id=run_id,
        workspaces_root=workspaces_root,
        matcher=matcher,
    )
    if skip_colmap:
        ws.create_layout()
        if image_paths:
            # Only copy if workspace images are empty
            if not list_image_files(ws.images_dir):
                ws.prepare_from_paths(image_paths)
        sparse = ensure_sparse_model(ws.sparse_dir)
        return ws.root, sparse
    return ws.run_sfm(image_paths)
