"""Resolve and invoke gsplat training (subprocess) on Windows-friendly paths."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

from colmap_workspace import project_root


def resolve_gsplat_python() -> Path:
    """Prefer project ``venv_gsplat`` interpreter; else current ``sys.executable``."""
    root = project_root()
    if sys.platform == "win32":
        candidate = root / "venv_gsplat" / "Scripts" / "python.exe"
    else:
        candidate = root / "venv_gsplat" / "bin" / "python"
    if candidate.is_file():
        return candidate
    return Path(sys.executable)


def resolve_simple_trainer_script() -> Optional[Path]:
    """
    Locate gsplat ``examples/simple_trainer.py``.

    Search order:
      1. ``GSPLAT_TRAINER`` env var (file path)
      2. ``3d_reconstruction/vendor/gsplat/examples/simple_trainer.py``
      3. ``venv_gsplat`` site-packages sibling clone is not assumed —
         examples are not installed with the wheel.
    """
    env = os.environ.get("GSPLAT_TRAINER", "").strip()
    if env:
        path = Path(env)
        if path.is_file():
            return path

    vendored = (
        project_root() / "vendor" / "gsplat" / "examples" / "simple_trainer.py"
    )
    if vendored.is_file():
        return vendored
    return None


def trainer_command_help() -> str:
    return (
        "gsplat training requires examples/simple_trainer.py.\n"
        "Options:\n"
        "  1) Clone into vendor:\n"
        "       git clone --depth 1 https://github.com/nerfstudio-project/gsplat.git "
        "vendor/gsplat\n"
        "  2) Or set env GSPLAT_TRAINER to the full path of simple_trainer.py\n"
        "Typical command (after COLMAP workspace exists):\n"
        "  <venv_gsplat>/python vendor/gsplat/examples/simple_trainer.py default \\\n"
        "    --data_dir <workspace> --result_dir <workspace>/results \\\n"
        "    --data_factor 2 --max_steps 7000 --save_ply\n"
    )


@dataclass
class TrainRequest:
    data_dir: Path
    result_dir: Path
    max_steps: int = 7000
    data_factor: int = 2
    view: bool = False
    save_ply: bool = True
    extra_args: Sequence[str] = ()


@dataclass
class TrainResult:
    command: List[str]
    returncode: int
    result_dir: Path
    dry_run: bool = False


def build_train_command(
    req: TrainRequest,
    *,
    python_exe: Optional[Path] = None,
    trainer_script: Optional[Path] = None,
) -> List[str]:
    python_exe = python_exe or resolve_gsplat_python()
    trainer_script = trainer_script or resolve_simple_trainer_script()
    if trainer_script is None:
        raise FileNotFoundError(trainer_command_help())

    cmd: List[str] = [
        str(python_exe),
        str(trainer_script),
        "default",
        "--data_dir",
        str(req.data_dir),
        "--result_dir",
        str(req.result_dir),
        "--data_factor",
        str(req.data_factor),
        "--max_steps",
        str(req.max_steps),
    ]
    if req.save_ply:
        cmd.append("--save_ply")
        # Export near the end of the configured budget
        cmd.extend(["--ply_steps", str(req.max_steps)])
    if not req.view:
        cmd.append("--disable_viewer")
    if req.extra_args:
        cmd.extend(req.extra_args)
    return cmd


def run_gsplat_training(
    req: TrainRequest,
    *,
    dry_run: bool = False,
    python_exe: Optional[Path] = None,
) -> TrainResult:
    """
    Shell out to gsplat ``simple_trainer.py default``.

    Raises FileNotFoundError if the trainer script cannot be resolved
    (unless dry_run, in which case the planned command is still returned
    when possible, or a placeholder is used).
    """
    req.result_dir.mkdir(parents=True, exist_ok=True)
    python_exe = python_exe or resolve_gsplat_python()

    try:
        cmd = build_train_command(req, python_exe=python_exe)
    except FileNotFoundError:
        if dry_run:
            placeholder = [
                str(python_exe),
                "<simple_trainer.py missing — see docs>",
                "default",
                "--data_dir",
                str(req.data_dir),
                "--result_dir",
                str(req.result_dir),
                "--data_factor",
                str(req.data_factor),
                "--max_steps",
                str(req.max_steps),
            ]
            print("[gsplat] dry-run (trainer not found yet):")
            print(" ", " ".join(placeholder))
            print(trainer_command_help())
            return TrainResult(
                command=placeholder,
                returncode=0,
                result_dir=req.result_dir,
                dry_run=True,
            )
        raise

    print("[gsplat] command:")
    print(" ", " ".join(cmd))
    if dry_run:
        return TrainResult(
            command=cmd, returncode=0, result_dir=req.result_dir, dry_run=True
        )

    # Run from examples/ so relative imports (datasets, etc.) resolve
    cwd = Path(cmd[1]).resolve().parent
    completed = subprocess.run(cmd, cwd=str(cwd))
    return TrainResult(
        command=cmd,
        returncode=completed.returncode,
        result_dir=req.result_dir,
        dry_run=False,
    )


def find_export_artifacts(result_dir: Path) -> dict:
    """Collect common gsplat output paths if present."""
    result_dir = Path(result_dir)
    artifacts = {
        "result_dir": str(result_dir),
        "ckpts": str(result_dir / "ckpts") if (result_dir / "ckpts").exists() else None,
        "ply_dir": str(result_dir / "ply") if (result_dir / "ply").exists() else None,
        "renders": str(result_dir / "renders")
        if (result_dir / "renders").exists()
        else None,
    }
    ply_files = sorted((result_dir / "ply").glob("*.ply")) if artifacts["ply_dir"] else []
    if ply_files:
        artifacts["latest_ply"] = str(ply_files[-1])
    else:
        artifacts["latest_ply"] = None
    return artifacts
