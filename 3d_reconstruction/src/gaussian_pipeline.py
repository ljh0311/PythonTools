"""Orchestrate photos/video → COLMAP workspace → gsplat training."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Union

from colmap_workspace import (
    ColmapWorkspace,
    MatcherKind,
    build_colmap_workspace,
    default_workspaces_root,
    list_image_files,
    project_root,
)
from gsplat_train_runner import (
    TrainRequest,
    find_export_artifacts,
    resolve_gsplat_python,
    run_gsplat_training,
)
from video_processor import VideoProcessor

ProgressCallback = Optional[Callable[[int, str], None]]

MIN_IMAGES_HARD = 8
MIN_IMAGES_WARN = 20

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


@dataclass
class GaussianPipelineResult:
    success: bool
    workspace: Path
    sparse_model: Optional[Path]
    result_dir: Path
    artifacts: dict = field(default_factory=dict)
    message: str = ""
    dry_run: bool = False
    train_command: List[str] = field(default_factory=list)


def _progress(cb: ProgressCallback, pct: int, msg: str) -> None:
    if cb:
        cb(pct, msg)
    else:
        print(f"[{pct:3d}%] {msg}")


def collect_images_from_dir(input_dir: Path) -> List[Path]:
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    images = list_image_files(input_dir)
    if not images:
        raise FileNotFoundError(f"No images found in {input_dir}")
    return images


def extract_frames_from_video(
    video_path: Path,
    output_dir: Path,
    *,
    frame_interval: int = 5,
) -> List[Path]:
    video_path = Path(video_path)
    if not video_path.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    processor = VideoProcessor(str(video_path))
    paths = processor.extract_frames(str(output_dir), frame_interval=frame_interval)
    return [Path(p) for p in paths]


def validate_image_count(n: int) -> None:
    if n < MIN_IMAGES_HARD:
        raise ValueError(
            f"Need at least {MIN_IMAGES_HARD} images for Gaussian Splatting "
            f"(got {n}). Capture more views with ~60–80% overlap."
        )
    if n < MIN_IMAGES_WARN:
        warnings.warn(
            f"Only {n} images provided; {MIN_IMAGES_WARN}+ recommended for "
            "stable COLMAP poses and splat quality.",
            UserWarning,
            stacklevel=2,
        )


def run_gaussian_pipeline(
    *,
    input_dir: Optional[Union[str, Path]] = None,
    video: Optional[Union[str, Path]] = None,
    image_paths: Optional[Sequence[Union[str, Path]]] = None,
    run_id: Optional[str] = None,
    workspaces_root: Optional[Union[str, Path]] = None,
    max_steps: int = 7000,
    data_factor: int = 2,
    view: bool = False,
    skip_colmap: bool = False,
    dry_run: bool = False,
    frame_interval: int = 5,
    matcher: Optional[MatcherKind] = None,
    progress_callback: ProgressCallback = None,
) -> GaussianPipelineResult:
    """
    End-to-end offline Gaussian Splatting pipeline.

    Provide one of: ``input_dir``, ``video``, or ``image_paths``.
    """
    workspaces_root = Path(workspaces_root or default_workspaces_root())
    sources: List[Path] = []

    _progress(progress_callback, 5, "Preparing images...")

    if video:
        # Temporary extract into a staging folder under workspaces before COLMAP copy
        staging_run = run_id or "video_frames"
        staging = workspaces_root / f"_staging_{staging_run}"
        sources = extract_frames_from_video(
            Path(video), staging / "frames", frame_interval=frame_interval
        )
        if matcher is None:
            matcher = "sequential"
    elif image_paths:
        sources = [Path(p) for p in image_paths]
    elif input_dir:
        sources = collect_images_from_dir(Path(input_dir))
    else:
        raise ValueError("Provide input_dir, video, or image_paths.")

    if matcher is None:
        matcher = "exhaustive"

    validate_image_count(len(sources))
    _progress(
        progress_callback,
        15,
        f"Using {len(sources)} images (matcher={matcher})...",
    )

    ws = ColmapWorkspace(
        run_id=run_id,
        workspaces_root=workspaces_root,
        matcher=matcher,
    )
    result_dir = ws.root / "results"

    try:
        if skip_colmap:
            _progress(progress_callback, 30, "Reusing existing COLMAP sparse model...")
            workspace, sparse_model = build_colmap_workspace(
                sources,
                run_id=ws.run_id,
                workspaces_root=workspaces_root,
                matcher=matcher,
                skip_colmap=True,
            )
        else:
            _progress(progress_callback, 25, "Running COLMAP SfM (persistent workspace)...")
            workspace, sparse_model = build_colmap_workspace(
                sources,
                run_id=ws.run_id,
                workspaces_root=workspaces_root,
                matcher=matcher,
                skip_colmap=False,
            )
    except Exception as exc:
        return GaussianPipelineResult(
            success=False,
            workspace=ws.root,
            sparse_model=None,
            result_dir=result_dir,
            message=str(exc),
            dry_run=dry_run,
        )

    _progress(progress_callback, 55, f"COLMAP ready: {sparse_model}")

    if dry_run:
        _progress(progress_callback, 90, "Dry-run: skipping gsplat training...")
        train = run_gsplat_training(
            TrainRequest(
                data_dir=workspace,
                result_dir=result_dir,
                max_steps=max_steps,
                data_factor=data_factor,
                view=view,
            ),
            dry_run=True,
        )
        _progress(progress_callback, 100, "Dry-run complete (COLMAP workspace prepared).")
        return GaussianPipelineResult(
            success=True,
            workspace=workspace,
            sparse_model=sparse_model,
            result_dir=result_dir,
            artifacts={
                "workspace": str(workspace),
                "sparse_model": str(sparse_model),
                "images": str(workspace / "images"),
                **find_export_artifacts(result_dir),
            },
            message="Dry-run: COLMAP workspace prepared; training skipped.",
            dry_run=True,
            train_command=train.command,
        )

    _progress(progress_callback, 60, "Starting gsplat training...")
    _progress(
        progress_callback,
        62,
        f"Using Python: {resolve_gsplat_python()}",
    )
    try:
        train = run_gsplat_training(
            TrainRequest(
                data_dir=workspace,
                result_dir=result_dir,
                max_steps=max_steps,
                data_factor=data_factor,
                view=view,
            ),
            dry_run=False,
        )
    except Exception as exc:
        return GaussianPipelineResult(
            success=False,
            workspace=workspace,
            sparse_model=sparse_model,
            result_dir=result_dir,
            artifacts={
                "workspace": str(workspace),
                "sparse_model": str(sparse_model),
            },
            message=str(exc),
            dry_run=False,
        )

    ok = train.returncode == 0
    artifacts = {
        "workspace": str(workspace),
        "sparse_model": str(sparse_model),
        "images": str(workspace / "images"),
        **find_export_artifacts(result_dir),
    }
    _progress(
        progress_callback,
        100,
        "Gaussian training finished." if ok else "Gaussian training failed.",
    )
    return GaussianPipelineResult(
        success=ok,
        workspace=workspace,
        sparse_model=sparse_model,
        result_dir=result_dir,
        artifacts=artifacts,
        message="" if ok else f"gsplat exited with code {train.returncode}",
        dry_run=False,
        train_command=train.command,
    )


# Re-export for callers
__all__ = [
    "GaussianPipelineResult",
    "MIN_IMAGES_HARD",
    "MIN_IMAGES_WARN",
    "project_root",
    "run_gaussian_pipeline",
    "validate_image_count",
]
