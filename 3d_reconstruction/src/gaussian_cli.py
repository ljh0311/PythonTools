#!/usr/bin/env python3
"""CLI for offline 3D Gaussian Splatting (photos or video → COLMAP → gsplat)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gaussian_pipeline import run_gaussian_pipeline


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Gaussian Splatting: photos/video -> COLMAP -> gsplat train",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python gaussian_cli.py --input-dir ./photos --max-steps 7000 --data-factor 2
  python gaussian_cli.py --video capture.mp4 --dry-run
  python gaussian_cli.py --input-dir ./photos --run-id my_scene --skip-colmap
  python gaussian_cli.py --input-dir ./photos --view

Workspace layout:
  3d_reconstruction/workspaces/<run_id>/{images,database.db,sparse/0,results}
        """,
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--input-dir",
        type=str,
        help="Directory of photos (jpg/png/...)",
    )
    src.add_argument(
        "--video",
        type=str,
        help="Video file; frames extracted then processed as images",
    )

    parser.add_argument("--run-id", type=str, default=None, help="Workspace id under workspaces/")
    parser.add_argument("--max-steps", type=int, default=7000, help="gsplat max_steps (default 7000)")
    parser.add_argument(
        "--data-factor",
        type=int,
        default=2,
        help="Image downsample factor for training (default 2)",
    )
    parser.add_argument(
        "--view",
        action="store_true",
        help="Enable gsplat Viser viewer during training",
    )
    parser.add_argument(
        "--skip-colmap",
        action="store_true",
        help="Reuse existing workspaces/<run_id>/sparse model",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prepare COLMAP workspace only; print train command, do not train",
    )
    parser.add_argument(
        "--frame-interval",
        type=int,
        default=5,
        help="When using --video, keep every Nth frame (default 5)",
    )
    return parser.parse_args(argv)


def _progress(pct: int, msg: str) -> None:
    bar_len = 40
    filled = int(bar_len * pct // 100)
    bar = "#" * filled + "-" * (bar_len - filled)
    print(f"\r[{bar}] {pct:3d}% - {msg}", end="", flush=True)
    if pct >= 100:
        print()


def main(argv=None) -> int:
    args = parse_args(argv)

    if args.skip_colmap and not args.run_id:
        print("Error: --skip-colmap requires --run-id pointing at an existing workspace.")
        return 2

    try:
        result = run_gaussian_pipeline(
            input_dir=args.input_dir,
            video=args.video,
            run_id=args.run_id,
            max_steps=args.max_steps,
            data_factor=args.data_factor,
            view=args.view,
            skip_colmap=args.skip_colmap,
            dry_run=args.dry_run,
            frame_interval=args.frame_interval,
            progress_callback=_progress,
        )
    except Exception as exc:
        print(f"\nError: {exc}")
        return 1

    print()
    print(f"Workspace:     {result.workspace}")
    if result.sparse_model:
        print(f"Sparse model:  {result.sparse_model}")
    print(f"Results dir:   {result.result_dir}")
    if result.train_command:
        print(f"Train command: {' '.join(result.train_command)}")
    if result.artifacts:
        print("Artifacts:")
        for key, value in result.artifacts.items():
            if value:
                print(f"  {key}: {value}")
    if result.message:
        print(result.message)

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
