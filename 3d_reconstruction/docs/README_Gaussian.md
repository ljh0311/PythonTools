# Gaussian Splatting Mode

Offline **3D Gaussian Splatting** for `3d_reconstruction`: photos or video → persistent COLMAP poses → gsplat training on an RTX GPU → checkpoints / exported splat under `workspaces/`.

This is a third photo/video mode alongside:
- `panorama` → 360 PNG
- `reconstruction` → point cloud / mesh
- **`gaussian`** → trained splat + optional Viser viewer

## Requirements

| Piece | Notes |
|---|---|
| NVIDIA RTX + driver | Check with `nvidia-smi` |
| CUDA PyTorch env | Created by `setup_gsplat_venv.bat` → `venv_gsplat/` |
| COLMAP on PATH | System binary (or optional `pycolmap` in the venv) |
| Vendor trainer script | `vendor/gsplat/examples/simple_trainer.py` |

Do **not** mix this stack with the classical Open3D `venv/` unless you know the installs are compatible.

## One-time setup

### 1. CUDA / gsplat venv

From `3d_reconstruction/`:

```bat
setup_gsplat_venv.bat
```

This creates `venv_gsplat/` with Python 3.12, a matching PyTorch CUDA wheel (cu124 / cu128 from driver), and `gsplat`.

Activate later with:

```powershell
.\venv_gsplat\Scripts\Activate.ps1
```

Or always launch via:

```bat
run_gaussian.bat --help
```

### 2. COLMAP

Install [COLMAP](https://colmap.github.io/) and ensure `colmap` is on your PATH:

```bat
where colmap
```

Gaussian mode needs a real SfM model kept on disk (`images/` + `sparse/0/`), not a disposable temp folder.

### 3. Vendor gsplat (trainer examples)

The pip wheel does not ship `examples/simple_trainer.py`. Clone once:

```bat
git clone --depth 1 https://github.com/nerfstudio-project/gsplat.git vendor/gsplat
```

Or set `GSPLAT_TRAINER` to the full path of `simple_trainer.py`.

## Capture tips

- Prefer **20+** images (hard fail under 8; warn under 20).
- Walk around the subject/scene with **60–80% overlap**.
- Good light; avoid motion blur and pure spin-in-place (needs baseline, unlike panorama).
- Supported stills: JPG, PNG, and other common formats via the pipeline.

## CLI examples

Dry-run (prepare workspace / print train command; **no training**):

```bat
run_gaussian.bat --input-dir path\to\photos --dry-run
```

Or with the venv Python:

```bat
venv_gsplat\Scripts\python.exe src\gaussian_cli.py --input-dir path\to\photos --dry-run
```

Train (default ~7k steps, `data_factor=2` for laptop VRAM):

```bat
run_gaussian.bat --input-dir path\to\photos --max-steps 7000 --data-factor 2
```

Video frames → same pipeline:

```bat
run_gaussian.bat --video capture.mp4 --frame-interval 5 --dry-run
```

Optional Viser viewer during training:

```bat
run_gaussian.bat --input-dir path\to\photos --view
```

Reuse an existing COLMAP sparse model:

```bat
run_gaussian.bat --input-dir path\to\photos --run-id my_scene --skip-colmap
```

GUI: launcher button **Gaussian Splatting (photos)** also routes to this mode.

## Outputs

Each run writes under:

```
3d_reconstruction/workspaces/<run_id>/
  images/
  database.db
  sparse/0/          # COLMAP model
  results/           # gsplat checkpoints, renders, optional PLY export
```

`workspaces/` and `venv_gsplat/` are gitignored.

## Smoke checks (dev)

```bat
nvidia-smi
where colmap
venv_gsplat\Scripts\python.exe -c "import torch; print(torch.cuda.is_available())"
venv_gsplat\Scripts\python.exe -c "import gsplat; print('ok')"
python -m py_compile src\colmap_workspace.py src\gaussian_pipeline.py src\gsplat_train_runner.py src\gaussian_cli.py
python src\gaussian_cli.py --help
```

Do not run a full train for a smoke test; use `--dry-run` on a small photo folder only when you already have images ready.

## Troubleshooting

| Symptom | Likely fix |
|---|---|
| `colmap` not found | Install COLMAP; add it to PATH |
| `torch.cuda.is_available()` is False | Re-run `setup_gsplat_venv.bat`; update NVIDIA driver |
| `No module named 'gsplat'` | Re-run setup, or `pip install gsplat` inside `venv_gsplat` |
| Missing `simple_trainer.py` | Clone `vendor/gsplat` as above |
| VRAM OOM | Raise `--data-factor` (e.g. 4) or lower `--max-steps` |
